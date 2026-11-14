"""Release v0.3.3: the fixes for the analyst findings of 14 Nov 2026 (the owner's 1A, decision D45)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from engine.lint_plain import lint
from engine.receipt import render
from engine.verdict import judge
from tests.acceptance.S1.test_S1_verdicts import A1, A2, UNIT, facts

ROOT = Path(__file__).resolve().parents[2]
NAMES = ("asbuild-test.yml", "asbuild-verdict.yml")
WORKFLOWS = [ROOT / d / n for d in ("workflows", "plugin/workflows") for n in NAMES]
CLONE = "git clone --quiet --depth 1 --branch v"
TREE_CHECK = re.compile(
    r'^ *test "\$\(git -C "\$RUNNER_TEMP/asbuild" rev-parse HEAD:engine\)" = "([0-9a-f]{40})"$', re.M
)
HASHED = (
    'python -m pip install --quiet --require-hashes --only-binary=:all: --no-deps -r "$ASBUILD/engine/requirements.txt"'
)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# Finding 1: a PROVEN receipt says only what was checked, never that merging is safe.
def test_proven_receipt_claims_no_safety(tmp_path):
    top = render(judge(facts(tmp_path)))["top"]
    assert "safe" not in top.lower()
    assert "If you want this change, press the green button there (Merge pull request)." in top
    assert "Every line on your list works; that is all AsBuild checked." in top
    assert lint("proven", top) == []


# Finding 2: the other tests are described by what was measured in the pull request's own run.
def test_receipts_say_only_what_was_measured_about_other_checks(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    proven = render(judge(facts(tmp_path / "a", pr=[(*UNIT, "pass"), (*A1, "pass"), (*A2, "pass")])))["top"]
    assert "None of your app's other checks failed." in proven
    broken = render(judge(facts(tmp_path / "b", pr=[(*UNIT, "assert"), (*A1, "pass"), (*A2, "pass")])))["top"]
    assert "Some of your app's other checks fail now." in broken
    assert "✗ Other checks in your app that fail now: 1." in broken
    for top in (proven, broken):
        assert "worked before" not in top and "still works" not in top and "stopped working" not in top
        assert lint("other-checks", top) == []


def test_readme_says_what_nothing_that_worked_before_broke_covers():
    limits = read("README.md").split("## What AsBuild does not prove", 1)[1].split("\n## ", 1)[0]
    for words in (
        "Only the tests you approved are protected.",
        "counts another test as broken only when it ran on the pull request and failed",
        "a test the agent deleted or skipped is not noticed",
        "a test that already fails on `main` counts as broken, so get `main` passing first",
    ):
        assert words in limits, words


def test_verdict_skill_never_has_the_agent_fix_a_test_the_change_did_not_touch():
    text = read("plugin/skills/verdict/SKILL.md")
    assert "never delete, skip or weaken them" in text
    assert "fail on `main` too" in text and "stop and tell the person which tests fail" in text


# Finding 3: the workflows run only the engine folder this release was built from, and install defusedxml by hash.
def engine_tree() -> str:
    """The Git tree id of engine/ as it is on disk now (committed or not), through a throwaway index."""
    index = ROOT / ".git" / "asbuild-engine-index"
    env = {**os.environ, "GIT_INDEX_FILE": str(index)}
    try:
        subprocess.run(["git", "add", "--", "engine"], cwd=ROOT, env=env, check=True, capture_output=True)
        out = subprocess.run(
            ["git", "write-tree", "--prefix=engine/"], cwd=ROOT, env=env, check=True, capture_output=True, text=True
        )
    finally:
        index.unlink(missing_ok=True)
    return out.stdout.strip()


def test_every_workflow_stops_unless_the_engine_is_this_release():
    expected = engine_tree()
    for f in WORKFLOWS:
        text = f.read_text(encoding="utf-8")
        ids = TREE_CHECK.findall(text)
        assert ids == [expected], (f, ids, expected)
        lines = text.splitlines()
        clone = next(i for i, line in enumerate(lines) if CLONE in line)
        assert TREE_CHECK.match(lines[clone + 1]), (f, "the check must follow the clone")


def test_engine_requirements_pin_defusedxml_with_its_hashes():
    pinned = read("engine/requirements.txt").strip()
    dev = next(line for line in read("requirements-dev.txt").splitlines() if line.startswith("defusedxml=="))
    assert pinned == dev.strip()
    assert pinned.startswith("defusedxml==0.7.1 ") and pinned.count("--hash=sha256:") == 2


def test_verdict_workflows_install_only_by_hash():
    for f in WORKFLOWS:
        text = f.read_text(encoding="utf-8")
        assert "defusedxml==" not in text, f
        if f.name == "asbuild-verdict.yml":
            assert text.count(HASHED) == 1, f


# Finding 4: the story skill says where the person's words go before saving them.
def test_story_skill_tells_the_person_before_saving_their_words():
    text = read("plugin/skills/story/SKILL.md")
    step1 = text.split("## 1.", 1)[1].split("\n## ", 1)[0]
    assert "anyone who can see the project can read them" in step1
    assert "leave out passwords, keys and other people's private details" in step1
    assert step1.index("anyone who can see") < step1.index("Create `dev-docs/stories/S<n>/story.md`")


# The README notes: the heading, and how an existing install moves to a new release.
def test_readme_install_heading_and_update_line():
    lines = read("README.md").splitlines()
    assert "### Before you start" in lines
    assert not any("OR move to" in line for line in lines)
    text = "\n".join(lines)
    skip = 'If Claude Code did the installation for you with the message above, go to "3. Agree your first story".'
    assert skip in text
    assert "To move to a newer AsBuild, update the plugin, then run `/asbuild:setup` again" in text
