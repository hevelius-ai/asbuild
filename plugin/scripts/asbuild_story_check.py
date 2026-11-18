#!/usr/bin/env python3
"""AsBuild's story-time checks: run by the skill before it opens a story pull request (decision C5).

Usage, from the project's root, with the Python that runs the project's tests:
    python asbuild_story_check.py S<n> [--base origin/main] [--lock] [--keep DIR]

For story S<n> (dev-docs/stories/S<n>/story.md and its tests in tests/acceptance/S<n>/):
  - the story file is complete: the owner's words, 1 to 5 checks, each with a plain sentence and 1 to 3 examples;
  - there is exactly one test per check;
  - check 1: each test fails on the base branch, by an assertion. The story's test folder is laid over the base in
    a git worktree and run with CI's hardened flags, as CI's fails-before check does (engine/c3_overlay.py);
  - check 2: each test asserts its check's approved examples (Phase 0's F4 example check, Python part).
A JavaScript story (v0.4.0; its folder holds `*.test.[cm]?[jt]sx?` files, one per check) is checked the same way,
with Vitest in place of pytest: a scanner reads each file's one top-level `test("S<n>-C<m> ...")` and refuses the
forms that skip, narrow or hide a check; the installed Vite and Vitest must be the table's (design §4.4); each file
must fail on the base by an assertion when run with AsBuild's own settings (`../js/vitest.acceptance.mjs`) through
`node node_modules/vitest/vitest.mjs`; each approved example must be a literal inside an `expect(...)` chain.
--lock then adds the story's test files to locks.json, with the same entries as engine/lock_check.py, and adds
Claude Code's deny rule for the story's test folder to .claude/settings.json (decision D26).
--keep DIR keeps the JUnit file (pytest's, or Vitest's for a JavaScript story). Exit 0: every check passed. 1: a check
failed (one line per problem, saying why). 2: the checks could not run. Standard library only; pytest (or Vitest)
is the project's own.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:  # the JavaScript facts live beside this file (also when it is loaded by path)
    sys.path.insert(0, str(HERE))
import asbuild_js as js  # noqa: E402

CHECK_ID = re.compile(r"\bS\d+-C\d+\b")
TEST_DEF = re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)\s*\(", re.M)  # as engine/lock_check.py
# JavaScript and TypeScript (v0.4.0, M3-C1; design §4.5). As engine/langs.py: the files the JavaScript row owns, and
# the literal titles of top-level `test(` and `it(` calls, which the lock records.
JS_OWNED = re.compile(r"\.[cm]?[jt]sx?$")
JS_FILE = re.compile(r"\.test\.[cm]?[jt]sx?$")  # what AsBuild's Vitest settings include
JS_TITLE = re.compile(r"""^(?:test|it)\s*\(\s*(?:"([^"\\\n]*)"|'([^'\\\n]*)'|`([^`\\$\n]*)`)""", re.M)
# As engine/junit_classify.py: the failures that only show a part of the app does not exist yet.
JS_EXISTENCE = (
    "Cannot find module",
    "Cannot find package",
    "Failed to resolve import",
    "does not provide an export named",
    "Element type is invalid",
)
JS_TYPE_ERROR = ("is not a function", "is not a constructor")
JS_SETTINGS = HERE.parent / "js" / "vitest.acceptance.mjs"  # a copy of the engine's, kept equal by a test
JS_WORKTREES = ".asbuild-story"  # inside the checkout, so the project's node_modules is found (JS-7)
JS_TIMEOUT = 120  # seconds per check file on the base
TOOLS_CMD = 'the first story\'s command, python "${CLAUDE_PLUGIN_ROOT}/scripts/asbuild_js.py" tools (javascript.md)'
NO_VITEST = f"Vitest is not installed in this project: run {TOOLS_CMD}, then run this again"
NPM_CI = "npm ci --no-audit --no-fund --legacy-peer-deps"  # the test job's own install (design §4.2)
NO_NODE_MODULES = (
    "the app's software is not installed on this computer (an earlier story added the test tools): run"
    f" {NPM_CI}, then run this again"
)
ASSERTION = ("assert", "AssertionError", "Failed:")  # pytest's messages for assert, AssertionError, pytest.raises
MAX_CHECKS, MAX_EXAMPLES = 5, 3
MAX_COMBOS = 50
FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)
END_OF_REQUEST = ("## Criteria", "## Plain checklist", "## Not in this story")  # the template's next headings
CONVERSIONS: dict[int, Callable[[object], str]] = {115: str, 114: repr, 97: ascii}  # !s !r !a in an f-string


class CannotRun(Exception):
    """The checks could not run at all (exit 2)."""


# ------------------------------------------------------------------ the lock entry (as engine/lock_check.py)


def normalised(data: bytes) -> bytes:
    text = data.decode("utf-8", errors="surrogateescape")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip(" \t") for ln in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return ("\n".join(lines) + "\n").encode("utf-8", errors="surrogateescape")


def js_titles(text: str) -> list[str]:
    return [next(g for g in m.groups() if g is not None) for m in JS_TITLE.finditer(text)]


def entry(raw: bytes, path: str = "") -> dict:
    text = raw.decode("utf-8", errors="replace")
    return {
        "sha256": hashlib.sha256(normalised(raw)).hexdigest(),
        "tests": js_titles(text) if JS_OWNED.search(path) else TEST_DEF.findall(text),
    }


# ------------------------------------------------------------------ the story file


def cells(line: str) -> list[str]:
    row = line.strip().removeprefix("|").removesuffix("|")
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", row)]  # "\|" is a literal bar


