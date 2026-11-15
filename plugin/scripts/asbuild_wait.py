#!/usr/bin/env python3
"""Wait for the AsBuild verdict on the current commit and print it (ported from step 0; decisions D19, D50).

`gh pr checks --watch` returns when the test workflow finishes, a few seconds before the verdict workflow posts its
verdict. This script waits for the verdict itself.

Since v0.4.0 it reads only the verdict that AsBuild's verdict workflow saves as a file attached to its own run
(`asbuild-verdict-<commit>`), and only from a run of `.github/workflows/asbuild-verdict.yml` that GitHub started by
`workflow_run`. GitHub runs a `workflow_run` workflow only from the default branch's copy, so a pull request can
neither start such a run nor change what it does. A check run named "AsBuild", or a file of that name, posted by any
other workflow (one a pull request adds, for example) is never read (D50, AsChecked B4).

Usage (from the repository root, after `git push`): python asbuild_wait.py [--timeout 1200] [--sha SHA]

Prints the verdict and its summary and exits:
  0 PROVEN   1 NOT PROVEN   3 UNRESOLVED   4 WAITING FOR YOU
  5 could not ask GitHub (gh or git failed: not logged in, no network)   7 timeout (no verdict yet)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

EXIT = {"PROVEN": 0, "NOT PROVEN": 1, "UNRESOLVED": 3, "WAITING FOR YOU": 4}
TOOL_FAILED = 5
VERDICT_WORKFLOW = ".github/workflows/asbuild-verdict.yml"


class ToolError(Exception):
    """gh or git failed, so there is no verdict to report."""


def sh(*cmd: str) -> str:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    except OSError as e:  # the program is not installed or cannot start
        raise ToolError(f"{cmd[0]} could not run: {e}") from e
    if p.returncode != 0:
        raise ToolError(f"{' '.join(cmd)} failed: {p.stderr.strip()}")
    return p.stdout.strip()


def api(run: Callable[..., str], path: str) -> dict:
    reply = run("gh", "api", path)
    try:
        data = json.loads(reply)
    except ValueError as e:
        raise ToolError(f"GitHub's answer was not readable: {reply[:200]}") from e
    return data if isinstance(data, dict) else {}


def saved_verdict(repo: str, sha: str, run: Callable[..., str]) -> tuple[str, str] | None:
    """(verdict, summary) from the newest file AsBuild's own verdict workflow saved for this commit, or None."""
    name = f"asbuild-verdict-{sha}"
    found = api(run, f"repos/{repo}/actions/artifacts?name={name}&per_page=100").get("artifacts", [])
    for art in sorted(found, key=lambda a: a.get("created_at") or "", reverse=True):
        run_id = (art.get("workflow_run") or {}).get("id")
        if art.get("expired") or art.get("name") != name or not run_id:
            continue
        origin = api(run, f"repos/{repo}/actions/runs/{run_id}")
        if origin.get("path") != VERDICT_WORKFLOW or origin.get("event") != "workflow_run":
            continue  # posted by another workflow: never read
        with tempfile.TemporaryDirectory() as d:
            run("gh", "run", "download", str(run_id), "--repo", repo, "--name", name, "--dir", d)
            doc_path, summary_path = Path(d, "verdict.json"), Path(d, "summary.md")
            try:
                doc = json.loads(doc_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                doc = None
            summary = summary_path.read_text(encoding="utf-8").strip() if summary_path.is_file() else ""
        if not isinstance(doc, dict):  # AsBuild's newest verdict is unreadable: never fall back to an older one
            return "UNRESOLVED", summary
        if doc.get("head_sha") not in (None, sha):
            continue
        return str(doc.get("verdict") or "UNRESOLVED"), summary
    return None


def main(
    argv: list[str] | None = None,
    run: Callable[..., str] = sh,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.time,
) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--interval", type=int, default=20)
    ap.add_argument("--sha", help="defaults to git rev-parse HEAD")
    a = ap.parse_args(argv)
    try:
        return wait(a, run, sleep, clock)
    except ToolError as e:
        print(f"could not ask GitHub for the verdict: {e}")
        return TOOL_FAILED


def wait(
    a: argparse.Namespace, run: Callable[..., str], sleep: Callable[[float], None], clock: Callable[[], float]
) -> int:
    repo = run("gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
    sha = a.sha or run("git", "rev-parse", "HEAD")
    print(f"waiting for the AsBuild verdict on {repo}@{sha[:10]} (up to {a.timeout}s)")
    deadline = clock() + a.timeout
    while clock() < deadline:
        found = saved_verdict(repo, sha, run)
        if found:
            v, summary = found
            print(f"verdict: {v}\n\n" + (summary or "(no summary)"))
            return EXIT.get(v, 3)
        sleep(a.interval)
    print(
        "timeout: no AsBuild verdict yet; look at the pull request's Checks tab. If this repository's AsBuild "
        "workflow files are older than v0.4.0, run /asbuild:setup to update them."
    )
    return 7


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
