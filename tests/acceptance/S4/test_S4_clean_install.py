"""Story S4, decision D29: the clean-install job (engineering-build-loop 2.4) in AsBuild's own CI.

On every pull request, a clean runner installs AsBuild the way the README's install page says, from the pull
request's branch, and runs the acceptance tests against the installed copy. The job itself runs in CI; this test
holds its shape, so a later edit cannot quietly turn it into a run of the checkout.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CI = ROOT / ".github" / "workflows" / "ci.yml"


def steps_text(job):
    return "\n".join(str(step.get("run", "")) + " " + str(step.get("uses", "")) for step in job["steps"])


def test_S4_C4_ci_installs_from_the_marketplace_and_tests_the_installed_copy():
    ci = yaml.safe_load(CI.read_text(encoding="utf-8"))
    assert "clean-install" in ci["jobs"], "AsBuild's CI has no clean-install job"
    job = ci["jobs"]["clean-install"]
    assert job["strategy"]["matrix"]["os"] == ["ubuntu-latest", "windows-latest"]
    text = steps_text(job)
    # Claude Code itself, pinned to an exact version (npm checks its integrity hash)
    assert "npm install --global @anthropic-ai/claude-code@2.1.319" in text
    # the README's two commands; only the source differs: this pull request's branch of the same repository
    assert 'claude plugin marketplace add "hevelius-ai/asbuild#$REF"' in text
    assert "claude plugin install asbuild@hevelius-ai" in text
    # the installed copy must equal what the repository ships, and the acceptance tests run against it
    assert "tests/install_check.py" in text
    assert "python -m pytest tests/acceptance" in text
    order = [text.index(s) for s in ("claude plugin install", "tests/install_check.py", "python -m pytest tests/acceptance")]
    assert order == sorted(order)
    # nothing in the job can reach a secret or write to the repository
    assert ci["permissions"] == {"contents": "read"}
    assert "secrets." not in CI.read_text(encoding="utf-8")
