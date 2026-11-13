"""Story S5 fixes: the owner's try findings T1 to T3 (D40, docs/plans/S5-fixes.md).

The setup rows reuse S5's own stand-in for GitHub (a local bare repository through `insteadOf`, a fake `gh`), loaded
from `test_S5_setup.py` by its path, because the acceptance run uses no conftest.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
_spec = importlib.util.spec_from_file_location("s5_setup_rows", HERE / "test_S5_setup.py")
assert _spec and _spec.loader
s5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s5)
world = s5.world  # the same fixture: a person's folder linked to an empty stand-in for GitHub


def install_section() -> str:
    lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    start = lines.index("## Install") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def opening_step(n: int) -> str:
    opening = install_section().split("\n### ", 1)[0]
    return next(line for line in opening.splitlines() if line.startswith(f"{n}. "))


def test_S5_T1_install_says_the_folder_is_on_your_computer():
    step = opening_step(2)
    assert "2. In your project, type `/asbuild:setup`." in step
    assert "folder on your computer" in step
    section = install_section().split("### 2. Set it up", 1)[1].split("\n### ", 1)[0]
    assert "folder on your computer" in section
    assert "git clone https://github.com/<owner>/<repository>.git" in section
    assert "not the GitHub repository" in section
    assert "a session that runs in the cloud does not have the plugin" in section


EXAMPLE = """Git's name or email is still the example ("Your Name" or you@example.com)"""
CLAUDE_SETS = "Tell Claude the name and email to use, and it sets them for you"


def test_S5_T2_example_identity_counts_as_not_set(world, capsys):
    """T2 as it happened: the examples in the global settings; each fix the message names lets setup carry on."""
    work, hub = world
    s5.git(work, "config", "--unset", "user.name")
    s5.git(work, "config", "--unset", "user.email")
    s5.git(work, "config", "--global", "user.name", "Your Name")
    s5.git(work, "config", "--global", "user.email", "you@example.com")
    before = s5.snapshot(work)
    code, out = s5.setup(work, capsys)
    assert code == 1
    assert EXAMPLE in out and CLAUDE_SETS in out and s5.AGAIN in out
    assert 'git config --global user.name "Your Name"' in out and "leave out --global" not in out
    assert s5.snapshot(work) == before and s5.hub_branches(hub) == set()
    s5.git(work, "config", "--global", "user.name", "Pat Example")  # the fix the message names
    code, out = s5.setup(work, capsys)
    assert code == 1 and EXAMPLE in out  # the email is still the example
    assert s5.snapshot(work) == before and s5.hub_branches(hub) == set()
    s5.git(work, "config", "--global", "user.email", "pat@example.com")
    code, out = s5.setup(work, capsys)
    assert code == 0 and "main" in s5.hub_branches(hub)


def test_S5_T2_example_identity_in_the_repository_names_the_local_fix(world, capsys):
    work, hub = world
    s5.git(work, "config", "--global", "user.name", "Pat Global")
    s5.git(work, "config", "user.name", "Your Name")  # README: "leave out --global ... for one repository only"
    before = s5.snapshot(work)
    code, out = s5.setup(work, capsys)
    assert code == 1
    assert EXAMPLE in out and "It is set in this repository's own settings" in out
    assert '  git config user.name "Your Name"' in out.splitlines() and "git config --global" not in out
    assert s5.snapshot(work) == before and s5.hub_branches(hub) == set()
    s5.git(work, "config", "user.name", "Pat Example")  # the fix the message names
    code, out = s5.setup(work, capsys)
    assert code == 0 and "main" in s5.hub_branches(hub)


def test_S5_T2_missing_identity_says_claude_can_set_it(world, capsys):
    work, _ = world
    s5.git(work, "config", "--unset", "user.email")
    code, out = s5.setup(work, capsys)
    assert code == 1
    assert "Git has no name or email for its commits yet." in out
    assert "your own name and email in place of the examples" in out and CLAUDE_SETS in out


def test_S5_T2_skill_asks_for_the_name_and_email():
    text = (ROOT / "plugin" / "skills" / "setup" / "SKILL.md").read_text(encoding="utf-8")
    assert "ask the person for the name and email to use" in text
    assert "run the two `git config` commands the message names, with `--global` or without it" in text
    assert 'never with the examples "Your Name" or `you@example.com`' in text
    assert len(text.splitlines()) < 60


def test_S5_T3_step_one_says_how():
    step = opening_step(1)
    assert step.startswith("1. Add the plugin to Claude.")
    for words in ("Settings", "Customize", "Plugins", "**Add marketplace**", "`hevelius-ai/asbuild`", "**Discover**"):
        assert words in step, words
    assert "terminal" in step
