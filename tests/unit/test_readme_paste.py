"""The README's copy-paste message: one block a person pastes into Claude Code, which follows it to install AsBuild."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADING = "### Or let Claude Code do it"


def install_section() -> str:
    lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    start = lines.index("## Install") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def paste_block() -> str:
    page = install_section()
    assert HEADING in page, f"the install section has no '{HEADING}'"
    part = page.split(HEADING, 1)[1].split("\n### ", 1)[0]
    blocks = re.findall(r"^```text\n(.*?)^```$", part, re.MULTILINE | re.DOTALL)
    assert len(blocks) == 1, "the part holds exactly one ```text block to copy"
    return blocks[0]


def test_paste_block_comes_first_and_the_manual_steps_stay():
    page = install_section()
    order = [HEADING, "### Before you start", "### 1. Add the plugin", "### 2. Set it up", "### By hand"]
    assert all(h in page for h in order)
    assert [page.index(h) for h in order] == sorted(page.index(h) for h in order)


def test_paste_block_names_this_marketplace_and_plugin():
    block = paste_block()
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    (entry,) = market["plugins"]
    add = block.find("claude plugin marketplace add hevelius-ai/asbuild")
    install = block.find(f"claude plugin install {entry['name']}@{market['name']}")
    assert add != -1 and install != -1 and add < install
    # the desktop path, for when the claude command is not in Claude's shell
    for words in ("Settings", "Customize", "Plugins", "Add marketplace", "Add from a repository", "Discover"):
        assert words in block, words
    # and the slash commands, for a terminal session whose shell has no claude command
    assert "/plugin marketplace add hevelius-ai/asbuild" in block and "/plugin install asbuild@hevelius-ai" in block
    # after the desktop menus, the README's own order: a new session, then /reload-plugins in it
    assert "start a new session in this folder, type /reload-plugins in it, then /asbuild:setup" in block


def test_paste_block_hands_over_to_setup_and_keeps_sign_in_with_the_person():
    block = paste_block()
    assert "/reload-plugins" in block and "/asbuild:setup" in block
    assert block.index("/reload-plugins") < block.index("/asbuild:setup")
    assert "Never ask for, type or handle a password, key or token" in block
    assert "tell me to run gh auth login in a terminal myself" in block  # the person signs in, never Claude
    assert "Only if this folder is empty" in block and "is not a Git repository" in block  # never a clone over work
    assert "setup checks the folder itself" in block and "Git's name and email" in block  # left to setup
    assert "git config" not in block  # the identity, with its --global or not, is setup's
    assert "gh auth setup-git" in block  # Git uses the sign-in gh has, for a private clone
    # the tools first, any Python 3.12 or newer, under each name setup tries
    assert block.index("git --version") < block.index("gh auth status") < block.index("git clone")
    assert "Python 3.12 or newer" in block
    assert all(name in block for name in ("python --version", "python3 --version", "py --version"))
    assert "Ask me before installing anything" in block
    assert "winget install --id Git.Git" in block and "winget install --id GitHub.cli" in block
    assert "winget install --id Python.Python.3.12" in block