def parse_story(text: str) -> tuple[str, list[dict]]:
    """(the Request section's text, [{id, plain, examples}]) from the plain checklist."""
    request: list[str] = []
    checks: list[dict] = []
    section = ""
    for line in text.splitlines():
        if section == "request" and not line.startswith(END_OF_REQUEST):
            request.append(line)  # the owner's words may hold lines that start with "#"
        elif line.startswith("#"):
            heading = line.lower()
            section = "request" if heading.startswith("## request") else "plain" if "plain" in heading else ""
        elif section == "plain":
            row = cells(line)
            if len(row) >= 2 and CHECK_ID.fullmatch(row[0]):
                examples = re.findall(r"`([^`]+)`", row[2]) if len(row) >= 3 else []
                checks.append({"id": row[0], "plain": row[1], "examples": examples})
    return "\n".join(request).strip(), checks


def story_problems(story: str, text: str, request: str, checks: list[dict]) -> list[str]:
    out = []
    if not request:
        out.append("story: the Request section is empty: copy the owner's words into it, unchanged")
    if not checks:
        out.append("story: the plain checklist has no checks")
    if len(checks) > MAX_CHECKS:
        out.append(f"story: {len(checks)} checks; a story has at most {MAX_CHECKS}")
    listed = {c["id"] for c in checks}
    for cid in dict.fromkeys(CHECK_ID.findall(text)):
        if cid not in listed:
            out.append(f"story: {cid} is not in the plain checklist")
    for c in checks:
        if not c["id"].startswith(story + "-"):
            out.append(f"{c['id']} belongs to another story")
        if not c["plain"]:
            out.append(f"{c['id']} has no plain sentence")
        if not 1 <= len(c["examples"]) <= MAX_EXAMPLES:
            out.append(f"{c['id']} needs 1 to {MAX_EXAMPLES} approved examples, each in backticks")
    return out


# ------------------------------------------------------------------ the tests


def matches(test_name: str, check: str) -> bool:
    """True when the test's name carries the check ID as whole words (as engine/verdict.py)."""
    toks = test_name.split("[", 1)[0].lower().split("_")
    want = check.lower().split("-")
    return any(toks[i : i + len(want)] == want for i in range(len(toks)))


def find_tests(folder: Path) -> tuple[dict[str, tuple[Path, str]], list[str]]:
    """{test name: (file, qualified name)} for test functions and Test* class methods, and the problems found."""
    found: dict[str, tuple[Path, str]] = {}
    bad = []

    def add(name: str, path: Path, qual: str) -> None:
        if name in found:  # a second test of the same name would be locked but never examined
            bad.append(f"{name} is defined more than once: give each test its own name")
        found[name] = (path, qual)

    for path in sorted(folder.rglob("*.py")):
        try:
            module = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, ValueError):
            bad.append(f"tests/acceptance/{folder.name}/{path.name} cannot be read as Python")
            continue
        for node in module.body:
            if isinstance(node, FUNCS) and node.name.startswith("test"):
                add(node.name, path, node.name)
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for m in node.body:
                    if isinstance(m, FUNCS) and m.name.startswith("test"):
                        add(m.name, path, f"{node.name}.{m.name}")
    return found, bad


# ------------------------------------------------------------------ check 1: fails on the base, by an assertion


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


