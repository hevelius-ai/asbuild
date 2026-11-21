"""v0.4.2 (D60): the five ideas the parked-ideas review kept (D59), each by its own criterion (plan
`docs/plans/v0.4.2.md`). Every receipt a test renders is also linted (the plain-words rules)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from engine.lint_plain import lint
from engine.receipt import render
from engine.verdict import Facts, judge
from tests.acceptance.S2.test_S2_story_checks import GOOD_C1, GOOD_C2, make_repo
from tests.conformance.test_conformance import outcome

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugin" / "scripts"))
import asbuild_story_check as sc  # noqa: E402

CASE = ROOT / "tests" / "conformance" / "cases" / "py-proven"
UNIT_OK = '<testcase classname="tests.unit.test_app" name="test_unit_ok" time="0.01"></testcase>'
UNIT_FAIL = UNIT_OK.replace("></testcase>", '><failure message="assert 1 == 2">assert 1 == 2</failure></testcase>')
SOFTWARE_FIRST = (
    'To have the lines on your list checked, tell the AI: "Put your change to the list of software your app '
    'installs in a separate change, so I can accept that one first."'
)


def tree(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def judged(tmp_path: Path, branch: str, changed: list[str], broken: bool) -> tuple[dict, dict]:
    ev = tmp_path / "evidence"
    shutil.copytree(CASE / "evidence", ev)
    if broken:
        pr = (ev / "pr.xml").read_text(encoding="utf-8")
        assert UNIT_OK in pr
        (ev / "pr.xml").write_text(pr.replace(UNIT_OK, UNIT_FAIL), encoding="utf-8")
    f = Facts(
        branch=branch,
        pr_number=1,
        pr_url="https://github.com/example/app/pull/1",
        head_sha="c" * 40,
        files_changed=changed,
        main_files=tree(CASE / "main"),
        head_files=tree(CASE / "head"),
        evidence=str(ev),
    )
    v = judge(f)
    return v, render(v)


# ------------------------------------------------------------------ V42-C1 (P33): a test name inside a text string


def test_V42_C1_a_test_name_inside_a_text_string_is_refused_at_story_time(tmp_path, monkeypatch, capsys):
    planted = GOOD_C1 + GOOD_C2 + '\nHELP = """\ndef test_planted(x):\n    an example line in a text\n"""\n'
    repo = make_repo(tmp_path, planted)
    monkeypatch.chdir(repo)
    code = sc.main(["S1", "--base", "main", "--lock"])
    out = capsys.readouterr().out
    assert code == 1, out
    assert "test_planted" in out and "is not a test" in out
    assert not (repo / "locks.json").exists() or "test_planted" not in (repo / "locks.json").read_text()


def test_V42_C1_a_clean_story_still_passes(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, GOOD_C1 + GOOD_C2)
    monkeypatch.chdir(repo)
    assert sc.main(["S1", "--base", "main"]) == 0, capsys.readouterr().out


# ------------------------------------------------------------------ V42-C2 (P70): the waiting check shows as failed


def test_V42_C2_readme_and_verdict_skill_say_the_waiting_check_shows_as_failed():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "show its check as failed" in readme
    assert "unless you set GitHub to require the AsBuild check" in readme
    skill = (ROOT / "plugin" / "skills" / "verdict" / "SKILL.md").read_text(encoding="utf-8")
    assert "GitHub shows the AsBuild check as failed while it waits for the person" in skill


# ------------------------------------------------------------------ V42-C3 (R03): no story, and other checks broke


def test_V42_C3_no_story_with_broken_checks_says_so_and_offers_no_accept(tmp_path):
    v, r = judged(tmp_path, "fix/typo", ["app/count.py"], broken=True)
    assert v["verdict"] == "WAITING FOR YOU" and [c["code"] for c in v["codes"]] == ["NO_STORY", "PASS_TO_PASS_BROKEN"]
    top = r["top"]
    assert "nothing could be checked" not in top
    assert "then accept it on GitHub" not in top  # no action to accept ("Don't accept it yet" is the headline)
    assert "No agreed check covers this change, and 1 of your app's other checks fails now." in top
    assert "Fix your change so my app's other checks pass again, without changing them." in top
    assert "Then agree a list of checks for this change with the AI." in top
    assert lint("v42-c3", top) == []


def test_V42_C3_no_story_without_broken_checks_keeps_its_words(tmp_path):
    v, r = judged(tmp_path, "fix/typo", ["app/count.py"], broken=False)
    assert "No agreed check covers this change, so nothing could be checked." in r["top"]
    assert "If it needs none, read the change, then accept it" in r["top"]
    assert lint("v42-c3-clean", r["top"]) == []


# ------------------------------------------------------------------ V42-C4 (P53): only the software list changed


def test_V42_C4_a_software_list_change_names_the_separate_change_path_last():
    v, r = outcome("py-frontend-lockfile")
    lines = r["top"].splitlines()
    assert f"- {SOFTWARE_FIRST}" in lines
    accept = next(i for i, ln in enumerate(lines) if "read the change, then accept it" in ln)
    assert lines.index(f"- {SOFTWARE_FIRST}") == accept + 1
    assert lint("v42-c4", r["top"]) == []


@pytest.mark.parametrize("case", ["py-tampered-settings", "py-weakened-check", "py-story", "js-story"])
def test_V42_C4_no_separate_change_line_for_other_protected_changes(case):
    assert SOFTWARE_FIRST not in outcome(case)[1]["top"]


@pytest.mark.parametrize("case", ["js-package-script", "js-npmrc"])
def test_V42_C4_javascript_builds_that_change_only_the_software_list_get_the_line(case):
    v, r = outcome(case)
    assert v["verdict"] == "WAITING FOR YOU"
    assert f"- {SOFTWARE_FIRST}" in r["top"].splitlines()
    assert lint(f"v42-c4-{case}", r["top"]) == []


def test_V42_C4_javascript_settings_change_gets_no_line():
    assert SOFTWARE_FIRST not in outcome("js-tampered-settings")[1]["top"]


def test_V42_C3_javascript_no_story_with_a_broken_vitest_check(tmp_path):
    case = ROOT / "tests" / "conformance" / "cases" / "js-proven"
    ev = tmp_path / "evidence"
    shutil.copytree(case / "evidence", ev)
    ok = '<testcase classname="src/Counter.test.tsx" name="counts words" time="0.001"></testcase>'
    pr = (ev / "pr-js.xml").read_text(encoding="utf-8")
    assert ok in pr
    bad = ok.replace("></testcase>", '><failure message="expected 2 to be 3">AssertionError</failure></testcase>')
    (ev / "pr-js.xml").write_text(pr.replace(ok, bad), encoding="utf-8")
    f = Facts(
        branch="fix/typo",
        pr_number=1,
        pr_url="https://github.com/example/app/pull/1",
        head_sha="c" * 40,
        files_changed=["src/Counter.tsx"],
        main_files=tree(case / "main"),
        head_files=tree(case / "head"),
        evidence=str(ev),
    )
    v = judge(f)
    top = render(v)["top"]
    assert [c["code"] for c in v["codes"]] == ["NO_STORY", "PASS_TO_PASS_BROKEN"]
    assert "No agreed check covers this change, and 1 of your app's other checks fails now." in top
    assert "then accept it on GitHub" not in top
    assert lint("v42-c3-js", top) == []


# ------------------------------------------------------------------ V42-C5 (R01, K11): the technical file_changed line


def test_V42_C5_the_technical_report_says_why_a_line_is_not_judged():
    v, r = outcome("py-tampered-settings")
    assert {i["status"] for i in v["items"]} == {"file_changed"}  # the status value stays (D58)
    tech = r["technical"]
    assert "- S1-C1: not judged, a protected file changed (file_changed)" in tech
    assert "- S1-C1: file_changed" not in tech
    assert json.loads(json.dumps(v))["items"][0]["status"] == "file_changed"
