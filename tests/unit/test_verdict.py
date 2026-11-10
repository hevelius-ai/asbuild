"""Unit tests for engine/verdict.py: the branches the S1 acceptance tests do not reach."""

from __future__ import annotations

import argparse
import base64
import json

import pytest

from engine import verdict as vm
from engine.lint_plain import lint
from engine.lock_check import entry
from engine.receipt import render
from engine.verdict import Facts, before, judge, matches, parse_story, protected, story_of
from tests.acceptance.S1.test_S1_verdicts import A1, A2, ACC, ACC_CLS, ACC_PATH, STORY, UNIT, facts, junit, locks


def codes(v):
    return [c["code"] for c in v["codes"]]


def test_matches_whole_words_only():
    assert matches("test_S1_C1_counts", "S1-C1")
    assert matches("test_x_S1_C1[case-a]", "S1-C1")
    assert not matches("test_S1_C10_counts", "S1-C1")
    assert not matches("test_S11_C1_counts", "S1-C1")


def test_story_of_and_protected():
    assert story_of(ACC_CLS) == "S1"
    assert story_of("tests.unit.test_app") is None
    assert protected("app/conftest.py", False, False)
    assert protected(".github/workflows/x.yml", False, False)
    assert protected("requirements-dev.txt", False, False)
    assert protected("locks.json", True, False) and not protected("locks.json", True, True)
    assert protected("dev-docs/stories/S1/story.md", True, True)
    assert not protected("dev-docs/stories/S2/story.md", False, True)
    assert protected("tests/acceptance/S2/test_new.py", False, False)
    assert not protected("app/main.py", False, False)


def test_parse_story_without_heading_or_plain_sentence():
    title, checks = parse_story("| S3-C1 | something |\n")
    assert title == ""
    assert checks == [{"id": "S3-C1", "plain": "One of your checks has no plain sentence yet."}]


def test_parse_story_keeps_an_escaped_bar():
    text = '# S1: x\n\n## Plain checklist\n\n| ID | plain: |\n| --- | --- |\n| S1-C1 | Type a \\| b, like "a". |\n'
    assert parse_story(text)[1] == [{"id": "S1-C1", "plain": 'Type a | b, like "a".'}]


def test_before_counts_a_collection_error_for_its_file():
    c3 = {("", "tests.acceptance.S1.test_S1_count"): "existence-only"}
    assert before(c3, A1) == "existence-only"
    assert before(c3, ("tests.acceptance.S1.test_S1_count.TestBox", "test_x")) == "existence-only"
    assert before({}, A1) is None


def test_locked_file_deleted_by_the_pr(tmp_path):
    f = facts(tmp_path, changed=["app/count.py", ACC_PATH])
    del f.head_files[ACC_PATH]
    assert "LOCK_DELETED" in codes(judge(f))


def test_branch_behind_main_is_out_of_date_not_a_change(tmp_path):
    f = facts(tmp_path)
    s2 = "tests/acceptance/S2/test_S2_greet.py"
    s2_raw = b"def test_S2_C1_greets():\n    assert False\n"
    f.main_files[s2] = s2_raw
    f.main_files["locks.json"] = locks({ACC_PATH: ACC, s2: s2_raw})
    v = judge(f)
    assert {"code": "OUT_OF_DATE", "params": {"path": s2}} in v["codes"]
    assert "LOCK_TEST_MISSING" not in codes(v) and "LOCK_DELETED" not in codes(v)
    r = render(v)
    assert r["template"] == 3 and "older version of your app" in r["top"]
    assert "Undo your change" not in r["top"] and lint("x", r["top"]) == []


def test_lock_entry_rewritten_in_lock_file(tmp_path):
    rewritten = json.dumps({"files": {ACC_PATH: dict(entry(ACC), tests=[])}}).encode()
    f = facts(tmp_path, changed=["app/count.py", "locks.json"])
    f.head_files["locks.json"] = rewritten
    v = judge(f)
    assert {"code": "LOCK_CHANGED", "params": {"path": "locks.json"}} in v["codes"]
    assert v["verdict"] == "WAITING FOR YOU"
    d = tmp_path / "behind"
    d.mkdir()
    g = facts(d)
    g.head_files["locks.json"] = rewritten
    assert {"code": "OUT_OF_DATE", "params": {"path": "locks.json"}} in judge(g)["codes"]