def run_on_base(repo: Path, base: str, story: str, keep: Path | None) -> dict[str, tuple[str, str]]:
    """{test name: (kind, first line of the message)}; kind is passed, assertion, other, error or skipped."""
    tmp = Path(tempfile.mkdtemp(prefix="asbuild-story-"))
    tree = tmp / "base"
    try:
        add = git(repo, "worktree", "add", "--detach", str(tree), base)
        if add.returncode != 0:
            raise CannotRun(f"could not check out {base}: {add.stderr.strip()}")
        rel = Path("tests", "acceptance", story)
        shutil.copytree(repo / rel, tree / rel, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
        xml = tmp / "story-check.xml"
        subprocess.run(
            [sys.executable, "-m", "pytest", rel.as_posix(), "--noconftest", "-p", "no:cacheprovider",
             "--continue-on-collection-errors", "-o", "junit_family=xunit2", f"--junitxml={xml}"],
            cwd=tree, env=dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"), capture_output=True, text=True,
        )  # fmt: skip
        if not xml.is_file():
            raise CannotRun("pytest wrote no results on the base branch")
        if keep is not None:
            keep.mkdir(parents=True, exist_ok=True)
            shutil.copy(xml, keep / xml.name)
        return results(xml)
    finally:
        git(repo, "worktree", "remove", "--force", str(tree))
        git(repo, "worktree", "prune")
        shutil.rmtree(tmp, ignore_errors=True)


def results(xml: Path) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for tc in ET.parse(xml).getroot().iter("testcase"):
        name = (tc.get("name") or "").split("[", 1)[0]
        kids = [k for k in tc if k.tag in ("failure", "error", "skipped")]
        msg = (kids[0].get("message") or "").strip().split("\n", 1)[0][:160] if kids else ""
        if not kids:
            kind = "passed"
        elif kids[0].tag == "failure":
            kind = "assertion" if msg.startswith(ASSERTION) else "other"
        else:
            kind = "skipped" if kids[0].tag == "skipped" else "error"
        if name not in out or kind != "assertion":  # a parametrised test: any case that did not fail
            out[name] = (kind, msg)  # by an assertion decides
    return out


def base_problem(test: str, ran: dict[str, tuple[str, str]], base: str) -> str | None:
    kind, msg = ran.get(test, ("missing", ""))
    on = base.removeprefix("origin/")
    return {
        "assertion": None,
        "passed": f"passes already on {on}: it checks nothing the build will change",
        "skipped": f"is skipped on {on}: a skipped test checks nothing ({msg})",
        "other": f"fails on {on} for a reason other than an assertion: {msg}",
        "error": f"could not run on {on}: {msg}",
        "missing": f"did not run on {on} (the file could not be collected)",
    }[kind]


# ------------------------------------------------------------------ check 2: asserts the approved examples
# Ported from Phase 0's F4 example_check.py (Python part), unchanged but for example_matches.


def is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_value(v) -> bool:
    return isinstance(v, str) or is_num(v)


def _callee(call: ast.Call) -> str:
    f = call.func
    return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""


def _key(node) -> str | None:
    """Binding key for a Name ("x") or a self/cls attribute ("self.x"); None otherwise."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in ("self", "cls"):
        return "self." + node.attr
    return None


def _bindings(stmts) -> dict[str, list]:
    """name -> [value exprs] from simple assignments (x = v, x: T = v, a, b = v1, v2)."""
    out: dict[str, list] = {}
    for st in stmts:
        if isinstance(st, ast.Assign):
            targets, value = st.targets, st.value
        elif isinstance(st, ast.AnnAssign) and st.value is not None:
            targets, value = [st.target], st.value
        else:
            continue
        for t in targets:
            if (
                isinstance(t, (ast.Tuple, ast.List))
                and isinstance(value, (ast.Tuple, ast.List))
                and len(t.elts) == len(value.elts)
            ):
                pairs = list(zip(t.elts, value.elts, strict=True))
            else:
                pairs = [(t, value)]
            for tt, vv in pairs:
                k = _key(tt)
                if k:
                    out.setdefault(k, []).append(vv)
    return out


def _assigns(node) -> list:
    return [n for n in ast.walk(node) if isinstance(n, (ast.Assign, ast.AnnAssign))]


class PyEnv:
    """Resolves names for one test: parametrize args, then function, class, module scope."""

    def __init__(self, module, cls, func):
        module_scope = _bindings(module.body)
        class_scope: dict[str, list] = {}
        if cls is not None:
            for k, v in _bindings(cls.body).items():
                class_scope[k] = list(v)
                class_scope.setdefault("self." + k, []).extend(v)
            for m in cls.body:
                if isinstance(m, FUNCS):
                    for k, v in _bindings(_assigns(m)).items():
                        if k.startswith("self."):
                            class_scope.setdefault(k, []).extend(v)
        self.module_scope = module_scope
        self.scopes = [self._parametrize(cls, func), _bindings(_assigns(func)), class_scope, module_scope]

    def _parametrize(self, cls, func) -> dict[str, list]:
        out: dict[str, list] = {}
        decos = list(func.decorator_list) + (list(cls.decorator_list) if cls is not None else [])
        for d in decos:
            if not (isinstance(d, ast.Call) and _callee(d) == "parametrize" and len(d.args) >= 2):
                continue
            names_node = d.args[0]
            rows: ast.expr | None = d.args[1]
            if isinstance(names_node, ast.Constant) and isinstance(names_node.value, str):
                names = [n.strip() for n in names_node.value.split(",") if n.strip()]
            elif isinstance(names_node, (ast.List, ast.Tuple)):
                names = [e.value for e in names_node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            else:
                continue
            if isinstance(rows, ast.Name):  # @parametrize("a", CASES) with CASES at module level
                rows = next(iter(self.module_scope.get(rows.id, [])), None)
            if not isinstance(rows, (ast.List, ast.Tuple)):
                continue
            for row in rows.elts:
                if isinstance(row, ast.Call) and _callee(row) == "param":  # pytest.param(...)
                    vals = list(row.args)
                elif len(names) == 1:
                    vals = [row]
                elif isinstance(row, (ast.Tuple, ast.List)):
                    vals = row.elts
                else:
                    continue
                for name, val in zip(names, vals, strict=False):
                    out.setdefault(name, []).append(val)
        return out

    def lookup(self, key: str) -> list:
        for scope in self.scopes:
            if key in scope:
                return scope[key]
        return []

    def scalars(self, node, seen=frozenset()) -> list | None:
        """Possible scalar values of node as a whole, or None when unknown."""
        if isinstance(node, ast.Constant):
            return [node.value] if is_value(node.value) else None
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            inner = self.scalars(node.operand, seen)
            if inner and all(is_num(v) for v in inner):
                return [-v if isinstance(node.op, ast.USub) else v for v in inner]
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = self.scalars(node.left, seen), self.scalars(node.right, seen)
            if left and right and all(isinstance(v, str) for v in left + right):
                return [a + b for a, b in itertools.islice(itertools.product(left, right), MAX_COMBOS)]
            return None
        if isinstance(node, ast.JoinedStr):
            parts = []
            for p in node.values:
                if not isinstance(p, ast.FormattedValue):  # a constant piece of the f-string
                    parts.append([str(getattr(p, "value", ""))])
                    continue
                vals = self.scalars(p.value, seen)
                spec = self.scalars(p.format_spec, seen) if p.format_spec else [""]
                if not vals or not spec:
                    return None
                conv = CONVERSIONS.get(p.conversion)
                try:
                    parts.append([format(conv(v) if conv else v, str(spec[0])) for v in vals])
                except (ValueError, TypeError):
                    return None
            return ["".join(c) for c in itertools.islice(itertools.product(*parts), MAX_COMBOS)]
        key = _key(node)
        if key and key not in seen:
            out = [v for e in self.lookup(key) for v in (self.scalars(e, seen | {key}) or [])]
            return out or None
        return None

    def leaves(self, node, seen=frozenset()) -> list:
        """All values of a resolvable expression, flattening containers; [] when unresolvable."""
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return [v for e in node.elts for v in self.leaves(e, seen)]
        if isinstance(node, ast.Dict):
            return [v for e in node.keys + node.values if e is not None for v in self.leaves(e, seen)]
        if isinstance(node, ast.Starred):
            return self.leaves(node.value, seen)
        key = _key(node)
        if key:
            return [] if key in seen else [v for e in self.lookup(key) for v in self.leaves(e, seen | {key})]
        return self.scalars(node, seen) or []

    def collect(self, node, out: list) -> None:
        """Collect values from an expression that sits inside an assertion."""
        if _key(node):
            out.extend(self.leaves(node))
            return
        if isinstance(node, (ast.Constant, ast.UnaryOp, ast.BinOp, ast.JoinedStr)):
            vals = self.scalars(node)
            if vals is not None:
                out.extend(vals)
                return
        for child in ast.iter_child_nodes(node):
            if not (isinstance(child, ast.keyword) and child.arg == "msg"):
                self.collect(child, out)


def find_py_test(module, name: str):
    if "." in name:
        cname, fname = name.rsplit(".", 1)
        for node in ast.walk(module):
            if isinstance(node, ast.ClassDef) and node.name == cname:
                for m in node.body:
                    if isinstance(m, FUNCS) and m.name == fname:
                        return node, m
        return None
    for node in module.body:
        if isinstance(node, FUNCS) and node.name == name:
            return None, node
    return None


def python_asserted(source: str, name: str) -> list:
    """Asserted values of test `name` (found by find_tests, so it exists and parses)."""
    module = ast.parse(source)
    cls, func = find_py_test(module, name)
    env = PyEnv(module, cls, func)
    out: list = []
    for n in ast.walk(func):
        if isinstance(n, ast.Assert):
            env.collect(n.test, out)  # the assert message is not a checked value
        elif isinstance(n, ast.Call) and _callee(n).startswith("assert"):
            for arg in n.args:
                env.collect(arg, out)
            for kw in n.keywords:
                if kw.arg != "msg":
                    env.collect(kw.value, out)
    return out


def example_matches(example: str, asserted: list) -> bool:
    """An approved example (text from the story) matches an asserted string that equals it or, at 4 characters
    or more, contains it as a whole value (not "words: 3" inside "words: 30", "words: 3.5" or "words: 3,000");
    or an asserted number written the same way."""
    left = r"(?<!\w)" if re.match(r"\w", example) else ""
    left += r"(?<!\d[.,])(?<![-+])" if re.match(r"\d", example) else ""  # not inside "1.5 items" or "-5 items"
    right = r"(?!\w)" if re.search(r"\w$", example) else ""
    right += r"(?![.,]\d)" if re.search(r"\d$", example) else ""  # "words: 3" is not inside "words: 3.5"
    whole = re.compile(left + re.escape(example) + right)
    for a in asserted:
        if isinstance(a, str) and (a == example or (len(example) >= 4 and whole.search(a))):
            return True
        if is_num(a) and str(a) == example:
            return True
    return False


# ------------------------------------------------------------------ JavaScript: the scanner (M3-C1)

# After these, a "/" starts a regular expression, not a division. Never after "<", ">" or "}": in JSX those come
# before the "/" of a closing tag or of "/>" (review round 1, B3); after "=>" a "/" still starts one.
REGEX_AFTER = set("(,=:[!&|?{;+-*%~^")
REGEX_KEYWORDS = {
    "return",
    "typeof",
    "case",
    "do",
    "else",
    "in",
    "of",
    "new",
    "delete",
    "void",
    "throw",
    "yield",
    "await",
}
REFUSED = {"describe", "suite", "xit", "xtest", "fit", "fdescribe", "xdescribe"}
CALLS = {"test", "it"}
IDENT = re.compile(r"[A-Za-z_$][\w$]*")
NUMBER = re.compile(r"\d[\w.]*")
SPACE = " \t\r\n" + chr(0xFEFF)  # a byte order mark counts as space


@dataclass
class Tok:
    kind: str  # id, str, tpl, num, punct, regex
    value: str
    line_start: bool  # its first character starts a line (no indentation)
    literal: bool = True  # a str or tpl with no escape and no ${...}


@dataclass
class JsScan:
    titles: list[str] = field(default_factory=list)  # the literal titles of the file's top-level test calls
    lock_titles: list[str] = field(default_factory=list)  # the titles the lock records (JS_TITLE)
    literals: list[str] = field(default_factory=list)  # literal strings and numbers inside expect(...) chains
    problems: list[str] = field(default_factory=list)


def _skip_string(text: str, i: int, quote: str) -> tuple[int, bool]:
    """From just after an opening quote: (the index after the closing quote, whether it holds no escape)."""
    plain = True
    while i < len(text):
        c = text[i]
        if c == "\\":
            plain, i = False, i + 2
            continue
        if c == quote:
            return i + 1, plain
        if c == "\n":  # an unclosed string ends at its line
            return i, False
        i += 1
    return i, False


def _skip_template(text: str, i: int) -> tuple[int, bool]:
    """From just after an opening backtick: (the index after the closing one, whether it is literal)."""
    plain = True
    while i < len(text):
        c = text[i]
        if c == "\\":
            plain, i = False, i + 2
            continue
        if c == "`":
            return i + 1, plain
        if c == "$" and text.startswith("{", i + 1):
            plain, i = False, _skip_code(text, i + 2)
            continue
        i += 1
    return i, False


def _skip_comment(text: str, i: int) -> int:
    """From a "//" or "/*": the index after the comment."""
    if text.startswith("//", i):
        j = text.find("\n", i)
        return len(text) if j < 0 else j
    j = text.find("*/", i + 2)
    return len(text) if j < 0 else j + 2


def _skip_code(text: str, i: int) -> int:
    """From just after "${": the index after its matching "}"."""
    depth = 1
    while i < len(text):
        c = text[i]
        if c in "'\"":
            i = _skip_string(text, i + 1, c)[0]
        elif c == "`":
            i = _skip_template(text, i + 1)[0]
        elif text.startswith(("//", "/*"), i):
            i = _skip_comment(text, i)
        else:
            depth += {"{": 1, "}": -1}.get(c, 0)
            i += 1
            if depth == 0:
                return i
    return i


def _skip_regex(text: str, i: int) -> int:
    """From just after a regular expression's opening "/": the index after its flags."""
    in_class = False
    while i < len(text) and text[i] != "\n":
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if in_class:
            in_class = c != "]"
        elif c == "[":
            in_class = True
        elif c == "/":
            m = IDENT.match(text, i + 1)
            return m.end() if m else i + 1
        i += 1
    return i


def js_tokens(text: str) -> list[Tok]:
    """The file's tokens, with comments, the insides of strings, templates and regular expressions read as one each."""
    toks: list[Tok] = []
    i = 0
    while i < len(text):
        c = text[i]
        sol = i == 0 or text[i - 1] == "\n"
        if c in SPACE:
            i += 1
        elif text.startswith(("//", "/*"), i):
            i = _skip_comment(text, i)
        elif c in "'\"":
            j, plain = _skip_string(text, i + 1, c)
            toks.append(Tok("str", text[i + 1 : j - 1] if plain else "", sol, plain))
            i = j
        elif c == "`":
            j, plain = _skip_template(text, i + 1)
            toks.append(Tok("tpl", text[i + 1 : j - 1] if plain else "", sol, plain))
            i = j
        elif c == "/" and (
            not toks
            or (toks[-1].kind == "punct" and toks[-1].value in REGEX_AFTER)
            or (toks[-1].kind == "id" and toks[-1].value in REGEX_KEYWORDS)
            or (_is(toks, len(toks) - 1, ">") and _is(toks, len(toks) - 2, "="))
        ):
            i = _skip_regex(text, i + 1)
            toks.append(Tok("regex", "", sol, False))
        elif (m := NUMBER.match(text, i)) or (m := IDENT.match(text, i)):
            toks.append(Tok("num" if c.isdigit() else "id", m.group(), sol))
            i = m.end()
        else:
            toks.append(Tok("punct", c, sol))
            i += 1
    return toks


def _is(toks: list[Tok], k: int, value: str) -> bool:
    return 0 <= k < len(toks) and toks[k].kind == "punct" and toks[k].value == value


def _close(toks: list[Tok], k: int) -> int:
    """From an opening bracket: the index of its matching closer (the last token if it has none)."""
    depth = 0
    for j in range(k, len(toks)):
        if toks[j].kind == "punct" and toks[j].value in "([{":
            depth += 1
        elif toks[j].kind == "punct" and toks[j].value in ")]}":
            depth -= 1
            if depth == 0:
                return j
    return len(toks) - 1


def _later_arguments(toks: list[Tok], k: int, end: int) -> range:
    """The token indexes of a call's arguments after its first one (from its "(" at k to its ")" at end)."""
    depth = 0
    for j in range(k, end):
        if toks[j].kind == "punct" and toks[j].value in "([{":
            depth += 1
        elif toks[j].kind == "punct" and toks[j].value in ")]}":
            depth -= 1
        elif depth == 1 and _is(toks, j, ","):
            return range(j, end)
    return range(0)


def _expect_literals(toks: list[Tok], a: int, b: int) -> list[str]:
    """The literal strings and numbers inside each expect(...) chain between tokens a and b."""
    out: list[str] = []
    j = a
    while j <= b:
        if toks[j].kind == "id" and toks[j].value == "expect" and not _is(toks, j - 1, "."):
            m = j + 1
            if _is(toks, m, ".") and m + 1 <= b and toks[m + 1].kind == "id":  # expect.soft(...)
                m += 2
            if _is(toks, m, "("):
                end = _close(toks, m)
                message = _later_arguments(toks, m, end)  # expect(value, "message"): never an asserted value
                while end + 2 <= b and _is(toks, end + 1, ".") and toks[end + 2].kind == "id":
                    end += 2
                    if _is(toks, end + 1, "("):
                        end = _close(toks, end + 1)
                out += [
                    t.value
                    for k, t in enumerate(toks[j : end + 1], start=j)
                    if k not in message and (t.kind == "num" or (t.kind in ("str", "tpl") and t.literal))
                ]
                j = end
        j += 1
    return out


def scan_js(text: str) -> JsScan:
    """One check file: its top-level test call, the forms refused, and the literals its expect(...) chains assert."""
    s = JsScan(lock_titles=js_titles(text))
    toks = js_tokens(text)
    depth = 0
    for k, t in enumerate(toks):
        if t.kind == "punct" and t.value in "([{":
            depth += 1
        elif t.kind == "punct" and t.value in ")]}":
            depth = max(0, depth - 1)
        if t.kind != "id" or _is(toks, k - 1, "."):
            continue
        if t.value in REFUSED and (_is(toks, k + 1, "(") or _is(toks, k + 1, ".")):
            s.problems.append(f"{t.value}(...) is not allowed: write one plain top-level test(...) per file")
        elif t.value in CALLS | {"describe"} and _is(toks, k + 1, ".") and k + 2 < len(toks):
            s.problems.append(
                f"{t.value}.{toks[k + 2].value} is not allowed: write one plain test(...) that always runs"
            )
        elif t.value in CALLS and _is(toks, k + 1, "("):
            title = toks[k + 2] if k + 2 < len(toks) else None
            if depth > 0:
                s.problems.append("a test(...) inside another block: write it at the top level of the file")
            elif not t.line_start:
                s.problems.append(f"{t.value}( must be at the start of a line, with no spaces before it")
            elif (
                title is None
                or title.kind not in ("str", "tpl")
                or not title.literal
                or (title.kind == "tpl" and "$" in title.value)
                or not (_is(toks, k + 3, ",") or _is(toks, k + 3, ")"))
            ):
                s.problems.append("the test needs a literal title in quotes, with no ${...} and no backslash")
            else:
                s.titles.append(title.value)
                s.literals += _expect_literals(toks, k + 1, _close(toks, k + 1))
    if len(s.titles) > 1:
        s.problems.append(f"holds {len(s.titles)} tests: one test per file")
    if s.titles != s.lock_titles:
        s.problems.append("a line starting with test( or it( is inside a comment or string: remove it")
    if not s.titles and not s.problems:
        s.problems.append("holds no test: write one top-level test(...) per file")
    return s


def carries(title: str, check: str) -> bool:
    """True when a title carries the check ID as whole words (as engine/langs.py: split on any character that is
    not a letter or a digit)."""
    toks = re.split(r"[\W_]", title.lower())
    want = check.lower().split("-")
    return any(toks[i : i + len(want)] == want for i in range(len(toks)))


# ------------------------------------------------------------------ JavaScript: the run on the base


def js_kind(tc: ET.Element) -> tuple[str, str]:
    """How one Vitest result behaved, by the engine's rules (engine/junit_classify.py, classify_js)."""
    kids = [k for k in tc if k.tag in ("failure", "error", "skipped")]
    if not kids:
        return "passed", ""
    k = kids[0]
    msg = (k.get("message") or "").strip()
    first = msg.split("\n", 1)[0][:160]
    typ = (k.get("type") or "").strip()
    if k.tag == "skipped":
        return "skipped", first
    if not typ:
        return "unreadable", first
    if typ == "AssertionError":
        return "assertion", first
    if typ == "ReferenceError" or (typ == "TypeError" and any(s in msg for s in JS_TYPE_ERROR)):
        return "existence", f"{typ}: {first}"
    if any(s in msg for s in JS_EXISTENCE):
        return "existence", f"{typ}: {first}"
    return "other", f"{typ}: {first}"


def js_results(xml: Path, files: dict[str, str]) -> dict[str, tuple[str, str]]:
    """{title: (kind, first line of the message)} for each check file's title ({path: title})."""
    cases = {(tc.get("classname") or "", tc.get("name") or ""): tc for tc in ET.parse(xml).getroot().iter("testcase")}
    out = {}
    for path, title in files.items():
        if (path, title) in cases:
            out[title] = js_kind(cases[(path, title)])
        elif (path, path) in cases:  # the file could not load: Vitest records one result named after the file
            kind, msg = js_kind(cases[(path, path)])
            out[title] = ("load", msg.split(": ", 1)[-1] if kind != "unreadable" else msg)
        else:
            out[title] = ("missing", "")
    return out


# Two shapes real apps showed (evidence 1, 2026-11-18): the fix each needs, from javascript.md.
JS_HINTS = (
    (
        "matchMedia is not a function",
        "jsdom has no window.matchMedia: add javascript.md's line window.matchMedia ??= ... before render",
    ),
    (
        "may be used only in the context of a <Router>",
        "what was rendered needs a router around it: render"
        " <MemoryRouter initialEntries={[...]}><App /></MemoryRouter> (javascript.md)",
    ),
)


def js_base_problem(title: str, ran: dict[str, tuple[str, str]], base: str) -> str | None:
    problem = _js_base_problem(title, ran, base)
    hint = next((h for s, h in JS_HINTS if problem and s in problem), None)
    return f"{problem}; {hint}" if hint else problem


def _js_base_problem(title: str, ran: dict[str, tuple[str, str]], base: str) -> str | None:
    kind, msg = ran.get(title, ("missing", ""))
    on = base.removeprefix("origin/")
    see = "render the page the person will see, and check its words (javascript.md)"
    if kind == "load" and re.match(r"(test|it|expect) is not defined", msg):  # AsBuild's settings have no globals
        return f'could not load on {on}: {msg}: start the file with import {{ expect, test }} from "vitest"'
    return {
        "assertion": None,
        "passed": f"passes already on {on}: it checks nothing the build will change",
        "skipped": f"is skipped on {on}: a skipped test checks nothing ({msg})",
        "unreadable": f"fails on {on} without saying why (its failure has no type), so AsBuild cannot tell how",
        "load": f"could not load on {on}: {msg}: import only files that exist on {on}, and {see}",
        "existence": f"fails on {on} only because a part of the app does not exist yet ({msg}): {see}",
        "other": f"fails on {on} for a reason other than an assertion: {msg}",
        "missing": f"did not run on {on}",
    }[kind]


def clear(path: Path) -> None:
    """Remove whatever is where the worktree goes (a folder, a file, a link)."""
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists() or path.is_symlink():
        path.unlink()


def run_js(cmd: list[str], cwd: Path, timeout: float) -> subprocess.CompletedProcess:
    """Run Vitest with its output in a file, not a pipe, so a stopped run cannot hang on its children's pipes."""
    with tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as log:
        p = subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        log.seek(0)
        return subprocess.CompletedProcess(cmd, p.returncode, log.read(), "")


def tools_on_base(repo: Path, base: str) -> bool:
    """True when the base's locks.json lists a JavaScript check: an earlier story added the test tools."""
    shown = git(repo, "show", f"{base}:locks.json")
    try:
        files = json.loads(shown.stdout).get("files", {}) if shown.returncode == 0 else {}
    except (ValueError, AttributeError):
        return False
    return isinstance(files, dict) and any(JS_FILE.search(p) for p in files)


def js_tool_problem(repo: Path, base: str) -> str | None:
    """Why the installed Vite and Vitest are outside the table (design §4.4); CannotRun when Vitest is missing."""
    if not (repo / "node_modules" / "vitest" / "vitest.mjs").is_file():
        raise CannotRun(NO_NODE_MODULES if tools_on_base(repo, base) else NO_VITEST)

    def version(name: str) -> tuple[int, ...] | None:
        try:
            meta = json.loads((repo / "node_modules" / name / "package.json").read_text(encoding="utf-8"))
            return js.version_of(meta.get("version"))
        except (OSError, ValueError, AttributeError):
            return None

    vitest = version("vitest")
    why = js.table_problem(version("vite"), vitest) or (None if vitest else "the installed Vitest's version is unknown")
    return f"this project cannot run its checks as AsBuild does: {why}. Run {TOOLS_CMD}" if why else None


def vitest_on_base(repo: Path, base: str, story: str, files: dict[str, str], keep: Path | None) -> dict:
    """Each check file laid over the base and run with AsBuild's settings: {title: (kind, message)}."""
    node = shutil.which("node")
    if not node:
        raise CannotRun("Node.js is not installed. " + js.INSTALL_NODE.format(found=""))
    on = base.removeprefix("origin/")
    inside = repo / JS_WORKTREES
    clear(inside)  # never run anything a pull request or an earlier run left there
    git(repo, "worktree", "prune")
    tree = inside / "base"
    try:
        add = git(repo, "worktree", "add", "--detach", str(tree), base)
        if add.returncode != 0:
            raise CannotRun(f"could not check out {base}: {add.stderr.strip()}")
        rel = Path("tests", "acceptance", story)
        shutil.copytree(repo / rel, tree / rel, dirs_exist_ok=True)
        xml = inside / "story-check-js.xml"
        config = inside / JS_SETTINGS.name  # Vite writes a bundled copy beside its config: never in the plugin
        shutil.copy(JS_SETTINGS, config)
        cmd = [node, str(repo / "node_modules" / "vitest" / "vitest.mjs"), "run", rel.as_posix()]
        cmd += ["--config", str(config), "--root", ".", "--reporter=junit", f"--outputFile={xml}"]
        limit = JS_TIMEOUT * len(files)
        try:
            p = run_js(cmd, tree, limit)
        except subprocess.TimeoutExpired:
            raise CannotRun(f"Vitest did not finish on {on} within {limit} seconds") from None
        if not xml.is_file():
            raise CannotRun(f"Vitest wrote no results on {on}. It said:\n" + "\n".join(p.stdout.splitlines()[-12:]))
        if keep is not None:
            keep.mkdir(parents=True, exist_ok=True)
            shutil.copy(xml, keep / xml.name)
        return js_results(xml, files)
    finally:
        git(repo, "worktree", "remove", "--force", str(tree))
        clear(inside)
        git(repo, "worktree", "prune")


def check_js(repo: Path, story: str, base: str, keep: Path | None, checks: list[dict], files: list[Path]) -> tuple:
    """A JavaScript story's checks: (problems found before the run, per-check lines, problems, tests found)."""
    general: list[str] = []
    titles: dict[str, str] = {}  # title: path
    literals: dict[str, list[str]] = {}
    if any(p.suffix == ".py" for p in files):
        general.append(
            f"tests/acceptance/{story} mixes Python and JavaScript test files: write a story's checks in one"
        )
    for p in files:
        rel = p.relative_to(repo).as_posix()
        if not JS_FILE.search(p.name):
            general.append(f"{rel} is not a check file: a JavaScript story holds only its check files, one per check")
            continue
        try:
            scanned = scan_js(p.read_bytes().decode("utf-8"))
        except UnicodeDecodeError:
            general.append(f"{rel} cannot be read as UTF-8 text")
            continue
        general += [f"{rel}: {problem}" for problem in scanned.problems]
        for t in scanned.titles:
            if t in titles:  # one would be locked without being checked (review round 1, B1)
                general.append(f'"{t}" is in two files, {titles[t]} and {rel}: one file per check, each with its title')
                continue
            titles[t], literals[t] = rel, scanned.literals
    for t in titles:
        carried = [c["id"] for c in checks if carries(t, c["id"])]
        if not carried:
            general.append(f"{t} carries none of this story's check IDs: one test per check, named after it")
        elif len(carried) > 1:
            general.append(f"{t} carries more than one check ID: one test per check, named after it")
        elif not re.match(re.escape(carried[0]) + r"(\s|$)", t):
            general.append(f'{t}: the title must start with its check ID, such as "{carried[0]} ..."')
    tool = js_tool_problem(repo, base) if titles else None
    if tool:
        general.append(tool)
    ran = vitest_on_base(repo, base, story, {p: t for t, p in titles.items()}, keep) if titles and not tool else {}
    lines = []
    count = 0
    for c in checks:
        mine = [t for t in titles if carries(t, c["id"])]
        why = [] if len(mine) == 1 else [f"needs exactly one test named after it, found {len(mine)}"]
        for t in mine:
            if not tool and (problem := js_base_problem(t, ran, base)) is not None:
                why.append(f'"{t}" {problem}')
            for ex in c["examples"]:
                if not example_matches(ex, literals[t]):
                    why.append(
                        f'"{t}" does not check the approved example `{ex}`: assert those exact words inside expect(...)'
                    )
        lines += [f"{c['id']} {w}" for w in why] or [f"{c['id']} ok: {', '.join(mine)}"]
        count += len(why)
    return general, lines, count, len(titles)


# ------------------------------------------------------------------ the run


def lock(repo: Path, story: str, base: str) -> list[str]:
    """Add the story's test files to locks.json. An entry locked on the base (approved by the owner's merge) is
    never changed; an entry this branch wrote earlier is replaced, so a story revised before approval can be
    locked again."""
    shown = git(repo, "show", f"{base}:locks.json")
    try:
        approved = json.loads(shown.stdout).get("files", {}) if shown.returncode == 0 else {}
        if not isinstance(approved, dict):
            raise TypeError("files is not an object")
    except (ValueError, TypeError, AttributeError) as e:
        raise CannotRun(f"locks.json on {base} cannot be read: {e}") from e
    path = repo / "locks.json"
    try:
        doc = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"files": {}}
        files = doc["files"]
        if not isinstance(files, dict):
            raise TypeError("files is not an object")
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise CannotRun(f"locks.json cannot be read: {e}") from e
    mine = f"tests/acceptance/{story}/"
    for rel in [r for r in files if r.startswith(mine) and r not in approved]:
        del files[rel]  # written by an earlier run on this branch: the files as they are now replace them
    problems = []
    folder = repo / "tests" / "acceptance" / story
    owned = "*.py" if not story_files(folder, js_only=True) else "*"  # a JavaScript story locks its own files
    for p in sorted(p for p in folder.rglob(owned) if p.is_file() and (owned == "*.py" or JS_OWNED.search(p.name))):
        rel = p.relative_to(repo).as_posix()
        new = entry(p.read_bytes(), rel)
        if rel in approved and approved[rel] != new:
            on = base.removeprefix("origin/")
            problems.append(f"{rel} is locked on {on} with other content: only the owner changes a locked test")
        files[rel] = new
    if problems:
        return problems
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    return []


