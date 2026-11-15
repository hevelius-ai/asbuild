"""Unit tests for v0.4.0's milestone M1 (docs/plans/v0.4-M1.md): the language seam and the JavaScript engine rules.

Each test is named after the criterion it proves (M1-C1 to M1-C8). The conformance suite (tests/conformance) runs the
agreed cases end to end; these tests reach the branches the cases do not.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

from engine import langs
from engine.junit_classify import classify_js, load
from engine.lint_plain import lint
from engine.lock_check import entry
from engine.receipt import plain_file, render
from engine.verdict import Facts, judge, protected

JS1 = "tests/acceptance/S1/S1-C1.test.tsx"
T1 = "S1-C1 shows the word count"
JS1_SRC = (
    '// @vitest-environment jsdom\nimport { test, expect } from "vitest";\n'
    f'test("{T1}", () => {{\n  expect(1).toBe(1);\n}});\n'
).encode()
PY = "tests/acceptance/S1/test_S1_count.py"
PY_SRC = b"def test_S1_C1_counts_words():\n    assert False\n"
STORY = (
    b"# S1: Count words\n\n## Plain checklist\n\n| ID | plain: |\n| --- | --- |\n"
    b'| S1-C1 | When you type some words, the page shows how many there are, like "words: 3". |\n'
)


def codes(v):
    return [c["code"] for c in v["codes"]]


def case(tag: str, name: str, classname: str, typ: str | None, msg: str = "boom"):
    tc = ET.Element("testcase", {"classname": classname, "name": name})
    if tag:
        attrs = {"message": msg}
        if typ is not None:
            attrs["type"] = typ
        ET.SubElement(tc, tag, attrs)
    return tc


def vitest(rows: list[tuple[str, str, str | None, str]]) -> str:
    """Vitest's JUnit form; each row is (path, title, failure type or None for a pass, message)."""
    out = ['<?xml version="1.0" encoding="UTF-8" ?>\n<testsuites>']
    for path, title, typ, msg in rows:
        inner = "" if typ is None else f'<failure message="{msg}" type="{typ}">x</failure>'
        out.append(
            f'<testsuite name="{path}"><testcase classname="{path}" name="{title}">{inner}</testcase></testsuite>'
        )
    return "".join(out) + "</testsuites>\n"


def lockfile(files: dict[str, bytes]) -> bytes:
    return (json.dumps({"files": {p: entry(raw, p) for p, raw in files.items()}}, indent=2) + "\n").encode()


def js_facts(tmp_path, *, evidence: dict[str, str], branch="build/S1", changed=("src/Counter.tsx",), main=None):
    main = main or {"locks.json": lockfile({JS1: JS1_SRC}), "dev-docs/stories/S1/story.md": STORY, JS1: JS1_SRC}
    ev = tmp_path / "evidence"
    for name, text in evidence.items():
        (ev / name).parent.mkdir(parents=True, exist_ok=True)
        (ev / name).write_text(text, encoding="utf-8")
    return Facts(
        branch=branch,
        pr_number=7,
        pr_url="https://github.com/o/r/pull/7",
        head_sha="d" * 40,
        files_changed=list(changed),
        main_files=dict(main),
        head_files=dict(main),
        evidence=str(ev),
    )


PY_EV = {
    "pr.xml": '<testsuites><testcase classname="tests.acceptance.S1.test_S1_count" name="test_S1_C1_counts_words"/>'
    "</testsuites>",
    "acceptance.xml": '<testsuites><testcase classname="tests.acceptance.S1.test_S1_count" '
    'name="test_S1_C1_counts_words"/></testsuites>',
    "c3/tests_acceptance_s1_test_s1_count_py.xml": '<testsuites><testcase classname="tests.acceptance.S1.'
    'test_S1_count" name="test_S1_C1_counts_words"><failure message="AssertionError: x">x</failure></testcase>'
    "</testsuites>",
}


