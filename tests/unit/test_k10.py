"""Release v0.4.1: known issue K10 (decision D54, plan docs/plans/v0.4.1.md).

A pull request that changes a file only the person may change said "read the change and accept it yourself"
without saying how, and marked every agreed line "? not judged: the AI changed a file only you may change", which
reads as if the agreed checks had changed. The verdict (WAITING FOR YOU) and D41's choice (every line unjudged)
stay; only the words change.
"""

from __future__ import annotations

import pytest

from engine.lint_plain import lint
from engine.receipt import render
from engine.verdict import judge
from tests.acceptance.S1.test_S1_verdicts import facts

BUTTON = "accept it on GitHub with the green button (Merge pull request)."
UNJUDGED = "? not judged, though this line is still as you agreed it: the AI changed a file only you may change"
SETUP_FILE = ".github/workflows/asbuild-verdict.yml"


def test_K10_C1_a_changed_protected_file_says_how_to_accept_it(tmp_path):
    v = judge(facts(tmp_path, changed=["app/count.py", "requirements.txt"]))
    top = render(v)["top"]
    assert v["verdict"] == "WAITING FOR YOU"
    assert "If you did ask for it, read the change, then " + BUTTON in top
    assert "accept it yourself" not in top
    assert lint("k10-protected", top) == []


def test_K10_C1_setup_s_own_update_says_how_to_accept_it(tmp_path):
    v = judge(facts(tmp_path, branch="asbuild-setup", changed=[SETUP_FILE]))
    top = render(v)["top"]
    assert v["verdict"] == "WAITING FOR YOU"
    assert "Yes. If you ran AsBuild's setup, read the change, then " + BUTTON in top
    assert "accept it yourself" not in top
    assert lint("k10-setup", top) == []


def test_K10_C1_a_change_no_check_covers_says_how_to_accept_it(tmp_path):
    v = judge(facts(tmp_path, branch="docs/readme"))
    top = render(v)["top"]
    assert v["verdict"] == "WAITING FOR YOU"
    assert "If it needs none, read the change, then " + BUTTON in top
    assert "accept it yourself" not in top
    assert lint("k10-no-story", top) == []


def test_K10_C1_two_accept_lines_name_the_button_once(tmp_path):
    """A protected change with no story: both lines say how; the bracket appears once (the lint's BRACKET_DUP)."""
    v = judge(facts(tmp_path, branch="docs/readme", changed=["README.md", "requirements.txt"]))
    top = render(v)["top"]
    assert top.count("(Merge pull request)") == 1
    assert "If you did ask for it, read the change, then " + BUTTON in top
    assert "If it needs none, read the change, then accept it on GitHub with the same green button." in top
    assert lint("k10-both", top) == []


@pytest.mark.parametrize(
    "path",
    ["dev-docs/stories/S1/story.md", "dev-docs/requests/S1.md", "locks.json"],
)
def test_K10_C2_no_still_as_agreed_claim_when_the_agreed_files_changed(tmp_path, path):
    """Review round 1, F1 (MEDIUM): the story's own files hold the lines, so the claim would be unchecked there."""
    extra = {path: b"# changed by the AI\n"} if path != "locks.json" else None
    v = judge(facts(tmp_path, changed=["app/count.py", path], head_extra=extra))
    top = render(v)["top"]
    assert v["verdict"] == "WAITING FOR YOU"
    assert {i["status"] for i in v["items"]} == {"file_changed"}
    assert "still as you agreed it" not in top
    assert top.count("? not judged: the AI changed a file only you may change") == 2  # v0.4.0's words
    assert lint("k10-agreed-files", top) == []


def test_K10_C2_unjudged_lines_say_the_line_is_still_as_agreed(tmp_path):
    v = judge(facts(tmp_path, changed=["app/count.py", "pytest.ini"]))
    top = render(v)["top"]
    assert {i["status"] for i in v["items"]} == {"file_changed"}
    assert top.count(UNJUDGED) == 2
    assert "? not judged: the AI changed a file" not in top
    assert lint("k10-lines", top) == []
