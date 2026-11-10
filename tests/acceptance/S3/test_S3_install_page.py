"""Story S3: the install page (README.md's "## Install" section) and the verdict skill.

The tests check the page against the repository's own files, so a renamed workflow file, marketplace or plugin
fails here rather than on a reader's machine. Following the page live on auto-job-search is shown in the PR.
"""

import json
import re
from pathlib import Path

from plugin.scripts import asbuild_wait
from tests.acceptance.S2.test_S2_story_checks import GOOD_C1, GOOD_C2, make_repo, run_checks

ROOT = Path(__file__).resolve().parents[3]
VERDICT_SKILL = ROOT / "plugin" / "skills" / "verdict" / "SKILL.md"
RAW = "https://raw.githubusercontent.com/hevelius-ai/asbuild/main/"


def install_section():
    lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    assert "## Install" in lines, "README.md has no '## Install' section"
    start = lines.index("## Install") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def install_id():
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    (entry,) = market["plugins"]
    plugin_root = ROOT / entry["source"]
    plugin = json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert entry["name"] == plugin["name"]
    return f"{plugin['name']}@{market['name']}"


def test_S3_C1_install_page_matches_the_repository():
    page = install_section()
    plugin_id = install_id()
    assert plugin_id == "asbuild@hevelius-ai"
    # in Claude Code
    assert "/plugin marketplace add hevelius-ai/asbuild" in page
    assert f"/plugin install {plugin_id}" in page
    # from a script or Claude's shell: the marketplace first (G6 runs 2 and 3), and Git is needed (G6 run 2)
    add = page.find("claude plugin marketplace add hevelius-ai/asbuild")
    install = page.find(f"claude plugin install {plugin_id}")
    assert add != -1 and install != -1 and add < install
    assert "Git is needed" in page
    # exactly the two workflow files, which exist, into .github/workflows/
    urls = set(re.findall(re.escape(RAW) + r"(\S+?\.yml)", page))
    assert urls == {"workflows/asbuild-test.yml", "workflows/asbuild-verdict.yml"}
    assert all((ROOT / u).is_file() for u in urls)
    assert ".github/workflows/asbuild-test.yml" in page and ".github/workflows/asbuild-verdict.yml" in page
    # the wiring pull request
    assert "gets no verdict" in page
    assert "`workflow` scope" in page
    # what the reader's repository needs
    for need in (
        "GitHub Actions",
        "Python 3.12",
        "pytest",
        "`requirements.txt`",
        "`dev-docs/stories/`",
        "`tests/acceptance/`",
        "`locks.json`",
        "`build/S<n>`",
    ):
        assert need in page, f"the page does not name {need}"
    assert "/asbuild:story" in page
    # no time claim until done line 3 gives one
    assert not re.search(r"\b\d+\s*(s|sec|secs|seconds?|min|mins|minutes?|hours?)\b", page, re.IGNORECASE)


def settings_of(repo):
    return json.loads((repo / ".claude" / "settings.json").read_text(encoding="utf-8"))


def test_S3_C2_story_lock_adds_the_deny_line_and_page_says_what_it_misses(tmp_path):
    line = "Edit(/tests/acceptance/S1/**)"
    # a repository with settings of its own: they are kept, and the story's line is added once
    repo = make_repo(tmp_path / "a", GOOD_C1 + GOOD_C2)
    (repo / ".claude").mkdir()
    own = {"model": "claude-sonnet-5-5", "permissions": {"allow": ["Bash(ls)"], "deny": ["Read(./.env)"]}}
    (repo / ".claude" / "settings.json").write_text(json.dumps(own, indent=2) + "\n", encoding="utf-8")
    out = run_checks(repo, "--lock")
    assert out.returncode == 0, out.stdout + out.stderr
    assert settings_of(repo) == {
        "model": "claude-sonnet-5-5",
        "permissions": {"allow": ["Bash(ls)"], "deny": ["Read(./.env)", line]},
    }
    out = run_checks(repo, "--lock")
    assert out.returncode == 0, out.stdout + out.stderr
    assert settings_of(repo)["permissions"]["deny"] == ["Read(./.env)", line]
    # a repository without settings: the file is created with the one line
    repo = make_repo(tmp_path / "b", GOOD_C1 + GOOD_C2)
    out = run_checks(repo, "--lock")
    assert out.returncode == 0, out.stdout + out.stderr
    assert settings_of(repo) == {"permissions": {"deny": [line]}}
    # when a check fails, nothing is locked and no line is added
    passing = GOOD_C1.replace('== "words: 3"', '!= "words: 3"').replace("assert out.returncode == 0\n", "")
    repo = make_repo(tmp_path / "c", passing + GOOD_C2)
    out = run_checks(repo, "--lock")
    assert out.returncode == 1, out.stdout + out.stderr
    assert not (repo / ".claude" / "settings.json").exists()
    # the skill commits the line with the story; the page says what the line does and does not cover
    skill = (ROOT / "plugin" / "skills" / "story" / "SKILL.md").read_text(encoding="utf-8")
    assert "`.claude/settings.json`" in skill
    page = install_section()
    assert "`Edit(/tests/acceptance/S<n>/**)`" in page
    assert "`.claude/settings.json`" in page
    assert "a script that opens a file itself is not blocked" in page
    assert "CI is the check" in page


def test_S3_C3_verdict_after_each_push():
    page = install_section()
    assert "/asbuild:verdict" in page
    assert "after each push" in page.lower()
    assert "gh pr checks --watch" in page
    text = VERDICT_SKILL.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) < 60
    assert lines[0] == "---" and "---" in lines[1:]
    front = lines[1 : lines.index("---", 1)]
    assert "name: verdict" in front
    assert any(line.startswith("description: ") and "push" in line for line in front)
    assert 'python "${CLAUDE_PLUGIN_ROOT}/scripts/asbuild_wait.py"' in text
    codes = {**asbuild_wait.EXIT, "could not ask GitHub": asbuild_wait.TOOL_FAILED, "no verdict yet": 7}
    for name, code in codes.items():
        assert re.search(rf"^- \*\*{code} {re.escape(name)}", text, re.MULTILINE | re.IGNORECASE), (
            f"the verdict skill does not say what to do on exit {code} ({name})"
        )
