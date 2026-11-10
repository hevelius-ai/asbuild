#!/usr/bin/env python3
"""Wait for the AsBuild verdict on the current commit and print it (ported from step 0; decision D19).

`gh pr checks --watch` returns when the test workflow finishes, a few seconds before the verdict workflow
posts the AsBuild check run. This script waits for that check run itself.

Usage (from the repository root, after `git push`): python asbuild_wait.py [--timeout 1200] [--sha SHA]

Prints the check run's summary and exits:
  0 PROVEN   1 NOT PROVEN   3 UNRESOLVED   4 WAITING FOR YOU
  5 could not ask GitHub (gh or git failed: not logged in, no network)   7 timeout (no verdict yet)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable

EXIT = {"PROVEN": 0, "NOT PROVEN": 1, "UNRESOLVED": 3, "WAITING FOR YOU": 4}
TOOL_FAILED = 5


class ToolError(Exception):
    """gh or git failed, so there is no verdict to report."""


def sh(*cmd: str) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        raise ToolError(f"{' '.join(cmd)} failed: {p.stderr.strip()}")
    return p.stdout.strip()


def verdict_of(run: dict) -> str:
    title = (run.get("output") or {}).get("title") or ""
    return title.removeprefix("AsBuild: ").strip() if title.startswith("AsBuild: ") else "UNRESOLVED"


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
    print(f"waiting for the AsBuild check on {repo}@{sha[:10]} (up to {a.timeout}s)")
    deadline = clock() + a.timeout
    while clock() < deadline:
        data = json.loads(run("gh", "api", f"repos/{repo}/commits/{sha}/check-runs?check_name=AsBuild&per_page=100"))
        done = [
            r
            for r in data.get("check_runs", [])
            if r.get("name") == "AsBuild"
            and (r.get("app") or {}).get("slug") == "github-actions"
            and r.get("status") == "completed"
        ]
        if done:
            last = sorted(done, key=lambda r: r.get("completed_at") or "")[-1]
            v = verdict_of(last)
            print(f"verdict: {v}\n\n" + ((last.get("output") or {}).get("summary") or "(no summary)"))
            return EXIT.get(v, 3)
        sleep(a.interval)
    print("timeout: no AsBuild verdict yet; look at the pull request's Checks tab")
    return 7


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
