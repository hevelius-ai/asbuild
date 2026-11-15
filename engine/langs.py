"""The language seam (D47; docs/plans/v0.4-design.md §4.1): one row per language, keyed by the file extension of
the locked acceptance files.

Each row says which result files the untrusted job writes for it, how a test's name carries a check ID, how a locked
test is found in the results, how the lock lists a file's tests, how the story is read from a result, which failure
rules apply and which file names it adds to the protected list. Python's row is v0.3.4's code, moved, except that
names now split on any non-letter, non-digit (M1-C3; the same result for every Python name, P-ENG-1). A language is in
play only when main's `locks.json` holds a file it owns (`in_play`); its protected names apply when main's or the pull
request's `locks.json` does (`owners`, L5 B).

Trusted-side code: it reads data only.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from engine.junit_classify import Key, classify, classify_js

NAME_SPLIT = re.compile(r"[\W_]")  # any character that is not a letter or a digit
TEST_DEF = re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)\s*\(", re.M)
# A top-level `test(` or `it(` call with a literal title: no indentation, no escapes, no `$` in a backtick title.
JS_TITLE = re.compile(r"""^(?:test|it)\s*\(\s*(?:"([^"\\\n]*)"|'([^'\\\n]*)'|`([^`\\$\n]*)`)""", re.M)
JS_STORY = re.compile(r"^tests/acceptance/(S\d+)/")


def _carries(name: str, check: str) -> bool:
    toks = NAME_SPLIT.split(name.lower())
    want = check.lower().split("-")
    return any(toks[i : i + len(want)] == want for i in range(len(toks)))


@dataclass(frozen=True)
class Lang:
    name: str
    owns: re.Pattern[str]  # the locked files it owns, by extension
    c3_tail: re.Pattern[str]  # its fails-before result files, by the end of their name
    pr_file: str  # the full run, with the project's own settings
    acc_file: str  # the agreed checks, hardened
    classify: Callable  # the failure rules
    protected: tuple[str, ...]  # file names it adds to the protected list (L5 B)
    hardened_p2p: bool  # another story's check failing in the hardened run counts as broken (design §4.4)
    _matches: Callable[[str, str], bool]
    _result_keys: Callable[[str, str], list[Key]]
    _locked_key: Callable[[str, str], Key]
    _before: Callable[[dict[Key, str], Key], str | None]
    _story_of: Callable[[str], str | None]
    _lock_tests: Callable[[str], list[str]]

    def matches(self, test_name: str, check: str) -> bool:
        """True when the test's name carries the check ID as whole words: S1-C1, not S1-C10 or S11-C1."""
        return self._matches(test_name, check)

    def result_keys(self, classname: str, name: str) -> list[Key]:
        """The keys a result is found under when the lock's tests are looked up."""
        return self._result_keys(classname, name)

    def locked_key(self, path: str, test: str) -> Key:
        """The key of one test the lock lists for a file."""
        return self._locked_key(path, test)

    def before(self, c3: dict[Key, str], key: Key) -> str | None:
        """How a test behaved laid over main; None when there is no readable result."""
        return self._before(c3, key)

    def story_of(self, classname: str) -> str | None:
        return self._story_of(classname)

    def lock_tests(self, text: str) -> list[str]:
        return self._lock_tests(text)


# ---------------------------------------------------------------- Python (v0.3.4's code, moved; the split is M1-C3's)
def _py_matches(test_name: str, check: str) -> bool:
    return _carries(test_name.split("[", 1)[0], check)  # a pytest parameter is not part of the name


def _py_result_keys(classname: str, name: str) -> list[Key]:
    """A test is found by its file's name in any part of its class name (a test inside a class has the class as
    the last part); a parametrised test by its name without the parameter."""
    return [(part, name.split("[", 1)[0]) for part in classname.split(".")]


def _py_locked_key(path: str, test: str) -> Key:
    return (path.rsplit("/", 1)[-1].removesuffix(".py"), test)