def ok_evidence(acc_type=None, c3_type="AssertionError", pr_extra=(), acc_extra=()) -> dict[str, str]:
    return {
        "pr-js.xml": vitest([("src/a.test.ts", "unit", None, ""), (JS1, T1, None, ""), *pr_extra]),
        "acceptance-js.xml": vitest([(JS1, T1, acc_type, "expected 2 to be 3"), *acc_extra]),
        "c3/tests_acceptance_s1_s1_c1_test_tsx.xml": vitest([(JS1, T1, c3_type, "expected 2 to be 3")]),
    }


# ---------------------------------------------------------------- M1-C1 the seam
def test_M1_C1_rows_are_keyed_by_the_locked_files_extension():
    assert langs.owner(PY) is langs.PYTHON
    for ext in ("ts", "tsx", "js", "jsx", "mjs", "cjs", "mts", "cts"):
        assert langs.owner(f"tests/acceptance/S1/S1-C1.test.{ext}") is langs.JAVASCRIPT, ext
    assert langs.owner("tests/acceptance/S1/data/words.json") is None
    assert langs.for_path("tests/acceptance/S1/data/words.json") is langs.PYTHON  # today's rule for any other file
    assert langs.for_path("") is langs.PYTHON


def test_M1_C1_a_language_is_in_play_only_when_the_lock_holds_a_file_it_owns():
    assert langs.in_play({}) == [langs.PYTHON]  # no agreed checks yet: today's Python behaviour
    assert langs.in_play({PY: {}}) == [langs.PYTHON]
    assert langs.in_play({JS1: {}}) == [langs.JAVASCRIPT]
    assert langs.in_play({PY: {}, JS1: {}}) == [langs.PYTHON, langs.JAVASCRIPT]
    assert langs.in_play({"tests/acceptance/S1/data/x.json": {}}) == [langs.PYTHON]
    assert langs.owners({}) == [] and langs.owners({JS1: {}, "a.json": {}}) == [langs.JAVASCRIPT]


def test_M1_C1_fails_before_files_are_read_by_the_row_their_name_ends_with():
    assert langs.for_c3("tests_acceptance_s1_s1_c1_test_tsx.xml") is langs.JAVASCRIPT
    assert langs.for_c3("tests_acceptance_s1_test_s1_count_py.xml") is langs.PYTHON
    assert langs.for_c3("anything.xml") is langs.PYTHON


def test_M1_C1_a_build_that_adds_a_javascript_lock_entry_does_not_put_javascript_in_play(tmp_path):
    """Premortem 2: the evidence rule reads main's lock, never the pull request's."""
    main = {"locks.json": lockfile({PY: PY_SRC}), "dev-docs/stories/S1/story.md": STORY, PY: PY_SRC}
    ev = dict(PY_EV, **{"js-install.txt": "EBADPLATFORM\n"})
    f = js_facts(tmp_path, evidence=ev, changed=["locks.json", JS1], main=main)
    f.head_files = dict(main, **{"locks.json": lockfile({PY: PY_SRC, JS1: JS1_SRC}), JS1: JS1_SRC})
    v = judge(f)
    assert v["verdict"] == "WAITING FOR YOU" and "PROTECTED_CHANGED" in codes(v)
    assert "NO_RESULTS" not in codes(v) and "INSTALL_FAILED" not in codes(v)
    assert v["items"][0]["status"] == "check_changed"  # judged from Python's results alone


