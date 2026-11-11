"""The plugin folder's README, which Anthropic's directory requires and shows as the listing (D17)."""

import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugin"


def test_plugin_readme_has_40_words_outside_code_blocks():
    text = (PLUGIN / "README.md").read_text(encoding="utf-8")
    prose = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    assert len(prose.split()) >= 40


def test_plugin_readme_discloses_every_script_and_the_settings_line():
    text = (PLUGIN / "README.md").read_text(encoding="utf-8")
    for script in sorted((PLUGIN / "scripts").glob("*.py")):
        assert f"scripts/{script.name}" in text, f"the plugin README does not describe {script.name}"
    assert "`.claude/settings.json`" in text and "never removes or loosens" in text
    assert "github.com/hevelius-ai/asbuild#readme" in text
