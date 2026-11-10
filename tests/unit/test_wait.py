"""Unit tests for plugin/scripts/asbuild_wait.py (decision D19)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugin" / "scripts"))
import asbuild_wait  # noqa: E402


def runs(*items):
    return json.dumps({"check_runs": list(items)})


def check(title, done=True, slug="github-actions", at="2026-11-10T10:00:00Z"):
    return {
        "name": "AsBuild",
        "app": {"slug": slug},
        "status": "completed" if done else "in_progress",
        "completed_at": at,
        "output": {"title": title, "summary": "details"},
    }


def fake(responses):
    seq = iter(responses)

    def run(*cmd):
        if cmd[:3] == ("gh", "repo", "view"):
            return "o/r"
        if cmd[:2] == ("git", "rev-parse"):
            return "c" * 40
        return next(seq)

    return run


@pytest.mark.parametrize(
    ("title", "code"),
    [
        ("AsBuild: PROVEN", 0),
        ("AsBuild: NOT PROVEN", 1),
        ("AsBuild: UNRESOLVED", 3),
        ("AsBuild: WAITING FOR YOU", 4),
        ("something else", 3),
        ("AsBuild: NEW NAME", 3),
    ],
)
def test_exit_code_per_verdict(title, code, capsys):
    resp = [runs(check("x", done=False), check("AsBuild: PROVEN", slug="other")), runs(check(title))]
    assert asbuild_wait.main(["--interval", "0"], run=fake(resp), sleep=lambda _s: None) == code
    assert "details" in capsys.readouterr().out


def test_latest_completed_run_wins():
    resp = [
        runs(
            check("AsBuild: NOT PROVEN", at="2026-11-10T10:00:00Z"), check("AsBuild: PROVEN", at="2026-11-10T11:00:00Z")
        )
    ]
    assert asbuild_wait.main(["--sha", "d" * 40], run=fake(resp), sleep=lambda _s: None) == 0


def test_timeout(capsys):
    ticks = iter([0, 0, 5, 11])
    resp = [runs(), runs()]
    rc = asbuild_wait.main(
        ["--timeout", "10", "--interval", "1"], run=fake(resp), sleep=lambda _s: None, clock=lambda: next(ticks)
    )
    assert rc == 7
    assert "timeout" in capsys.readouterr().out


def test_sh_runs_and_fails():
    assert asbuild_wait.sh(sys.executable, "-c", "print('ok')") == "ok"
    with pytest.raises(asbuild_wait.ToolError, match="failed"):
        asbuild_wait.sh(sys.executable, "-c", "import sys; sys.exit(2)")


def test_a_failed_tool_is_exit_5_never_not_proven(capsys):
    def broken(*_cmd):
        raise asbuild_wait.ToolError("gh api failed: HTTP 401")

    assert asbuild_wait.main([], run=broken, sleep=lambda _s: None) == 5
    assert "could not ask GitHub" in capsys.readouterr().out


def test_no_output_block():
    assert asbuild_wait.verdict_of({}) == "UNRESOLVED"
    assert (
        asbuild_wait.main(
            [],
            run=fake([runs({"name": "AsBuild", "app": {"slug": "github-actions"}, "status": "completed"})]),
            sleep=lambda _s: None,
        )
        == 3
    )


def test_subprocess_is_used(monkeypatch):
    monkeypatch.setattr(asbuild_wait.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, " x \n", ""))
    assert asbuild_wait.sh("anything") == "x"