@pytest.mark.parametrize("c3", [None, [(*A1, "pass"), (*A2, "pass")]])
def test_changed_locked_test_is_never_shown_as_working(tmp_path, c3):
    f = facts(
        tmp_path, head_acc=ACC.replace(b"assert False", b"assert True"), changed=["app/count.py", ACC_PATH], c3=c3
    )
    v = judge(f)
    r = render(v)
    assert [i["status"] for i in v["items"]] == ["check_changed", "check_changed"]
    assert "ACCEPTANCE_PASSES_ON_MAIN" not in codes(v)
    assert "✓" not in r["top"] and "Suggest a new example" not in r["top"]
    assert "! the AI changed how this line is checked" in r["top"]


def test_changed_sample_data_marks_the_storys_checks(tmp_path):
    v = judge(facts(tmp_path, changed=["app/count.py", "tests/acceptance/S1/data/words.txt"]))
    assert {i["status"] for i in v["items"]} == {"check_changed"}
    assert "the sample data your checks use" in render(v)["top"]


def test_locked_test_missing_from_run_or_skipped(tmp_path):
    v = judge(facts(tmp_path, acc=[(*A1, "pass")], pr=[(*UNIT, "pass"), (*A1, "pass")]))
    assert "LOCK_TEST_MISSING" in codes(v)
    d = tmp_path / "skip"
    d.mkdir()
    v = judge(facts(d, acc=[(*A1, "pass"), (A2[0], A2[1] + "[a]", "pass"), (A2[0], A2[1] + "[b]", "skip")]))
    assert "LOCK_TEST_SKIPPED" in codes(v)
    assert v["verdict"] == "WAITING FOR YOU"


def test_locked_test_inside_a_class_is_found(tmp_path):
    cls = ACC_CLS + ".TestCount"
    v = judge(
        facts(
            tmp_path,
            pr=[(*UNIT, "pass"), (cls, A1[1], "pass"), (*A2, "pass")],
            acc=[(cls, A1[1], "pass"), (*A2, "pass")],
            c3=[(cls, A1[1], "assert"), (*A2, "assert")],
        )
    )
    assert v["verdict"] == "PROVEN"


def test_check_with_no_test_and_existence_only(tmp_path):
    story = STORY.replace("| S1-C2 | For", "| S1-C3 | Extra |\n| S1-C2 | For")
    f = facts(tmp_path, c3=[(*A1, "import"), (*A2, "assert")])
    f.main_files["dev-docs/stories/S1/story.md"] = story.encode()
    v = judge(f)
    assert {"code": "LOCK_TEST_MISSING", "params": {"check": "S1-C3"}} in v["codes"]
    assert {"code": "EXISTENCE_ONLY", "params": {"check": "S1-C1"}} in v["codes"]
    assert [i["status"] for i in v["items"]] == ["exists_only", "not_checked", "works"]


def test_missing_before_result_is_unresolved(tmp_path):
    v = judge(facts(tmp_path, c3=[(*A2, "assert")]))
    assert {"code": "NO_BEFORE_RESULT", "params": {"check": "S1-C1"}} in v["codes"]
    assert v["verdict"] == "UNRESOLVED"
    assert {i["status"] for i in v["items"]} == {"not_checked"}
    r = render(v)
    assert r["template"] == 6 and "already true" not in r["top"]


def test_other_story_failing_on_main_too_is_not_breakage(tmp_path):
    other = ("tests.acceptance.S2.test_S2_greet", "test_S2_C1_greets")
    f = facts(tmp_path, pr=[(*UNIT, "pass"), (*A1, "pass"), (*A2, "pass"), (*other, "assert")])
    (tmp_path / "evidence" / "c3" / "s2.xml").write_text(junit([(*other, "assert")]))
    v = judge(f)
    assert v["verdict"] == "PROVEN"
    assert v["pass_to_pass"] == {"total": 2, "broken": 0}


