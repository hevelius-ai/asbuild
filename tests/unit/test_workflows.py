"""Structure tests for the two workflow templates: the parts the verdict's safety rests on.

These add to the locked S1-C6 acceptance test (which stays unchanged): the trusted job takes the commit and the
artifact only from the workflow_run event, never fetches or runs the pull request's code, always posts a check
run, matches only same-repository pull requests whose head is the commit, and calls the engine with arguments
the engine accepts.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import yaml

from engine import c3_overlay, verdict

ROOT = Path(__file__).resolve().parents[2]


def wf(name):
    return yaml.safe_load((ROOT / "workflows" / name).read_text(encoding="utf-8"))


def steps(name):
    return [s for job in wf(name)["jobs"].values() for s in job["steps"]]


def step(name, title):
    return next(s for s in steps(name) if s.get("name", "").startswith(title))


def command(run, script):
    """The arguments a run step passes to one engine script, with line continuations joined."""
    line = next(ln for ln in run.replace("\\\n", " ").splitlines() if script in ln)
    args = shlex.split(line)
    return args[args.index(next(a for a in args if a.endswith(script))) + 1 :]


def test_trusted_job_takes_commit_and_artifact_from_the_event_only():
    job = wf("asbuild-verdict.yml")["jobs"]["verdict"]
    assert job["env"]["HEAD_SHA"] == "${{ github.event.workflow_run.head_sha }}"
    dl = next(s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/download-artifact"))
    assert dl["with"]["run-id"] == "${{ github.event.workflow_run.id }}"
    assert dl["continue-on-error"] is True
    text = (ROOT / "workflows" / "asbuild-verdict.yml").read_text(encoding="utf-8")
    for banned in (
        "pull_request.head",
        "gh pr checkout",
        "git checkout",
        "git fetch",
        "pip install -r",
        "bash ./",
        "sh ./",
        "source ",
        "evidence/*.sh",
        "pytest",
    ):
        assert banned not in text, banned


def test_every_step_runs_only_trusted_code():
    for s in steps("asbuild-verdict.yml"):
        run = s.get("run", "")
        for target in re.findall(r"\bpython3?\s+(\S+(?:\s+\S+){0,3})", run):
            assert target.startswith('"$ASBUILD/engine/') or target == "-m pip install --quiet", target
        # v0.3.3 (D45): besides the clone, only the read of the trusted clone's engine tree id
        for target in re.findall(r"\bgit\s+(\S+(?:\s+\S+){0,2})", run):
            assert target.split()[0] == "clone" or target == '-C "$RUNNER_TEMP/asbuild" rev-parse', target
        if "git clone" in run:
            assert "https://github.com/hevelius-ai/asbuild " in run


def test_check_run_is_always_posted_with_the_right_conclusion():
    post = step("asbuild-verdict.yml", "Post the check run")
    assert post["if"].startswith("always()") and "skip" in post["if"]
    assert step("asbuild-verdict.yml", "Post the receipt")["if"].startswith("always()")
    run = post["run"]
    assert "PROVEN) c=success" in run and '"WAITING FOR YOU") c=action_required' in run and "*) c=failure" in run
    assert 'name: "AsBuild"' in run and '--arg title "AsBuild: $verdict"' in run
    assert '{"verdict": "UNRESOLVED"}' in run


def test_lookup_matches_same_repo_pr_whose_head_is_this_commit():
    run = step("asbuild-verdict.yml", "Find the pull request")["run"]
    for clause in (".head.repo.full_name == $repo", ".head.sha == $sha", ".base.ref == $main", '.state == "open"'):
        assert clause in run, clause
    assert wf("asbuild-verdict.yml")["jobs"]["verdict"]["defaults"]["run"]["shell"] == "bash"


def test_untrusted_job_has_no_write_rights_and_judges_main_only():
    w = wf("asbuild-test.yml")
    assert w["permissions"] == {"contents": "read"}
    assert w.get("on", w.get(True))["pull_request"]["branches"] == ["main"]
    up = next(s for s in steps("asbuild-test.yml") if str(s.get("uses", "")).startswith("actions/upload-artifact"))
    assert up["if"] == "always()"
    assert all(s.get("continue-on-error") for s in steps("asbuild-test.yml") if "pytest" in s.get("run", ""))


def test_templates_call_the_engine_with_arguments_it_accepts(tmp_path):
    run = step("asbuild-verdict.yml", "Compute the verdict")["run"]
    args = verdict.parser().parse_args(command(run, "engine/verdict.py"))
    assert args.main == "." and args.evidence == "evidence/"
    over = step("asbuild-test.yml", "Fails before")["run"]
    args = c3_overlay.parser().parse_args(command(over, "engine/c3_overlay.py"))
    assert args.out == "out/c3"


def test_all_actions_pinned_by_commit():
    for name in ("asbuild-test.yml", "asbuild-verdict.yml"):
        for s in steps(name):
            if "uses" in s:
                assert re.fullmatch(r"actions/[\w-]+@[0-9a-f]{40}", s["uses"]), s["uses"]


def test_plugin_and_every_workflow_clone_one_version():
    """D32: the plugin's version and the AsBuild tag every workflow file clones are one number."""
    import json

    version = json.loads((ROOT / "plugin" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    names = ("asbuild-test.yml", "asbuild-verdict.yml")
    files = [ROOT / d / n for d in ("workflows", "plugin/workflows") for n in names]
    for f in files:
        tags = re.findall(r"--branch (\S+) https://github\.com/hevelius-ai/asbuild", f.read_text(encoding="utf-8"))
        assert tags == [f"v{version}"], (f, tags, version)
