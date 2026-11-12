"""Story S5: the setup skill and the install page that leads with it (D39, docs/plans/S5.md)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def install_section() -> str:
    lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    start = lines.index("## Install") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def test_S5_C11_setup_skill_runs_the_script_and_is_found_in_an_unwired_repository():
    text = (ROOT / "plugin" / "skills" / "setup" / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "---"
    front = lines[1 : lines.index("---", 1)]
    assert "name: setup" in front
    description = next(line for line in front if line.startswith("description: "))
    assert "`.github/workflows/asbuild-test.yml` is not on `origin/main`" in description
    assert "/asbuild:setup" in description
    assert 'python "${CLAUDE_PLUGIN_ROOT}/scripts/asbuild_setup.py"' in text
    assert "Never enter a password, key or token" in text
    assert "/asbuild:story" in text
    assert len(lines) < 60


def test_S5_C12_install_page_leads_with_the_three_steps():
    page = install_section()
    opening = page.split("\n### ", 1)[0]
    assert "1. Add the plugin to Claude." in opening
    assert "2. In your project, type `/asbuild:setup`." in opening
    assert "3. Say what you want with `/asbuild:story`." in opening
    assert "### Before you start" in page
    assert "### By hand" in page
    by_hand = page.split("### By hand", 1)[1]
    assert "curl -fsSL -o .github/workflows/asbuild-test.yml" in by_hand
    setup_part = page.split("### 2. Set it up", 1)[1].split("\n### ", 1)[0]
    assert "/asbuild:setup" in setup_part
    assert "gets no verdict" in setup_part
    assert "WAITING FOR YOU" in setup_part