def _py_before(c3: dict[Key, str], key: Key) -> str | None:
    """A collection error of its file (pytest records it with an empty classname and the module's dotted path as
    the name) counts for every test in that file."""
    if key in c3:
        return c3[key]
    parts = key[0].split(".")
    for i in range(len(parts), 0, -1):
        hit = c3.get(("", ".".join(parts[:i])))
        if hit is not None:
            return hit
    return None


def _py_story_of(classname: str) -> str | None:
    parts = classname.split(".")
    return parts[2] if len(parts) > 3 and parts[:2] == ["tests", "acceptance"] else None


PYTHON = Lang(
    name="python",
    owns=re.compile(r"\.py$"),
    c3_tail=re.compile(r"_py\.xml$"),
    pr_file="pr.xml",
    acc_file="acceptance.xml",
    classify=classify,
    protected=(),  # Python's names apply in every repository (engine/verdict.py PROTECTED_NAMES)
    hardened_p2p=False,
    _matches=_py_matches,
    _result_keys=_py_result_keys,
    _locked_key=_py_locked_key,
    _before=_py_before,
    _story_of=_py_story_of,
    _lock_tests=TEST_DEF.findall,
)


# ---------------------------------------------------------------- JavaScript and TypeScript (Vitest)
def _js_before(c3: dict[Key, str], key: Key) -> str | None:
    """A file that could not load is one result named after the file: it counts for every check in that file. A
    failure with no type is unreadable: no result."""
    hit = c3.get(key)
    if hit is None:
        hit = c3.get((key[0], key[0]))
    return None if hit == "unreadable" else hit


def _js_story_of(path: str) -> str | None:
    m = JS_STORY.match(path)
    return m.group(1) if m else None


def _js_titles(text: str) -> list[str]:
    return [next(g for g in m.groups() if g is not None) for m in JS_TITLE.finditer(text)]


JAVASCRIPT = Lang(
    name="javascript",
    owns=re.compile(r"\.[cm]?[jt]sx?$"),
    c3_tail=re.compile(r"_[cm]?[jt]sx?\.xml$"),
    pr_file="pr-js.xml",
    acc_file="acceptance-js.xml",
    classify=classify_js,
    protected=(
        "package.json",
        "npm-shrinkwrap.json",
        ".npmrc",
        "bun.lockb",
        ".yarnrc*",
        "pnpm-workspace.yaml",
        "vite.config.*",
        "vitest.config.*",
        "vitest.workspace.*",
        "tsconfig*.json",
        "jsconfig.json",
        ".nvmrc",
        ".node-version",
    ),
    hardened_p2p=True,
    _matches=_carries,
    _result_keys=lambda classname, name: [(classname, name)],
    _locked_key=lambda path, test: (path, test),
    _before=_js_before,
    _story_of=_js_story_of,
    _lock_tests=_js_titles,
)

ROWS = (PYTHON, JAVASCRIPT)


def owner(path: str) -> Lang | None:
    """The row that owns a locked file, or None (a data file, for example)."""
    return next((r for r in ROWS if r.owns.search(path)), None)


def for_path(path: str) -> Lang:
    """The row whose rules read a locked file: its owner, else Python's (v0.3.4's rule for every file)."""
    return owner(path) or PYTHON


def owners(lock_files: dict) -> list[Lang]:
    """The rows owning at least one file of a lock, in table order."""
    return [r for r in ROWS if any(r.owns.search(p) for p in lock_files)]


def in_play(main_lock_files: dict) -> list[Lang]:
    """The languages whose results a build needs: those owning a file in main's lock; Python's when none does."""
    return owners(main_lock_files) or [PYTHON]


def for_c3(filename: str) -> Lang:
    """The row whose rules read one fails-before result file (its name ends with the checked file's extension)."""
    return next((r for r in ROWS if r.c3_tail.search(filename)), PYTHON)
