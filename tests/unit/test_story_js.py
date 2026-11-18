"""M3-C1: the story-time checks for a JavaScript story (plugin/scripts/asbuild_story_check.py; docs/plans/v0.4-M3.md).

The scanner and the example rule are pure functions. The whole run uses a real git repository and a stand-in Vitest:
a Python file at `node_modules/vitest/vitest.mjs`, started by this Python in place of `node`, that records how it was
started and writes the JUnit file the test gives it. No Node, no network.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from xml.sax.saxutils import quoteattr

import pytest

from engine import lock_check
from engine.junit_classify import JS_EXISTENCE, JS_TYPE_ERROR
from engine.langs import JS_TITLE

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugin" / "scripts"))
import asbuild_story_check as sc  # noqa: E402

TITLE1 = "S1-C1 the page says Saved after a click"
TITLE2 = "S1-C2 the list shows 3 items"
C1 = f"""// @vitest-environment jsdom
import {{ render, screen, fireEvent }} from "@testing-library/react";
import {{ MemoryRouter }} from "react-router-dom";
import Index from "../../../src/pages/Index";

test("{TITLE1}", () => {{
  render(<MemoryRouter><Index /></MemoryRouter>);
  fireEvent.click(screen.getByRole("button"));
  expect(document.body.textContent).toContain("Saved");
}});
"""
C2 = f"""// @vitest-environment jsdom
import {{ render }} from "@testing-library/react";
import Index from "../../../src/pages/Index";

test("{TITLE2}", () => {{
  render(<Index />);
  expect(document.querySelectorAll("li").length).toBe(3);
  expect(document.body.textContent).toContain("3 items");
}});
"""
STORY = """# S1: Save the list

## Request (the owner's words, unchanged)

I want a save button that says it saved, and the list to show how many items it has.

## Criteria

| ID | Criterion | Cites |
| --- | --- | --- |
| S1-C1 | After a click the page says `Saved` | Request, sentence 1 |
| S1-C2 | The list shows `3 items` | Request, sentence 1 |

## Plain checklist (approved by the owner; the receipt quotes it word for word)

| ID | plain: | Examples (approved) |
| --- | --- | --- |
| S1-C1 | After you press Save, the page says it saved. | `Saved` |
| S1-C2 | The list says how many items it has. | `3 items` |

## Not in this story

