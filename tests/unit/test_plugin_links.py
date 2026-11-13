"""Release v0.3.2: the directory listing's links in plugin.json, each pointing at a file this repository holds."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = "https://github.com/hevelius-ai/asbuild"


def manifest() -> dict:
    return json.loads((ROOT / "plugin" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))


def test_listing_links_point_at_this_repository():
    m = manifest()
    assert m["supportUrl"] == f"{REPO}/issues"
    assert m["documentationUrl"] == f"{REPO}#install"
    assert "## Install" in (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    assert m["privacyPolicyUrl"] == f"{REPO}/blob/main/PRIVACY.md"
    assert (ROOT / "PRIVACY.md").is_file()
    assert m["termsOfServiceUrl"] == f"{REPO}/blob/main/LICENSE"
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")


def test_privacy_page_says_what_asbuild_collects_and_sends():
    text = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
    assert "Hevelius AI Group LLC" in text
    assert "collects no personal data" in text
    assert "no server" in text and "no analytics" in text
    assert "your own `git` and `gh`" in text
    assert "no repository secrets" in text
    assert f"{REPO}/issues" in text


def test_plugin_readme_installs_in_one_step():
    text = (ROOT / "plugin" / "README.md").read_text(encoding="utf-8")
    assert "/plugin install asbuild --marketplace hevelius-ai/asbuild" in text
