"""M3-C4 to M3-C6: the skills' and READMEs' lines for TypeScript and JavaScript apps (docs/plans/v0.4-M3.md)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def section(text: str, title: str) -> str:
    return text.split(title + "\n", 1)[1].split("\n## ", 1)[0]


def test_M3_C4_the_story_skill_points_a_javascript_app_to_javascript_md():
    skill = read("plugin/skills/story/SKILL.md")
    assert "follow `javascript.md`, in this skill's folder, in place of this section" in skill
    assert "`package.json` and `package-lock.json`" in section(skill, "## 6. Open the story pull request")
    assert "Node.js 24 with npm 11.19 (a TypeScript or JavaScript app)" in skill.split("\n---", 1)[0]


def test_M3_C4_javascript_md_says_how_to_write_each_check():
    text = read("plugin/skills/story/javascript.md")
    for words in (
        'python "${CLAUDE_PLUGIN_ROOT}/scripts/asbuild_js.py" tools',
        "`tests/acceptance/S<n>/S<n>-C<m>.test.tsx`",
        '`test("S<n>-C<m> <what the person sees>", () => { ... });`',
        "// @vitest-environment jsdom",
        'import { expect, test } from "vitest";',
        "MemoryRouter",
        'window.history.pushState({}, "", "/settings")',
        'expect(document.body.textContent).toContain("Saved")',
        "expect(save).not.toBeNull();",
        "Never add a setup file, a mock of the app's own code",
        "Import only files that exist on `main` now",
        # evidence 1 (2026-11-18): the page inside a router worked in all four Lovable apps; App needed one of these
        "render(<MemoryRouter><Index /></MemoryRouter>)",
        "window.matchMedia ??= ",
        '<MemoryRouter initialEntries={["/settings"]}><App /></MemoryRouter>',
    ):
        assert words in text, words
    for form in ("describe", "it.each", ".only", ".skip", ".todo", ".fails"):
        assert f"`{form}`" in text, form


def test_M3_C5_the_verdict_skill_names_the_javascript_files_and_the_package_rule():
    text = read("plugin/skills/verdict/SKILL.md")
    unresolved = next(line for line in text.splitlines() if line.startswith("- **3 UNRESOLVED:**"))
    assert "`package.json` or `package-lock.json`" in unresolved
    waiting = next(line for line in text.splitlines() if line.startswith("- **4 WAITING FOR YOU:**"))
    assert "a build that adds or changes a package waits for the person" in waiting


def test_M3_C3_the_setup_skill_stops_on_not_yet_without_running_again():
    text = read("plugin/skills/setup/SKILL.md")
    assert '- **1, starting "AsBuild cannot check this project yet":**' in text
    assert "Node.js 24 or newer with npm 11.19 or newer" in text.split("\n---", 1)[0]


def test_M3_C6_the_readme_names_node_the_apps_and_the_vitest_limit():
    readme = read("README.md")
    before = section(readme, "### Before you start")
    assert "Node.js 24 or newer, with npm 11.19 or newer" in before
    assert "`winget install --id OpenJS.NodeJS.LTS`" in before and "https://nodejs.org" in before
    assert "a TypeScript or JavaScript app made with React and Vite 5 to 8" in before
    assert "AsBuild adds Vitest, the tool its checks run with, in your first story" in before
    assert "push the app to `main` before setup" in before
    limits = section(readme, "## What AsBuild does not prove")
    line = "In a TypeScript or JavaScript app, your other tests are the app's Vitest tests"
    assert line in limits and not re.search(r"^\d\. " + re.escape(line), limits, re.MULTILINE)  # not numbered
    block = re.findall(r"```text\n(.*?)```", readme, re.DOTALL)[0]
    assert "node --version, npm --version" in block and "winget install --id OpenJS.NodeJS.LTS" in block


def test_M3_C6_the_plugin_says_it_works_with_react_and_vite_apps():
    meta = json.loads(read("plugin/.claude-plugin/plugin.json"))
    assert "a TypeScript or JavaScript app made with React and Vite" in meta["description"]
    assert meta["version"] == "0.3.4"  # the version moves in M4
    text = read("plugin/README.md")
    assert "to the npm registry, through your own `npm`" in text
    assert "`.asbuild-story/`" in text and "`scripts/asbuild_js.py tools`" in text