Nothing else.
"""


def scan(text: str) -> sc.JsScan:
    return sc.scan_js(text)


# ------------------------------------------------------------------ the scanner (M3-C1)


def test_M3_C1_a_check_written_as_the_skill_says_is_read():
    s = scan(C1)
    assert s.titles == [TITLE1] and s.problems == []
    assert "Saved" in s.literals and "button" not in s.literals  # getByRole("button") is outside expect


@pytest.mark.parametrize(
    ("source", "said"),
    [
        ('describe("S1", () => {\n  test("S1-C1 x", () => {});\n});\n', "describe"),
        ('test.only("S1-C1 x", () => { expect(1).toBe(1); });\n', "test.only"),
        ('test.skip("S1-C1 x", () => {});\n', "test.skip"),
        ('test.todo("S1-C1 x");\n', "test.todo"),
        ('test.each([1])("S1-C1 x %s", () => {});\n', "test.each"),
        ('test.fails("S1-C1 x", () => {});\n', "test.fails"),
        ('it.skipIf(true)("S1-C1 x", () => {});\n', "it.skipIf"),
        ('xit("S1-C1 x", () => {});\n', "xit"),
        ('suite("S1-C1", () => {});\n', "suite"),
        ('function f() {\n  test("S1-C1 x", () => {});\n}\nf();\n', "inside another block"),
        ("test(`S1-C1 ${name}`, () => {});\n", "literal title"),
        ('test("S1-C1 say \\"hi\\"", () => {});\n', "literal title"),
        ("test(TITLE, () => {});\n", "literal title"),
        ('  test("S1-C1 x", () => {});\n', "start of a line"),
        ('test("S1-C1 x", () => {});\ntest("S1-C2 y", () => {});\n', "one test per file"),
        ("const x = 1;\n", "no test"),
        ('/*\ntest("S1-C1 hidden", () => {});\n*/\n', "comment or string"),
        ('const s = `\ntest("S1-C1 hidden", () => {});\n`;\n', "comment or string"),
    ],
)
def test_M3_C1_the_scanner_refuses_every_form_but_one_plain_top_level_test(source, said):
    problems = scan(source).problems
    assert any(said in p for p in problems), problems


def test_M3_C1_it_is_read_like_test():
    assert scan('it("S1-C1 x", () => {\n  expect(a).toBe("b");\n});\n').titles == ["S1-C1 x"]


def test_M3_C1_comments_strings_and_regular_expressions_never_confuse_the_scanner():
    source = textwrap.dedent(
        """\
        // test("S1-C9 in a line comment")
        /* a block comment with "a quote and test( */
        const re = /it's "not" a string/g;
        const half = total / 2 / 3;
        const t = `a ${ {b: "}"}.b } c`;
        const obj = { test: 1, it: 2 };
        test('S1-C1 the title', () => {
          expect(/x/.test(s)).toBe(true);
          expect(obj.test).not.toBe("Saved");
          const want = "Not literal in expect";
          expect(x).toBe(want);
          expect(y).toMatch(/Regex words/);
          expect(z).toBe(`Template words`);
          expect(w).toBe(`with ${sub}`);
          expect.soft(v).toEqual("Soft words");
          expect(n).toBe(42);
        });
        """
    )
    s = scan(source)
    assert s.problems == [] and s.titles == ["S1-C1 the title"]
    assert {"Saved", "Template words", "Soft words", "42"} <= set(s.literals)
    assert not {"Not literal in expect", "Regex words", "a ", " c"} & set(s.literals)


def test_M3_C1_regular_expression_classes_and_escapes_are_skipped():
    source = 'const r = /[/"]\\/x/;\ntest("S1-C1 x", () => { expect(a).toBe("ok"); });\n'
    s = scan(source)
    assert s.problems == [] and "ok" in s.literals


def test_M3_C1_an_unclosed_string_or_comment_ends_the_file_without_a_crash():
    for source in (
        'test("S1-C1 x", () => { expect(a).toBe("open',
        "/* never closed",
        "`never ${ closed",
        "const r = /[x",
    ):
        scan(source)  # no exception


@pytest.mark.parametrize(
    "source",
    [C1, C2, "it('S1-C3 single quotes', () => {});\n", "test(`S1-C4 backticks`, () => {});\n", "// no test\n"],
)
def test_M3_C1_the_scanners_titles_are_the_locks(source):
    assert scan(source).lock_titles == [next(g for g in m.groups() if g is not None) for m in JS_TITLE.finditer(source)]


def test_M3_C1_the_lock_entry_is_the_engines():
    for name, text in (
        ("tests/acceptance/S1/S1-C1.test.tsx", C1),
        ("tests/acceptance/S1/test_S1_x.py", "def test_S1_C1_x():\n"),
    ):
        raw = text.replace("\n", "\r\n").encode()
        assert sc.entry(raw, name) == lock_check.entry(raw, name)


def test_M3_C1_the_story_check_mirrors_the_engines_failure_rules():
    assert sc.JS_EXISTENCE == JS_EXISTENCE and sc.JS_TYPE_ERROR == JS_TYPE_ERROR


def test_M3_C1_the_plugin_carries_the_engines_settings_byte_for_byte():
    assert sc.JS_SETTINGS == ROOT / "plugin" / "js" / "vitest.acceptance.mjs"
    assert sc.JS_SETTINGS.read_bytes() == (ROOT / "engine" / "js" / "vitest.acceptance.mjs").read_bytes()


@pytest.mark.parametrize(
    ("title", "check", "carried"),
    [
        ("S1-C1 x", "S1-C1", True),
        ("S1-C10 x", "S1-C1", False),
        ("S11-C1 x", "S1-C1", False),
        ("x S1-C1", "S1-C1", True),
    ],
)
def test_M3_C1_a_title_carries_a_check_as_whole_words(title, check, carried):
    assert sc.carries(title, check) is carried


# ------------------------------------------------------------------ results on main


def junit(cases: list[tuple[str, str, str | None, str | None, str]]) -> str:
    """cases: (classname, name, tag or None for a pass, type, message)."""
    body = []
    for classname, name, tag, typ, message in cases:
        inner = ""
        if tag == "skipped":
            inner = "<skipped/>"
        elif tag:
            attrs = f" message={quoteattr(message)}" + (f" type={quoteattr(typ)}" if typ is not None else "")
            inner = f"<{tag}{attrs}>trace</{tag}>"
        body.append(f"<testcase classname={quoteattr(classname)} name={quoteattr(name)}>{inner}</testcase>")
    return f'<?xml version="1.0"?><testsuites><testsuite>{"".join(body)}</testsuite></testsuites>'


P1 = "tests/acceptance/S1/S1-C1.test.tsx"


@pytest.mark.parametrize(
    ("case", "kind"),
    [
        ((P1, TITLE1, "failure", "AssertionError", "expected 'x' to contain 'Saved'"), "assertion"),
        ((P1, TITLE1, None, None, ""), "passed"),
        ((P1, TITLE1, "skipped", None, ""), "skipped"),
        ((P1, TITLE1, "failure", "", "no type"), "unreadable"),
        ((P1, TITLE1, "failure", None, "no type at all"), "unreadable"),
        ((P1, P1, "failure", "Error", "Failed to resolve import ../../../src/pages/Settings"), "load"),
        ((P1, TITLE1, "failure", "ReferenceError", "Settings is not defined"), "existence"),
        ((P1, TITLE1, "failure", "TypeError", "save is not a function"), "existence"),
        ((P1, TITLE1, "failure", "TypeError", "Cannot read properties of null"), "other"),
        ((P1, TITLE1, "failure", "Error", "Element type is invalid: expected a string"), "existence"),
        (
            (P1, TITLE1, "failure", "TestingLibraryElementError", "Unable to find an element with the text: Saved"),
            "other",
        ),
        ((P1, TITLE1, "error", "Error", "setup broke"), "other"),
    ],
)
def test_M3_C1_each_result_on_main_is_read_by_the_engines_rules(tmp_path, case, kind):
    xml = tmp_path / "r.xml"
    xml.write_text(junit([case]), encoding="utf-8")
    assert sc.js_results(xml, {P1: TITLE1})[TITLE1][0] == kind


def test_M3_C1_a_check_with_no_result_is_missing(tmp_path):
    xml = tmp_path / "r.xml"
    xml.write_text(junit([("other.test.tsx", "S1-C9 x", None, None, "")]), encoding="utf-8")
    assert sc.js_results(xml, {P1: TITLE1})[TITLE1][0] == "missing"


# ------------------------------------------------------------------ the whole run, with a stand-in Vitest

FAKE_VITEST = """
import json, os, sys, time, pathlib
args = sys.argv
config = pathlib.Path(args[args.index("--config") + 1]).read_text(encoding="utf-8")
pathlib.Path(os.environ["FAKE_ARGV"]).write_text(json.dumps({"args": args, "cwd": os.getcwd(), "config": config}))
time.sleep(float(os.environ.get("FAKE_SLEEP", "0")))
out = next((a.split("=", 1)[1] for a in args if a.startswith("--outputFile=")), None)
junit = os.environ.get("FAKE_JUNIT")
if out and junit:
    pathlib.Path(out).write_text(pathlib.Path(junit).read_text())