# ---------------------------------------------------------------- M1-C2 JavaScript results
def test_M1_C2_javascript_failure_rules_by_type_and_message():
    p = JS1
    assert classify_js(case("", T1, p, None)) == ("passed", "")
    assert classify_js(case("skipped", T1, p, None, "todo"))[0] == "skipped"
    assert classify_js(case("failure", T1, p, "AssertionError", "Cannot find module x"))[0] == "strong"
    assert classify_js(case("failure", T1, p, "ReferenceError", "Counter is not defined"))[0] == "existence-only"
    assert classify_js(case("failure", T1, p, "TypeError", "Counter is not a function"))[0] == "existence-only"
    assert classify_js(case("failure", T1, p, "TypeError", "Counter is not a constructor"))[0] == "existence-only"
    assert classify_js(case("failure", T1, p, "TypeError", "Cannot read properties of undefined"))[0] == "strong"
    for msg in (
        "Cannot find module '../src/Counter'",
        "Cannot find package 'left-pad'",
        'Failed to resolve import "@/x"',
        "The requested module './x' does not provide an export named 'Counter'",
        "Element type is invalid: expected a string",
    ):
        assert classify_js(case("failure", T1, p, "Error", msg))[0] == "existence-only", msg
    assert classify_js(case("failure", p, p, "Error", "Transform failed"))[0] == "existence-only"  # file not loaded
    assert classify_js(case("failure", p, p, "AssertionError", "expected 1 to be 2"))[0] == "existence-only"
    assert classify_js(case("error", T1, p, "RangeError", "too deep"))[0] == "strong"
    assert classify_js(case("failure", T1, p, "", "something failed"))[0] == "unreadable"
    assert classify_js(case("failure", T1, p, None, "something failed"))[0] == "unreadable"


def test_M1_C2_load_uses_the_rule_it_is_given(tmp_path):
    x = tmp_path / "a.xml"
    x.write_text(vitest([(JS1, T1, "Error", "Cannot find module 'x'")]), encoding="utf-8")
    assert load(str(x)) == {(JS1, T1): "strong"}  # Python's rule keys on the message's first word
    assert load(str(x), classify_js) == {(JS1, T1): "existence-only"}


def test_M1_C2_a_repeated_name_never_lets_a_pass_hide_a_failure(tmp_path):
    """`it.each` without a placeholder, or two tests with one title, give Vitest results the same name."""
    x = tmp_path / "a.xml"
    rows = [("src/a.test.ts", "handles input", t, "expected 1 to be 2") for t in ("AssertionError", None)]
    x.write_text(vitest(rows), encoding="utf-8")
    assert load(str(x), classify_js) == {("src/a.test.ts", "handles input"): "strong"}
    x.write_text(vitest(rows[::-1]), encoding="utf-8")
    assert load(str(x), classify_js) == {("src/a.test.ts", "handles input"): "strong"}
    ev = ok_evidence(pr_extra=rows)
    v = judge(js_facts(tmp_path, evidence=ev))
    assert v["verdict"] == "NOT PROVEN" and "PASS_TO_PASS_BROKEN" in codes(v)
    # nor a skip, in either order (an `it.todo` beside a failing `it` of the same title)
    fail = '<testcase classname="a.test.ts" name="x"><failure message="m" type="AssertionError">x</failure></testcase>'
    skip = '<testcase classname="a.test.ts" name="x"><skipped/></testcase>'
    for body in (fail + skip, skip + fail):
        x.write_text(f"<testsuites><testsuite>{body}</testsuite></testsuites>", encoding="utf-8")
        assert load(str(x), classify_js) == {("a.test.ts", "x"): "strong"}, body