SETTINGS = Path(".claude") / "settings.json"


def deny_rule(story: str) -> str:
    """Claude Code's deny rule for one story's locked tests (decision D26)."""
    return f"Edit(/tests/acceptance/{story}/**)"


def read_settings(repo: Path, story: str) -> dict:
    """The project's Claude Code settings, checked before anything is written, so a bad file changes nothing."""
    path = repo / SETTINGS
    again = "; fix it, then run this again"
    if path.parent.exists() and not path.parent.is_dir():
        raise CannotRun(f".claude/settings.json cannot be written: .claude is not a folder{again}")
    try:
        doc = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if not isinstance(doc, dict):
            raise TypeError("it is not an object")
        perms = doc.setdefault("permissions", {})
        if not isinstance(perms, dict):
            raise TypeError("permissions is not an object")
        if not isinstance(perms.setdefault("deny", []), list):
            raise TypeError("permissions.deny is not a list")
    except (ValueError, TypeError, OSError) as e:
        raise CannotRun(f".claude/settings.json cannot be read: {e}{again}") from e
    if deny_rule(story) not in doc["permissions"]["deny"] and path.is_file() and not os.access(path, os.W_OK):
        raise CannotRun(f".claude/settings.json cannot be written: it is read-only{again}")
    return doc


def protect(repo: Path, story: str, doc: dict) -> str:
    """Add the story's deny rule once, keeping every other setting; a file that has it already is left as it is."""
    rule = deny_rule(story)
    deny = doc["permissions"]["deny"]
    done = f"{story} tests protected: {rule} in .claude/settings.json"
    if rule in deny:
        return done
    deny.append(rule)
    path = repo / SETTINGS
    try:
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    except OSError as e:
        raise CannotRun(f".claude/settings.json cannot be written: {e}; fix it, then run this again") from e
    return done


