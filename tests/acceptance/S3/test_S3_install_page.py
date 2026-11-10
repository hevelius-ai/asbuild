"""Story S3: the install page (README.md's "## Install" section) and the verdict skill.

The tests check the page against the repository's own files, so a renamed workflow file, marketplace or plugin
fails here rather than on a reader's machine. Following the page live on auto-job-search is shown in the PR.
"""

import json
import re
from pathlib import Path

from plugin.scripts import asbuild_wait

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
