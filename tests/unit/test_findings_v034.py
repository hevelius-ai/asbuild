"""Release v0.3.4: the fixes for the v0.3.3 release walkthrough's findings F1 to F4 (decision D46)."""

from __future__ import annotations

from pathlib import Path

from engine.lint_plain import lint
from engine.receipt import render
from engine.verdict import judge
from tests.acceptance.S1.test_S1_verdicts import ACC_PATH, facts

ROOT = Path(__file__).resolve().parents[2]
SETUP_FILE = ".github/workflows/asbuild-verdict.yml"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# F1 (MEDIUM): the shell install path says to reload before /asbuild:setup.
def test_shell_install_path_says_to_reload():
    text = read("README.md")
    part = text.split("**From a script, from CI, or from Claude's own shell**", 1)[1].split("### 2. Set it up", 1)[0]
    assert (
        "If Claude Code ran these commands in its own shell, type `/reload-plugins` in that session, or start "
        "Claude Code again, before `/asbuild:setup`."
    ) in part


# F2a (LOW): a protected-file receipt does not presume the change was unwanted.
def test_protected_file_receipt_does_not_presume(tmp_path):
    top = render(judge(facts(tmp_path, changed=["app/count.py", "conftest.py"])))["top"]
    assert "Most likely" not in top
    assert "Yes. If you didn't ask for this, tell the AI: \"Undo your change to" in top
    assert "If you did ask for it, read the change and accept it yourself." in top
    assert lint("protected", top) == []


# F2a (LOW): setup's own update pull request is told to read and accept it, not to undo it or agree checks.
def test_setup_update_receipt_says_read_and_accept(tmp_path):
    v = judge(facts(tmp_path, branch="asbuild-setup", changed=[SETUP_FILE]))
    assert v["verdict"] == "WAITING FOR YOU"
    top = render(v)["top"]
    assert "This looks like AsBuild's own update from its setup." in top
    assert "Yes. If you ran AsBuild's setup, read the change and accept it yourself." in top
    assert "Agree a list of checks" not in top and "Most likely" not in top
    assert lint("setup-update", top) == []


# F2b (LOW): a story receipt's new lines carry one bullet, not two.
def test_new_checks_have_one_bullet(tmp_path):
    from tests.acceptance.S1.test_S1_verdicts import locks

    f = facts(tmp_path, branch="story/S2", changed=["tests/acceptance/S2/test_S2_greet.py", "locks.json"])
    s2 = b'def test_S2_C1_greets():\n    assert greet() == "hi"\n'
    f.head_files["tests/acceptance/S2/test_S2_greet.py"] = s2
    f.head_files["dev-docs/stories/S2/story.md"] = (
        b"# S2: greet\n\n## Plain checklist\n\n| ID | plain: |\n| --- | --- |\n| S2-C1 | It says hi. |\n"
    )
    f.head_files["locks.json"] = locks(
        {ACC_PATH: f.main_files.get(ACC_PATH, b""), "tests/acceptance/S2/test_S2_greet.py": s2}
    )
    top = render(judge(f))["top"]
    assert "•" not in top
    assert "- new, for you to approve:" in top


# F4 (LOW): a removed check is called removed, not changed.
def test_removed_check_is_called_removed(tmp_path):
    f = facts(tmp_path, changed=["app/count.py", ACC_PATH])
    del f.head_files[ACC_PATH]
    v = judge(f)
    assert {i["status"] for i in v["items"]} == {"check_removed"}
    top = render(v)["top"]
    assert "? not judged: the AI removed one of your agreed checks" in top
    assert "The AI removed one of your agreed checks" in top and "changed" not in top.split("Do you need")[0]
    assert lint("removed", top) == []


# F3 (LOW, a mitigation): the setup skill shows the script's message word for word, in a block.
def test_setup_skill_shows_the_message_word_for_word():
    text = read("plugin/skills/setup/SKILL.md")
    assert text.count("word for word, in a text block") >= 3
    assert "pass on the script's message as it is" not in text