print("fake vitest output line")
sys.exit(1)
"""


def git(cwd: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return p.stdout


@pytest.fixture
def js_repo(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "src" / "pages").mkdir(parents=True)
    (repo / "package.json").write_text('{"devDependencies": {"vite": "^5.4.1"}}\n', encoding="utf-8")
    (repo / "src" / "pages" / "Index.tsx").write_text("export default () => <button>Save</button>;\n", encoding="utf-8")
    (repo / ".gitignore").write_text("node_modules\n", encoding="utf-8")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "-c", "user.name=x", "-c", "user.email=x@example.com", "add", ".")
    git(repo, "-c", "user.name=x", "-c", "user.email=x@example.com", "commit", "-q", "-m", "app")
    for name, version in (("vite", "5.4.21"), ("vitest", "3.2.4")):
        (repo / "node_modules" / name).mkdir(parents=True)
        (repo / "node_modules" / name / "package.json").write_text(json.dumps({"version": version}), encoding="utf-8")
    (repo / "node_modules" / "vitest" / "vitest.mjs").write_text(FAKE_VITEST, encoding="utf-8")
    story = repo / "dev-docs" / "stories" / "S1"
    story.mkdir(parents=True)
    (story / "story.md").write_text(STORY, encoding="utf-8")
    tests = repo / "tests" / "acceptance" / "S1"
    tests.mkdir(parents=True)
    (tests / "S1-C1.test.tsx").write_text(C1, encoding="utf-8")
    (tests / "S1-C2.test.tsx").write_text(C2, encoding="utf-8")
    real_which = sc.shutil.which
    monkeypatch.setattr(sc.shutil, "which", lambda name: sys.executable if name == "node" else real_which(name))
    monkeypatch.setenv("FAKE_ARGV", str(tmp_path / "argv.json"))
    results = tmp_path / "junit.xml"
    results.write_text(
        junit(
            [
                (
                    "tests/acceptance/S1/S1-C1.test.tsx",
                    TITLE1,
                    "failure",
                    "AssertionError",
                    "expected '' to contain 'Saved'",
                ),
                ("tests/acceptance/S1/S1-C2.test.tsx", TITLE2, "failure", "AssertionError", "expected 1 to be 3"),
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("FAKE_JUNIT", str(results))
    monkeypatch.chdir(repo)
    return repo, tmp_path


def run(capsys, *args: str) -> tuple[int, str]:
    code = sc.main(["S1", "--base", "main", *args])
    return code, capsys.readouterr().out


def test_M3_C1_a_javascript_story_passes_and_locks(js_repo, capsys):
    repo, tmp = js_repo
    code, out = run(capsys, "--lock")
    assert code == 0, out
    assert f"S1-C1 ok: {TITLE1}" in out and f"S1-C2 ok: {TITLE2}" in out
    assert "story-time checks passed: 2 checks, 2 tests" in out
    files = json.loads((repo / "locks.json").read_text(encoding="utf-8"))["files"]
    for name, text in (("S1-C1.test.tsx", C1), ("S1-C2.test.tsx", C2)):
        rel = f"tests/acceptance/S1/{name}"
        assert files[rel] == lock_check.entry(text.encode(), rel)
    assert "Edit(/tests/acceptance/S1/**)" in (repo / ".claude" / "settings.json").read_text(encoding="utf-8")
    started = json.loads((tmp / "argv.json").read_text())
    args = started["args"]
    assert args[0] == str(repo / "node_modules" / "vitest" / "vitest.mjs")
    assert args[1:3] == ["run", "tests/acceptance/S1"]
    # A copy in the run's own folder: Vite writes a bundled copy beside its config, and the plugin's folder may be
    # read-only (found in evidence 1, 2026-11-18).
    config = Path(args[args.index("--config") + 1])
    assert config == repo / ".asbuild-story" / "vitest.acceptance.mjs"
    assert started["config"] == sc.JS_SETTINGS.read_text(encoding="utf-8")
    assert args[args.index("--root") + 1] == "." and "--reporter=junit" in args
    assert Path(started["cwd"]).parent == repo / ".asbuild-story"  # inside the checkout: node_modules is found
    assert not (repo / ".asbuild-story").exists()  # removed after the run
    assert "worktree" not in git(repo, "worktree", "list").split("\n", 1)[-1]


def test_M3_C1_keep_saves_the_results(js_repo, capsys):
    repo, tmp = js_repo
    code, _ = run(capsys, "--keep", str(tmp / "kept"))
    assert code == 0 and (tmp / "kept" / "story-check-js.xml").is_file()


@pytest.mark.parametrize(
    ("case", "said"),
    [
        ((TITLE1, None, None, ""), "passes already on main"),
        ((TITLE1, "skipped", None, ""), "is skipped on main"),
        ((TITLE1, "failure", "", "x"), "without saying why"),
        ((P1, "failure", "Error", "Failed to resolve import ../x"), "could not load on main"),
        ((TITLE1, "failure", "ReferenceError", "Settings is not defined"), "does not exist yet"),
        ((TITLE1, "failure", "TestingLibraryElementError", "Unable to find"), "for a reason other than an assertion"),
        (("S1-C9 other", None, None, ""), "did not run on main"),
    ],
)
def test_M3_C1_a_check_that_does_not_fail_on_main_by_an_assertion_is_refused(js_repo, capsys, case, said):
    repo, tmp = js_repo
    name, tag, typ, message = case
    (tmp / "junit.xml").write_text(
        junit(
            [
                (P1, name, tag, typ, message),
                ("tests/acceptance/S1/S1-C2.test.tsx", TITLE2, "failure", "AssertionError", "expected 1 to be 3"),
            ]
        ),
        encoding="utf-8",
    )
    code, out = run(capsys, "--lock")
    assert code == 1
    assert f'S1-C1 "{TITLE1}" ' in out and said in out
    assert "S1-C2 ok" in out and not (repo / "locks.json").exists()


def test_M3_C1_an_example_not_asserted_literally_is_refused(js_repo, capsys):
    repo, _ = js_repo
    path = repo / "tests" / "acceptance" / "S1" / "S1-C1.test.tsx"
    path.write_text(C1.replace('toContain("Saved")', "toContain(WANT)"), encoding="utf-8")
    code, out = run(capsys)
    assert code == 1
    assert (
        f'S1-C1 "{TITLE1}" does not check the approved example `Saved`: assert those exact words inside expect(...)'
        in out
    )


def test_M3_C1_scanner_problems_and_naming_problems_are_listed(js_repo, capsys):
    repo, _ = js_repo
    folder = repo / "tests" / "acceptance" / "S1"
    (folder / "S1-C1.test.tsx").write_text(C1.replace("test(", "test.only("), encoding="utf-8")
    (folder / "S1-C2.test.tsx").write_text(C2.replace("S1-C2", "S1-C1 and S1-C2"), encoding="utf-8")
    (folder / "S1-C3.test.tsx").write_text(C2.replace("S1-C2", "S2-C1"), encoding="utf-8")
    (folder / "S1-C4.test.tsx").write_text(C2.replace("S1-C2 the", "The S1-C2"), encoding="utf-8")
    code, out = run(capsys)
    assert code == 1
    assert "tests/acceptance/S1/S1-C1.test.tsx: test.only" in out
    assert "carries more than one check ID" in out
    assert "carries none of this story's check IDs" in out
    assert "must start with its check ID" in out
    assert "S1-C2 needs exactly one test named after it, found 2" in out


def test_M3_C1_a_story_mixing_languages_or_holding_other_files_is_refused(js_repo, capsys):
    repo, _ = js_repo
    folder = repo / "tests" / "acceptance" / "S1"
    (folder / "helpers.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (folder / "test_S1_more.py").write_text("def test_S1_C1_x():\n    assert False\n", encoding="utf-8")
    code, out = run(capsys)
    assert code == 1
    assert "tests/acceptance/S1/helpers.ts is not a check file" in out
    assert "mixes Python and JavaScript" in out


def test_M3_C1_a_file_that_cannot_be_read_as_text_is_refused(js_repo, capsys):
    repo, _ = js_repo
    (repo / "tests" / "acceptance" / "S1" / "S1-C2.test.tsx").write_bytes(b"\xff\xfe\x00bad")
    code, out = run(capsys)
    assert code == 1 and "S1-C2.test.tsx cannot be read as UTF-8 text" in out


@pytest.mark.parametrize(
    ("vite", "vitest", "said"),
    [("4.5.3", "3.2.4", "Vite 4.5.3"), ("5.4.21", "4.1.12", "Vitest 4.1.12"), (None, "3.2.4", "not built with Vite")],
)
def test_M3_C1_a_vite_or_vitest_off_the_table_is_refused(js_repo, capsys, vite, vitest, said):
    repo, tmp = js_repo
    for name, version in (("vite", vite), ("vitest", vitest)):
        meta = repo / "node_modules" / name / "package.json"
        if version is None:
            meta.unlink()
        else:
            meta.write_text(json.dumps({"version": version}), encoding="utf-8")
    code, out = run(capsys)
    assert code == 1 and said in out and 'asbuild_js.py" tools' in out
    assert not (tmp / "argv.json").exists()  # nothing ran


def test_M3_C1_no_vitest_installed_cannot_run(js_repo, capsys):
    repo, _ = js_repo
    (repo / "node_modules" / "vitest" / "vitest.mjs").unlink()
    code, out = run(capsys)
    assert code == 2 and "Vitest is not installed" in out and 'asbuild_js.py" tools' in out


def test_M3_C1_unreadable_vitest_metadata_reads_as_off_the_table(js_repo, capsys):
    repo, _ = js_repo
    (repo / "node_modules" / "vitest" / "package.json").write_text("{ broken", encoding="utf-8")
    code, out = run(capsys)
    assert code == 1 and "Vitest" in out


def test_M3_C1_no_node_cannot_run(js_repo, capsys, monkeypatch):
    monkeypatch.setattr(sc.shutil, "which", lambda name: None)
    code, out = run(capsys)
    assert code == 2 and "Node.js is not installed" in out


def test_M3_C1_vitest_that_writes_no_results_cannot_run(js_repo, capsys, monkeypatch):
    monkeypatch.delenv("FAKE_JUNIT")
    code, out = run(capsys)
    assert code == 2 and "Vitest wrote no results on main" in out and "fake vitest output line" in out


def test_M3_C1_vitest_that_runs_too_long_cannot_run(js_repo, capsys, monkeypatch):
    monkeypatch.setattr(sc, "JS_TIMEOUT", 1)
    monkeypatch.setenv("FAKE_SLEEP", "5")
    code, out = run(capsys)
    assert code == 2 and "did not finish on main within 2 seconds" in out  # 1 second per check file
    assert not (js_repo[0] / ".asbuild-story").exists()


def test_M3_C1_a_worktree_that_cannot_be_made_cannot_run(js_repo, capsys):
    code, out = run(capsys, "--base", "no-such-branch")
    assert code == 2


def test_M3_C1_something_in_the_way_of_the_worktree_folder_is_cleared(js_repo, capsys):
    repo, _ = js_repo
    (repo / ".asbuild-story").write_text("a file where the folder goes", encoding="utf-8")
    code, out = run(capsys)
    assert code == 0, out
    assert not (repo / ".asbuild-story").exists()
    (repo / ".asbuild-story" / "base").mkdir(parents=True)
    (repo / ".asbuild-story" / "base" / "planted.test.tsx").write_text("x", encoding="utf-8")
    assert run(capsys)[0] == 0


def test_M3_C1_add_worktree_failure_is_reported(js_repo, capsys, monkeypatch):
    real = sc.git

    def git_fails_on_add(repo, *args):
        if args[:2] == ("worktree", "add"):
            return subprocess.CompletedProcess(args, 128, "", "fatal: cannot add")
        return real(repo, *args)

    monkeypatch.setattr(sc, "git", git_fails_on_add)
    code, out = run(capsys)
    assert code == 2 and "could not check out main: fatal: cannot add" in out


def test_M3_C1_a_python_story_is_unchanged_by_the_javascript_path(tmp_path, monkeypatch, capsys):
    from tests.acceptance.S2.test_S2_story_checks import GOOD_C1, GOOD_C2, make_repo

    repo = make_repo(tmp_path, GOOD_C1 + GOOD_C2)
    monkeypatch.chdir(repo)
    assert sc.main(["S1", "--base", "main"]) == 0
    assert "story-time checks passed: 2 checks, 2 tests" in capsys.readouterr().out


def test_M3_C1_the_stand_in_runs_through_a_real_process(js_repo):
    p = sc.run_js([sys.executable, "-c", "print('hello')"], js_repo[0], 30)
    assert p.returncode == 0 and "hello" in p.stdout
    assert os.environ["FAKE_ARGV"]


def test_M3_C1_a_javascript_story_needs_no_pytest(js_repo, capsys, monkeypatch):
    monkeypatch.setattr(sc.importlib.util, "find_spec", lambda name: None)
    code, out = run(capsys)
    assert code == 0, out


def test_M3_C1_the_rarer_shapes_of_strings_templates_and_expect():
    source = (
        'const open = "never closed\n'
        "const esc = `a \\` b`;\n"
        "const nest = `x ${ `inner ${1}` /* note */ + 2 // end\n } y`;\n"
        'test("S1-C1 x", () => {\n  const e = expect;\n  expect(a).toBe("ok");\n});\n'
    )
    s = scan(source)
    assert s.titles == ["S1-C1 x"] and "ok" in s.literals and s.problems == []


def test_M3_C1_the_story_check_finds_its_javascript_facts_when_loaded_by_path(monkeypatch):
    import importlib.util

    here = str(ROOT / "plugin" / "scripts")
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != here])
    monkeypatch.delitem(sys.modules, "asbuild_js")
    path = ROOT / "plugin" / "scripts" / "asbuild_story_check.py"
    spec = importlib.util.spec_from_file_location("story_check_by_path", path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "story_check_by_path", module)  # dataclasses look their module up
    spec.loader.exec_module(module)
    assert module.js.VITEST_FOR[5] == "3.2.4" and here in sys.path


@pytest.mark.parametrize("name", ["test", "expect", "it"])
def test_M3_C1_a_check_without_vitests_import_is_told_the_import(js_repo, capsys, name):
    repo, tmp = js_repo
    (tmp / "junit.xml").write_text(
        junit(
            [
                (P1, P1, "failure", "ReferenceError", f"{name} is not defined"),
                ("tests/acceptance/S1/S1-C2.test.tsx", TITLE2, "failure", "AssertionError", "expected 1 to be 3"),
            ]
        ),
        encoding="utf-8",
    )
    code, out = run(capsys)
    assert code == 1
    assert (
        f'could not load on main: {name} is not defined: start the file with import {{ expect, test }} from "vitest"'
        in out
    )