def test_proven_with_no_other_tests_claims_nothing_about_them(tmp_path):
    v = judge(facts(tmp_path, pr=[(*A1, "pass"), (*A2, "pass")]))
    assert v["verdict"] == "PROVEN" and v["pass_to_pass"]["total"] == 0
    assert "worked before" not in render(v)["top"]


def test_story_pr_that_also_changes_an_existing_lock(tmp_path):
    s2 = "tests/acceptance/S2/test_S2_x.py"
    f = facts(
        tmp_path,
        branch="story/S2",
        changed=["locks.json", s2],
        head_extra={"locks.json": locks({ACC_PATH: b"other", s2: b"def test_S2_C1_x(): pass\n"})},
    )
    v = judge(f)
    assert codes(v) == ["NEW_CHECKS", "LOCK_CHANGED", "NEW_CHECKS_UNDESCRIBED"]
    r = render(v)
    assert r["template"] == 2 and "Don't approve these yet" in r["top"]
    assert lint("x", r["top"]) == []


def test_story_pr_lists_every_new_story_and_flags_undescribed_tests(tmp_path):
    s2, s3, loose = "tests/acceptance/S2/test_S2_a.py", "tests/acceptance/S3/test_S3_a.py", "tests/acceptance/test_x.py"
    st = "# {s}: Thing {s}\n\n## Plain checklist\n\n| ID | plain: |\n| --- | --- |\n| {s}-C1 | Line {s}. |\n"
    f = facts(
        tmp_path,
        branch="story/S2-S3",
        changed=["locks.json", s2, s3, loose],
        head_extra={
            "locks.json": locks({ACC_PATH: ACC, s2: b"x", s3: b"y", loose: b"z"}),
            "dev-docs/stories/S2/story.md": st.format(s="S2").encode(),
            "dev-docs/stories/S3/story.md": st.format(s="S3").encode(),
        },
    )
    v = judge(f)
    assert [i["plain"] for i in v["items"]] == ["Line S2.", "Line S3."]
    assert v["title"] == "Thing S2 and Thing S3"
    assert {"code": "NEW_CHECKS_UNDESCRIBED", "params": {"paths": [loose]}} in v["codes"]
    r = render(v)
    assert "AsBuild hasn't checked anything yet" in r["top"] and lint("x", r["top"]) == []


def test_read_tree_and_fetch_facts(tmp_path, monkeypatch):
    (tmp_path / "tests" / "acceptance" / "S1").mkdir(parents=True)
    (tmp_path / "tests" / "acceptance" / "S1" / "test_a.py").write_bytes(b"x")
    (tmp_path / "locks.json").write_bytes(b"{}")
    assert vm.read_tree(str(tmp_path)) == {"tests/acceptance/S1/test_a.py": b"x", "locks.json": b"{}"}
    assert vm.read_tree(str(tmp_path / "missing")) == {}

    blobs = {"b1": b"lock", "b2": b"story"}
    tree = {
        "tree": [
            {"type": "blob", "path": "locks.json", "sha": "b1", "size": 4},
            {"type": "blob", "path": "dev-docs/stories/S1/story.md", "sha": "b2", "size": 5},
            {"type": "blob", "path": "app/x.py", "sha": "b3", "size": 1},
            {"type": "blob", "path": "tests/acceptance/big.bin", "sha": "b4", "size": 10**8},
            {"type": "tree", "path": "tests/acceptance", "sha": "t1"},
        ]
    }
    pr = {"head": {"ref": "build/S1", "sha": "h" * 40}, "html_url": "https://x/pull/7", "changed_files": 2}

    def api(path):
        if path.endswith("/pulls/7"):
            return pr
        if "/git/trees/" in path:
            return tree
        return {"content": base64.b64encode(blobs[path.rsplit("/", 1)[1]]).decode()}

    def paged(_path):
        return [{"filename": "a.py"}, {"filename": "b.py", "previous_filename": "old.py"}]

    monkeypatch.setenv("REPO", "o/r")
    monkeypatch.setenv("RUN_URL", "https://run")
    a = argparse.Namespace(pr="7", head="h" * 40, main=str(tmp_path), evidence="ev")
    f = vm.fetch_facts(a, api=api, paged=paged)
    assert f.branch == "build/S1" and f.files_changed == ["a.py", "b.py", "old.py"]
    assert f.head_files == {"locks.json": b"lock", "dev-docs/stories/S1/story.md": b"story"}
    assert f.run_url == "https://run" and "locks.json" in f.main_files

    pr["changed_files"] = 3001
    with pytest.raises(ValueError, match="more than AsBuild can list"):
        vm.fetch_facts(a, api=api, paged=paged)
    pr["head"]["sha"] = "n" * 40
    with pytest.raises(ValueError, match="moved on"):
        vm.fetch_facts(a, api=api, paged=paged)


