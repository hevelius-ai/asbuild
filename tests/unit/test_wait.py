"""Unit tests for plugin/scripts/asbuild_wait.py (decisions D19, D50).

Since v0.4.0 (D50, AsChecked B4) the script reads the verdict that AsBuild's verdict workflow saves as a file attached
to its own run, and only from a run of `.github/workflows/asbuild-verdict.yml` that GitHub started by `workflow_run`
(only the default branch's copy of a workflow runs that way, so a pull request can neither start such a run nor change
its file). A check run or file posted by any other workflow, such as one a pull request adds, is never read.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugin" / "scripts"))
import asbuild_wait  # noqa: E402

SHA = "c" * 40
REAL = {"path": ".github/workflows/asbuild-verdict.yml", "event": "workflow_run"}


def art(run_id, at="2026-11-15T10:00:00Z", name=f"asbuild-verdict-{SHA}", expired=False):
    return {"name": name, "created_at": at, "expired": expired, "workflow_run": {"id": run_id}}


def fake(artifact_pages, runs, files, calls=None):
    """artifact_pages: the artifact lists answered in turn; runs: {run_id: run};
    files: {run_id: (verdict doc, summary)}."""
    pages = iter(artifact_pages)

    def run(*cmd):
        if calls is not None:
            calls.append(cmd)
        if cmd[:3] == ("gh", "repo", "view"):
            return "o/r"
        if cmd[:2] == ("git", "rev-parse"):
            return SHA
        if cmd[:2] == ("gh", "api") and "/actions/artifacts?" in cmd[2]:
            return json.dumps({"artifacts": next(pages)})
        if cmd[:2] == ("gh", "api") and "/actions/runs/" in cmd[2]:
            return json.dumps(runs[int(cmd[2].rsplit("/", 1)[1])])
        if cmd[:3] == ("gh", "run", "download"):
            doc, summary = files[int(cmd[3])]
            out = Path(cmd[cmd.index("--dir") + 1])
            if doc is not None:
                (out / "verdict.json").write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")
            if summary is not None:
                (out / "summary.md").write_text(summary, encoding="utf-8")
            return ""
        raise AssertionError(cmd)

    return run


def go(run, *args):
    return asbuild_wait.main(["--interval", "0", *args], run=run, sleep=lambda _s: None)


@pytest.mark.parametrize(
    ("verdict", "code"),
    [("PROVEN", 0), ("NOT PROVEN", 1), ("UNRESOLVED", 3), ("WAITING FOR YOU", 4), ("NEW NAME", 3)],
)
def test_SF_C2_exit_code_per_verdict_from_the_saved_file(verdict, code, capsys):
    run = fake([[], [art(9)]], {9: REAL}, {9: ({"verdict": verdict, "head_sha": SHA}, "details")})
    assert go(run) == code
    out = capsys.readouterr().out
    assert f"verdict: {verdict}" in out and "details" in out


def test_SF_C2_a_file_from_any_other_workflow_is_never_read(capsys):
    """A workflow the pull request adds can save a file with the same name; its run is not the verdict workflow
    started by workflow_run, so it is skipped, and the real verdict (older here) is the one reported."""
    fakes = {
        1: {"path": ".github/workflows/fake.yml", "event": "pull_request"},
        2: {"path": ".github/workflows/asbuild-verdict.yml", "event": "pull_request"},  # the PR's own copy, changed
        3: {"path": ".github/workflows/fake.yml", "event": "workflow_run"},
    }
    arts = [art(1, "2026-11-15T12:00:00Z"), art(2, "2026-11-15T11:00:00Z"), art(3, "2026-11-15T10:30:00Z")]
    arts += [art(9, "2026-11-15T10:00:00Z")]
    files = {i: ({"verdict": "PROVEN", "head_sha": SHA}, "fake") for i in fakes}
    files[9] = ({"verdict": "WAITING FOR YOU", "head_sha": SHA}, "real")
    calls: list = []
    assert go(fake([arts], {**fakes, 9: REAL}, files, calls)) == 4
    assert "real" in capsys.readouterr().out
    assert [c[3] for c in calls if c[:3] == ("gh", "run", "download")] == ["9"]  # no fake file was even opened


def test_SF_C2_only_fakes_means_no_verdict_yet(capsys):
    ticks = iter([0, 0, 11])
    run = fake([[art(1)]], {1: {"path": ".github/workflows/fake.yml", "event": "pull_request"}}, {})
    rc = asbuild_wait.main(
        ["--timeout", "10", "--interval", "1"], run=run, sleep=lambda _s: None, clock=lambda: next(ticks)
    )
    assert rc == 7
    out = capsys.readouterr().out
    assert "timeout" in out and "/asbuild:setup" in out


def test_SF_C2_the_newest_real_verdict_for_this_commit_wins():
    arts = [
        art(8, "2026-11-15T09:00:00Z"),
        art(9, "2026-11-15T11:00:00Z"),
        art(7, "2026-11-15T12:00:00Z", expired=True),
    ]
    files = {8: ({"verdict": "NOT PROVEN", "head_sha": SHA}, ""), 9: ({"verdict": "PROVEN", "head_sha": SHA}, "")}
    assert go(fake([arts], {8: REAL, 9: REAL, 7: REAL}, files)) == 0


def test_SF_C2_the_commit_inside_the_file_must_match(capsys):
    arts = [
        art(9, "2026-11-15T11:00:00Z"),
        art(8, "2026-11-15T10:00:00Z"),
        {"name": "x", "created_at": "2026-11-15T13:00:00Z"},
    ]
    files = {9: ({"verdict": "PROVEN", "head_sha": "d" * 40}, ""), 8: ({"verdict": "NOT PROVEN", "head_sha": SHA}, "")}
    assert go(fake([arts], {8: REAL, 9: REAL}, files)) == 1


def test_SF_C2_an_unreadable_real_file_is_unresolved_never_an_older_verdict(capsys):
    arts = [art(9, "2026-11-15T12:00:00Z"), art(8, "2026-11-15T11:00:00Z")]
    older = ({"verdict": "PROVEN", "head_sha": SHA}, "older")
    for newest in (("not json", "x"), (None, None), ({"head_sha": SHA}, None), (["a list"], None)):
        assert go(fake([arts], {8: REAL, 9: REAL}, {9: newest, 8: older})) == 3, newest
        out = capsys.readouterr().out
        assert "verdict: UNRESOLVED" in out and "older" not in out


def test_SF_C2_it_asks_for_this_commits_file_by_name():
    calls: list = []
    go(fake([[art(9)]], {9: REAL}, {9: ({"verdict": "PROVEN", "head_sha": SHA}, "")}, calls), "--sha", SHA)
    asked = [c[2] for c in calls if c[:2] == ("gh", "api")]
    assert asked[0] == f"repos/o/r/actions/artifacts?name=asbuild-verdict-{SHA}&per_page=100"
    assert asked[1] == "repos/o/r/actions/runs/9"


def test_sh_runs_and_fails():
    assert asbuild_wait.sh(sys.executable, "-c", "print('ok')") == "ok"
    with pytest.raises(asbuild_wait.ToolError, match="failed"):
        asbuild_wait.sh(sys.executable, "-c", "import sys; sys.exit(2)")


def test_a_failed_tool_is_exit_5_never_not_proven(capsys):
    def broken(*_cmd):
        raise asbuild_wait.ToolError("gh api failed: HTTP 401")

    assert asbuild_wait.main([], run=broken, sleep=lambda _s: None) == 5
    assert "could not ask GitHub" in capsys.readouterr().out


def test_subprocess_is_used(monkeypatch):
    monkeypatch.setattr(asbuild_wait.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, " x \n", ""))
    assert asbuild_wait.sh("anything") == "x"


def test_missing_program_or_unreadable_answer_is_exit_5(capsys):
    with pytest.raises(asbuild_wait.ToolError, match="could not run"):
        asbuild_wait.sh("asbuild-no-such-program-xyz")

    def garbled(*cmd):
        return "o/r" if cmd[:3] == ("gh", "repo", "view") else "not json"

    assert asbuild_wait.main(["--sha", SHA], run=garbled, sleep=lambda _s: None) == 5
    assert "not readable" in capsys.readouterr().out