def story_files(folder: Path, js_only: bool = False) -> list[Path]:
    """The story's test folder's files (its JavaScript check files only, with js_only)."""
    found = sorted(p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    return [p for p in found if JS_FILE.search(p.name)] if js_only else found


def check(repo: Path, story: str, base: str, keep: Path | None) -> tuple[list[str], int, int, int]:
    """(output lines, number of checks, number of problems, number of tests). The language is chosen by the story's
    files: any JavaScript check file makes it a JavaScript story (M3-C1); otherwise v0.3.4's Python checks."""
    story_file = repo / "dev-docs" / "stories" / story / "story.md"
    if not story_file.is_file():
        raise CannotRun(f"no story file at {story_file.relative_to(repo).as_posix()}")
    text = story_file.read_text(encoding="utf-8")
    request, checks = parse_story(text)
    general = story_problems(story, text, request, checks)
    folder = repo / "tests" / "acceptance" / story
    if story_files(folder, js_only=True):
        more, lines, count, n_tests = check_js(repo, story, base, keep, checks, story_files(folder))
        general += more
        return general + lines, len(checks), len(general) + count, n_tests
    tests, bad = find_tests(folder)
    general += bad
    for name in tests:
        carried = sum(matches(name, c["id"]) for c in checks)
        if carried == 0:
            general.append(f"{name} carries none of this story's check IDs: one test per check, named after it")
        elif carried > 1:  # one test per check
            general.append(f"{name} carries more than one check ID: one test per check, named after it")
    ran = run_on_base(repo, base, story, keep) if tests else {}
    lines, count = list(general), len(general)
    for c in checks:
        mine = [t for t in tests if matches(t, c["id"])]
        why = []
        if len(mine) != 1:
            why.append(f"needs exactly one test named after it, found {len(mine)}")
        for t in mine:
            if (p := base_problem(t, ran, base)) is not None:
                why.append(f"{t} {p}")
            path, qual = tests[t]
            asserted = python_asserted(path.read_text(encoding="utf-8"), qual)
            for ex in c["examples"]:
                if not example_matches(ex, asserted):
                    why.append(f"{t} does not check the approved example `{ex}`: assert that exact value")
        lines += [f"{c['id']} {w}" for w in why] or [f"{c['id']} ok: {', '.join(mine)}"]
        count += len(why)
    return lines, len(checks), count, len(tests)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="asbuild_story_check.py", description="AsBuild's story-time checks.")
    ap.add_argument("story", help="the story's ID, such as S2")
    ap.add_argument("--base", default="origin/main", help="the branch the build will start from")
    ap.add_argument("--lock", action="store_true", help="when every check passes, lock the tests, add the deny rule")
    ap.add_argument("--keep", type=Path, help="keep pytest's JUnit file in this folder")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        if not re.fullmatch(r"S\d+", a.story):
            raise CannotRun(f"{a.story} is not a story ID such as S2")
        top = git(Path.cwd(), "rev-parse", "--show-toplevel")
        if top.returncode != 0:
            raise CannotRun("this is not a git repository")
        repo = Path(top.stdout.strip())
        python_story = not story_files(repo / "tests" / "acceptance" / a.story, js_only=True)
        if python_story and importlib.util.find_spec("pytest") is None:  # a JavaScript story needs Node, not pytest
            raise CannotRun("pytest is not installed for this Python: run this with the Python that runs your tests")
        if git(repo, "rev-parse", "--verify", "--quiet", a.base + "^{commit}").returncode != 0:
            raise CannotRun(f"no branch {a.base}: fetch it first (git fetch origin)")
        lines, n_checks, n_problems, n_tests = check(repo, a.story, a.base, a.keep)
        if n_problems == 0 and a.lock:
            settings = read_settings(repo, a.story)
            refused = lock(repo, a.story, a.base)
            lines += refused or [protect(repo, a.story, settings)]
            n_problems += len(refused)
    except CannotRun as e:
        print(f"story-time checks could not run: {e}")
        return 2
    print("\n".join(lines))
    if n_problems:
        print("story-time checks failed: fix the tests, never the owner's words or the approved examples")
        return 1
    print(f"story-time checks passed: {n_checks} checks, {n_tests} tests")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
