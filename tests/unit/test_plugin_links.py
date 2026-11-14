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
    assert m["termsOfServiceUrl"] == f"{REPO}/blob/main/TERMS.md"
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")


def test_terms_disclaim_warranty_and_liability_where_people_read():
    terms = (ROOT / "TERMS.md").read_text(encoding="utf-8")
    assert "created by Hevelius AI Group LLC" in terms and "MIT License" in terms
    for heading in ("## No warranty", "## No liability", "## Your responsibility"):
        assert heading in terms, heading
    assert 'provided "as is"' in terms and "without warranty of any kind" in terms
    assert "To the fullest extent permitted by law" in terms and "are not liable for any claim" in terms
    assert "You use AsBuild at your own risk" in terms and "not a guarantee" in terms
    # the MIT licence grants use without restriction: the terms describe the purpose, they do not limit use
    assert "only as intended" not in terms and "your own GitHub repositories" not in terms
    # the short form, on the privacy page and in the README's licence section, points at the terms
    privacy = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
    licence = (ROOT / "README.md").read_text(encoding="utf-8").split("## Licence", 1)[1]
    for page in (privacy, licence):
        assert "created by Hevelius AI Group LLC" in page and "without warranty of any kind" in page
        assert "is not liable for any damage or loss" in page and "you use it at your own risk" in page
        assert "(TERMS.md)" in page


def test_privacy_page_says_what_asbuild_collects_and_sends():
    text = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
    assert "Hevelius AI Group LLC" in text
    assert "collects no personal data" in text
    assert "no server" in text and "no analytics" in text
    assert "counts of visits to the AsBuild repository and of how often it is copied" in text  # anonymous counts
    assert "It sends data only to GitHub, through your own `git` and `gh`" in text
    # every upload the plugin makes is named: setup's branches, the story pull request, the builds
    for upload in ("`asbuild-setup`", "first uploads `main`", "story pull request", "The AI's builds"):
        assert upload.lower() in text.lower(), upload
    assert "no repository secrets" in text
    assert "only GitHub and the Python Package Index (PyPI)" in text and "`defusedxml`" in text
    # review round 1: the two absolute claims that were false stay out
    assert "Nothing else leaves your computer" not in text
    assert "nothing outside GitHub" not in text
    assert f"{REPO}/issues" in text


def test_privacy_page_names_every_package_the_workflows_install():
    for name in ("asbuild-test.yml", "asbuild-verdict.yml"):
        flow = (ROOT / "workflows" / name).read_text(encoding="utf-8")
        for line in (x.strip() for x in flow.splitlines() if "pip install" in x):
            # v0.3.3: AsBuild's own package comes from its hashed file, which names only defusedxml
            ok = line.endswith(" -r requirements.txt") or line.endswith(
                '-r "$RUNNER_TEMP/asbuild-run/engine/requirements.txt"'
            )
            assert ok, line
    assert (ROOT / "engine" / "requirements.txt").read_text(encoding="utf-8").startswith("defusedxml==0.7.1 ")


def test_plugin_readme_installs_in_one_step():
    text = (ROOT / "plugin" / "README.md").read_text(encoding="utf-8")
    # the shell form, which `claude plugin install --help` documents (--marketplace <source>)
    assert "claude plugin install asbuild --marketplace hevelius-ai/asbuild" in text