def test_run_writes_three_files(tmp_path):
    out = tmp_path / "out"
    f = facts(tmp_path)
    rc = vm.run(
        [
            "--evidence",
            "x",
            "--head",
            "a" * 40,
            "--pr",
            "7",
            "--out",
            str(out / "v.json"),
            "--summary",
            str(out / "s.md"),
            "--receipt",
            str(out / "r.md"),
        ],
        fetch=lambda _a: f,
    )
    assert rc == 0
    assert json.loads((out / "v.json").read_text(encoding="utf-8"))["verdict"] == "PROVEN"
    assert "AsBuild: PROVEN" in (out / "s.md").read_text(encoding="utf-8")
    assert (out / "r.md").read_text(encoding="utf-8").startswith("<!-- asbuild-receipt -->")


def test_crash_receipt_says_asbuild_could_not_finish():
    r = render(vm.unresolved(7, "a" * 40, "RuntimeError: API down"))
    assert "AsBuild couldn't finish its check" in r["top"] and "Fix the setup" not in r["top"]
    assert lint("x", r["top"]) == []


def test_facts_defaults():
    f = Facts(branch="b", pr_number=1, pr_url="u", head_sha="s")
    assert f.files_changed == [] and f.main_files == {} and f.evidence == ""


@pytest.mark.parametrize(
    "helper", ["tests/acceptance/S1/expected.py", "tests/acceptance/helpers.py", "tests/acceptance/S1/__init__.py"]
)
def test_changed_locked_helper_marks_every_check(tmp_path, helper):
    f = facts(tmp_path, changed=["app/count.py", helper])
    f.main_files[helper] = b"EXPECTED = 3\n"
    f.head_files[helper] = b"EXPECTED = 0\n"
    f.main_files["locks.json"] = f.head_files["locks.json"] = locks({ACC_PATH: ACC, helper: b"EXPECTED = 3\n"})
    v = judge(f)
    assert {"code": "LOCK_CHANGED", "params": {"path": helper}} in v["codes"]
    assert {i["status"] for i in v["items"]} == {"check_changed"}
    assert "✓" not in render(v)["top"]


def test_other_storys_changed_test_does_not_mark_this_storys_checks(tmp_path):
    other = "tests/acceptance/S2/test_S2_greet.py"
    f = facts(tmp_path, changed=["app/count.py", other])
    f.main_files[other] = b"def test_S2_C1_greets():\n    assert False\n"
    f.head_files[other] = b"def test_S2_C1_greets():\n    assert True\n"
    v = judge(f)
    assert [i["status"] for i in v["items"]] == ["works", "works"]
    assert v["verdict"] == "WAITING FOR YOU"


def test_story_pr_with_a_check_missing_its_plain_sentence(tmp_path):
    s2 = "tests/acceptance/S2/test_S2_a.py"
    story = (
        "# S2: Greet\n\n## Criteria\n\n| S2-C1 | greets |\n| S2-C2 | usage |\n\n"
        "## Plain checklist\n\n| S2-C1 | Says hello. |\n"
    )
    f = facts(
        tmp_path,
        branch="story/S2",
        changed=["locks.json", s2, "dev-docs/stories/S2/story.md"],
        head_extra={
            "locks.json": locks({ACC_PATH: ACC, s2: b"x"}),
            s2: b"x",
            "dev-docs/stories/S2/story.md": story.encode(),
        },
    )
    v = judge(f)
    assert {"code": "NEW_CHECKS_UNDESCRIBED", "params": {"paths": ["dev-docs/stories/S2/story.md"]}} in v["codes"]
    r = render(v)
    assert "Don't approve these yet" in r["top"] and "If every line says what you asked for" not in r["top"]
