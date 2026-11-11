"""Story S4, decision D29: the clean-install job (engineering-build-loop 2.4) in AsBuild's own CI.

On every pull request from this repository, a clean runner installs the plugin the way the README's install page
says (its step 1), from the pull request's own commit, starts the installed scripts from outside the checkout, and
runs the acceptance tests against the installed copy. The job itself runs in CI; this test holds its shape, so a
later edit cannot quietly turn it into a run of the checkout or let it reach a secret.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / ".github" / "workflows" / "ci.yml"


def steps_text(job):
    return "\n".join(str(step.get("run", "")) + " " + str(step.get("uses", "")) for step in job["steps"])


def test_S4_C4_ci_installs_from_the_marketplace_and_tests_the_installed_copy():
    source = CI.read_text(encoding="utf-8")
    ci = yaml.safe_load(source)
    assert "clean-install" in ci["jobs"], "AsBuild's CI has no clean-install job"
    job = ci["jobs"]["clean-install"]
    assert job["strategy"]["matrix"]["os"] == ["ubuntu-latest", "windows-latest"]
    text = steps_text(job)
    # the commit installed is the pull request's own head, the one checked out
    checkout = next(s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/checkout@"))
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.head.sha || github.sha }}"
    # Claude Code itself, pinned to an exact version
    assert "npm install --global @anthropic-ai/claude-code@2.1.319" in text
    # the README's two commands; only the source differs: this pull request's branch of the same repository
    assert 'claude plugin marketplace add "hevelius-ai/asbuild#$REF"' in text
    assert "claude plugin install asbuild@hevelius-ai" in text
    # the installed copy is the commit checked out, equals what the repository ships, starts on its own from outside
    # the checkout, and replaces plugin/ before the acceptance tests run
    order = [
        "claude plugin install",
        'tests/install_check.py "$RUNNER_TEMP/installed.json" --commit "$(git rev-parse HEAD)"',
        'cd "$RUNNER_TEMP"',
        'python "$ASBUILD_INSTALLED/scripts/asbuild_story_check.py" --help',
        'python "$ASBUILD_INSTALLED/scripts/asbuild_wait.py" --help',
        "rm -rf plugin",
        'cp -R "$ASBUILD_INSTALLED" plugin',
        "python -m pytest tests/acceptance",
    ]
    assert all(s in text for s in order), [s for s in order if s not in text]
    assert [text.index(s) for s in order] == sorted(text.index(s) for s in order)
    # no step can fail quietly
    assert not any("continue-on-error" in step for step in job["steps"])
    assert not re.search(r"\|\|\s*true", text)
    # nothing in the job can reach a secret or write to the repository
    assert ci["permissions"] == {"contents": "read"}
    assert "permissions" not in job
    for word in ("secrets", "github.token", "pull_request_target"):
        assert word not in source, f"ci.yml mentions {word}"