def test_M1_C1_python_keeps_v034s_result_for_a_failure_then_a_teardown_error(tmp_path):
    """pytest writes two test cases with one name when a test fails and its teardown errors (proved with pytest 9.2):
    v0.3.4 read the second; Python's row must still do so (the repeated-name rule only stops a pass hiding a
    failure)."""
    x = tmp_path / "c3.xml"
    x.write_text(
        '<testsuites><testsuite><testcase classname="tests.acceptance.S1.test_S1_count" name="test_S1_C1_x">'
        '<failure message="assert False">x</failure></testcase>'
        '<testcase classname="tests.acceptance.S1.test_S1_count" name="test_S1_C1_x">'
        '<error message="failed on teardown with &quot;RuntimeError: boom&quot;">x</error></testcase>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    assert load(str(x)) == {("tests.acceptance.S1.test_S1_count", "test_S1_C1_x"): "existence-only"}


def test_M1_C2_a_javascript_repository_reads_its_own_result_files(tmp_path):
    v = judge(js_facts(tmp_path, evidence=ok_evidence()))
    assert v["verdict"] == "PROVEN", v["codes"]
    assert v["pass_to_pass"] == {"total": 1, "broken": 0, "unbuilt": 0}
    assert v["rows"][0]["with"] == {f"{JS1}::{T1}": "passed"}


def test_M1_C2_python_result_files_still_count_in_a_javascript_repository(tmp_path):
    """An in-play language's files are required; another language's, when present, still show breakage."""
    ev = ok_evidence()
    ev["pr.xml"] = (
        '<testsuites><testsuite><testcase classname="tests.unit.test_api" name="test_api">'
        '<failure message="AssertionError: assert 1 == 2">x</failure></testcase></testsuite></testsuites>'
    )
    v = judge(js_facts(tmp_path, evidence=ev))
    assert v["verdict"] == "NOT PROVEN" and "PASS_TO_PASS_BROKEN" in codes(v)
    assert "NO_RESULTS" not in codes(v)


def test_M1_C2_a_check_failing_after_with_an_empty_type_still_fails(tmp_path):
    v = judge(js_facts(tmp_path, evidence=ok_evidence(acc_type="")))
    assert v["verdict"] == "NOT PROVEN" and v["items"][0]["status"] == "fails"


def test_M1_C2_an_unreadable_fails_before_result_gives_unresolved(tmp_path):
    v = judge(js_facts(tmp_path, evidence=ok_evidence(c3_type="")))
    assert v["verdict"] == "UNRESOLVED" and "NO_BEFORE_RESULT" in codes(v)


# ---------------------------------------------------------------- M1-C3 names and lookups
def test_M1_C3_matches_splits_on_any_non_letter_non_digit():
    js = langs.JAVASCRIPT
    assert js.matches("S1-C1 shows the word count", "S1-C1")
    assert js.matches("shows the count (S1-C1)", "S1-C1")
    assert js.matches("tests/acceptance/S1/S1-C1.test.tsx", "S1-C1")  # a file that could not load
    assert not js.matches("S1-C10 shows", "S1-C1") and not js.matches("S11-C1 shows", "S1-C1")
    assert js.matches("renders [S1-C1]", "S1-C1")  # no parameter suffix to strip in Vitest
    py = langs.PYTHON
    assert py.matches("test_S1_C1_counts", "S1-C1") and py.matches("test_x_S1_C1[case-a]", "S1-C1")
    assert not py.matches("test_S1_C10_counts", "S1-C1")
    assert not py.matches("test_x[S1_C1]", "S1-C1")  # the pytest parameter is not the name, as today


def test_M1_C3_story_of_reads_the_path():
    assert langs.JAVASCRIPT.story_of(JS1) == "S1"
    assert langs.JAVASCRIPT.story_of("tests/acceptance/S12/x/S12-C3.test.ts") == "S12"
    assert langs.JAVASCRIPT.story_of("src/a.test.ts") is None
    assert langs.PYTHON.story_of("tests.acceptance.S2.test_S2_x") == "S2"
    assert langs.PYTHON.story_of("tests.unit.test_app") is None


def test_M1_C3_locked_javascript_tests_are_found_by_path_and_title(tmp_path):
    js = langs.JAVASCRIPT
    assert js.locked_key(JS1, T1) == (JS1, T1)
    assert js.result_keys(JS1, T1) == [(JS1, T1)]
    ev = ok_evidence()
    ev["acceptance-js.xml"] = vitest([(JS1, "S1-C1 renamed", None, "")])
    v = judge(js_facts(tmp_path, evidence=ev))
    assert {"code": "LOCK_TEST_MISSING", "params": {"path": JS1, "test": T1}} in v["codes"]


def test_M1_C3_a_file_that_could_not_load_counts_its_checks_existence_only():
    c3 = {(JS1, JS1): "existence-only"}
    assert langs.JAVASCRIPT.before(c3, (JS1, T1)) == "existence-only"
    assert langs.JAVASCRIPT.before({(JS1, T1): "strong", (JS1, JS1): "existence-only"}, (JS1, T1)) == "strong"
    assert langs.JAVASCRIPT.before({(JS1, T1): "unreadable"}, (JS1, T1)) is None
    assert langs.JAVASCRIPT.before({}, (JS1, T1)) is None


# ---------------------------------------------------------------- M1-C4 the lock
def test_M1_C4_python_entries_are_unchanged_by_the_path():
    assert entry(PY_SRC) == entry(PY_SRC, PY)
    assert entry(PY_SRC, PY)["tests"] == ["test_S1_C1_counts_words"]


def test_M1_C4_javascript_entries_list_the_literal_top_level_titles():
    src = (
        b'import { test, it, describe } from "vitest";\n'
        b'test("S1-C1 one", () => {});\n'
        b"it('S1-C2 two', () => {});\n"
        b"test(`S1-C3 three`, () => {});\n"
        b'test ( "S1-C4 four" , () => {});\n'
        b'  test("nested, not top level", () => {});\n'
        b'describe("group", () => {});\n'
        b"test(`with ${x}`, () => {});\n"
        b'test("with \\"escape\\"", () => {});\n'
        b'test.skip("S1-C5 skipped", () => {});\n'
        b"def test_S1_C9_python():\n"
    )
    assert entry(src, "tests/acceptance/S1/x.test.ts")["tests"] == [
        "S1-C1 one",
        "S1-C2 two",
        "S1-C3 three",
        "S1-C4 four",
    ]
    assert entry(src, "tests/acceptance/S1/x.test.ts")["sha256"] == entry(src)["sha256"]
    assert entry(JS1_SRC, JS1)["tests"] == [T1]


def test_M1_C4_the_conformance_cases_lock_entries_match_the_engine():
    from pathlib import Path

    case = Path(__file__).resolve().parents[1] / "conformance" / "cases" / "js-proven" / "main"
    files = json.loads((case / "locks.json").read_text(encoding="utf-8"))["files"]
    for p, rec in files.items():
        assert entry((case / p).read_bytes(), p) == rec, p


# ---------------------------------------------------------------- M1-C5 protected names, scoped (L5 B)
NEW_NAMES = (
    "package.json",
    "npm-shrinkwrap.json",
    ".npmrc",
    "bun.lockb",
    ".yarnrc",
    ".yarnrc.yml",
    "pnpm-workspace.yaml",
    "vite.config.ts",
    "vitest.config.mts",
    "vitest.workspace.ts",
    "tsconfig.json",
    "tsconfig.app.json",
    "jsconfig.json",
    ".nvmrc",
    ".node-version",
)


def test_M1_C5_the_new_names_apply_only_with_javascript_checks():
    extra = langs.JAVASCRIPT.protected
    for name in NEW_NAMES:
        for path in (name, f"frontend/{name}"):
            assert protected(path, False, False, extra), path
            assert not protected(path, False, False), path
            assert not protected(path, False, False, langs.PYTHON.protected), path
    assert not protected("src/vite-env.d.ts", False, False, extra)
    assert not protected("config/ts-base.json", False, False, extra)
    assert protected("package-lock.json", False, False)  # lock files stay protected everywhere


def test_M1_C5_scope_reads_main_or_the_pull_requests_lock(tmp_path):
    py_main = {"locks.json": lockfile({PY: PY_SRC}), "dev-docs/stories/S1/story.md": STORY, PY: PY_SRC}
    f = js_facts(tmp_path, evidence=PY_EV, changed=["app/count.py", "tsconfig.json"], main=py_main)
    assert judge(f)["verdict"] == "PROVEN"
    f.head_files = dict(py_main, **{"locks.json": lockfile({PY: PY_SRC, JS1: JS1_SRC})})
    assert {"code": "PROTECTED_CHANGED", "params": {"path": "tsconfig.json"}} in judge(f)["codes"]


def test_M1_C5_the_receipt_names_the_new_files_in_plain_words():
    software = "the list of software your app installs"
    settings = "the settings for how your checks run"
    for name in ("package.json", "npm-shrinkwrap.json", ".npmrc", "bun.lockb", ".yarnrc.yml", "pnpm-workspace.yaml"):
        assert plain_file(name) == software and plain_file(f"web/{name}") == software, name
    for name in (
        "vite.config.ts",
        "vitest.config.js",
        "vitest.workspace.ts",
        "tsconfig.json",
        "tsconfig.node.json",
        "jsconfig.json",
        ".nvmrc",
        ".node-version",
    ):
        assert plain_file(name) == settings and plain_file(f"web/{name}") == settings, name
    assert plain_file("tests/acceptance/S1/package.json") == "one of your agreed checks"


# ---------------------------------------------------------------- M1-C6 STORY_ADDS_TOOLS
def story_facts(tmp_path, *, changed, extra_head=None, new=None):
    new = new or {JS1: JS1_SRC}
    head = {"locks.json": lockfile(new), "dev-docs/stories/S1/story.md": STORY, **new, **(extra_head or {})}
    f = js_facts(tmp_path, evidence={}, branch="story/S1", changed=changed, main={"package.json": b"{}\n"})
    f.head_files = head
    return f


def test_M1_C6_a_javascript_story_that_adds_its_tools_says_so_in_one_line(tmp_path):
    changed = ["locks.json", "dev-docs/stories/S1/story.md", JS1, "package.json", "package-lock.json"]
    v = judge(story_facts(tmp_path, changed=changed))
    assert v["verdict"] == "WAITING FOR YOU"
    assert codes(v) == ["NEW_CHECKS", "STORY_ADDS_TOOLS"]
    assert v["codes"][1]["params"] == {"paths": ["package-lock.json", "package.json"]}
    r = render(v)
    assert r["template"] == 2
    assert (
        "It also changes the list of software your app installs; approving the checks approves that change too."
        in (r["top"])
    )
    assert "Undo your change" not in r["top"] and lint("story", r["top"]) == []


def test_M1_C6_only_the_two_package_files_count(tmp_path):
    changed = ["locks.json", "dev-docs/stories/S1/story.md", JS1, "package.json", ".npmrc"]
    v = judge(story_facts(tmp_path, changed=changed))
    assert "STORY_ADDS_TOOLS" not in codes(v) and codes(v).count("PROTECTED_CHANGED") == 2
    v = judge(story_facts(tmp_path, changed=["locks.json", "dev-docs/stories/S1/story.md", JS1]))
    assert codes(v) == ["NEW_CHECKS"]


def test_M1_C6_a_python_story_keeps_todays_wording(tmp_path):
    changed = ["locks.json", "dev-docs/stories/S1/story.md", PY, "package-lock.json"]
    v = judge(story_facts(tmp_path, changed=changed, new={PY: PY_SRC}))
    assert "STORY_ADDS_TOOLS" not in codes(v) and "PROTECTED_CHANGED" in codes(v)
    both = {PY: PY_SRC, JS1: JS1_SRC}
    v = judge(story_facts(tmp_path, changed=changed + [JS1], new=both))
    assert "STORY_ADDS_TOOLS" not in codes(v)


def test_M1_C6_an_undescribed_story_keeps_its_stop_line(tmp_path):
    changed = ["locks.json", "dev-docs/stories/S1/story.md", JS1, "package.json"]
    f = story_facts(tmp_path, changed=changed)
    f.head_files["dev-docs/stories/S1/story.md"] = b"# S1: x\n\n| S1-C1 | y |\n"
    v = judge(f)
    assert "STORY_ADDS_TOOLS" in codes(v) and "NEW_CHECKS_UNDESCRIBED" in codes(v)
    top = render(v)["top"]
    assert "Don't approve these yet" in top and "approving the checks approves" not in top


# ---------------------------------------------------------------- M1-C7 install codes
def test_M1_C7_each_known_install_code_adds_its_one_sentence(tmp_path):
    want = {
        "EBADPLATFORM": "only work on another kind of computer",
        "ERESOLVE": "don't work with each other",
        "EUSAGE": "doesn't match its list of exact versions",
    }
    for err, phrase in want.items():
        d = tmp_path / err
        d.mkdir()
        v = judge(js_facts(d, evidence={"js-install.txt": f"{err}\n"}))
        assert v["verdict"] == "UNRESOLVED"
        assert {"code": "INSTALL_FAILED", "params": {"error": err}} in v["codes"]
        top = render(v)["top"]
        assert phrase in top and "GitHub could not install it" in top
        assert sum(p in top for p in want.values()) == 1
        assert lint(err, top) == []


def test_M1_C7_anything_else_adds_none(tmp_path):
    for i, text in enumerate(("OTHER\n", "EBADPLATFORM extra\n", "", "x" * 5000)):
        d = tmp_path / str(i)
        d.mkdir()
        v = judge(js_facts(d, evidence={"js-install.txt": text}))
        assert v["verdict"] == "UNRESOLVED" and "INSTALL_FAILED" not in codes(v), text[:20]
        assert "could not install" not in render(v)["top"]
    v = judge(js_facts(tmp_path / "none", evidence={}))
    assert "INSTALL_FAILED" not in codes(v)


def test_M1_C7_the_install_code_is_ignored_when_results_exist(tmp_path):
    ev = dict(ok_evidence(), **{"js-install.txt": "EBADPLATFORM\n"})
    v = judge(js_facts(tmp_path, evidence=ev))
    assert v["verdict"] == "PROVEN" and "INSTALL_FAILED" not in codes(v)


# ---------------------------------------------------------------- M1-C8 earlier stories
JS_S2 = "tests/acceptance/S2/S2-C1.test.tsx"
T2 = "S2-C1 clears the box"
S2_SRC = f'test("{T2}", () => {{}});\n'.encode()
STORY2 = b"# S2: Clear\n\n## Plain checklist\n\n| ID | plain: |\n| --- | --- |\n| S2-C1 | Press Clear. |\n"


def s2_facts(tmp_path, *, s1_acc, s1_before):
    main = {
        "locks.json": lockfile({JS1: JS1_SRC, JS_S2: S2_SRC}),
        "dev-docs/stories/S1/story.md": STORY,
        "dev-docs/stories/S2/story.md": STORY2,
        JS1: JS1_SRC,
        JS_S2: S2_SRC,
    }
    ev = {
        "pr-js.xml": vitest([(JS1, T1, None, ""), (JS_S2, T2, None, "")]),
        "acceptance-js.xml": vitest([(JS1, T1, s1_acc, "expected 2 to be 3"), (JS_S2, T2, None, "")]),
        "c3/tests_acceptance_s1_s1_c1_test_tsx.xml": vitest([(JS1, T1, s1_before, "x")]),
        "c3/tests_acceptance_s2_s2_c1_test_tsx.xml": vitest([(JS_S2, T2, "AssertionError", "x")]),
    }
    return js_facts(tmp_path, evidence=ev, branch="build/S2", changed=["src/Clear.tsx"], main=main)


def test_M1_C8_an_earlier_story_failing_in_the_hardened_run_counts_as_broken(tmp_path):
    v = judge(s2_facts(tmp_path, s1_acc="AssertionError", s1_before=None))
    assert v["verdict"] == "NOT PROVEN"
    assert {"code": "PASS_TO_PASS_BROKEN", "params": {"count": 1, "tests": [f"{JS1}::{T1}"]}} in v["codes"]
    assert v["pass_to_pass"] == {"total": 1, "broken": 1, "unbuilt": 0}
    assert render(v)["template"] == 5


def test_M1_C8_an_unbuilt_story_failing_on_main_too_is_listed_not_counted(tmp_path):
    v = judge(s2_facts(tmp_path, s1_acc="AssertionError", s1_before="AssertionError"))
    assert v["verdict"] == "PROVEN"
    assert v["pass_to_pass"] == {"total": 1, "broken": 0, "unbuilt": 1}


def test_M1_C8_all_passing_is_proven(tmp_path):
    v = judge(s2_facts(tmp_path, s1_acc=None, s1_before=None))
    assert v["verdict"] == "PROVEN" and v["pass_to_pass"] == {"total": 1, "broken": 0, "unbuilt": 0}
