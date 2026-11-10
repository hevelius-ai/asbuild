"""Fails before: each acceptance test file at the head, laid over main unchanged, one file at a time.

Ported from step 0 (the G3 overlay in auditor.py, via c3_overlay.py). Runs in the untrusted job, with the
hardened flags (no conftest, no plugin autoload). Writes one JUnit XML file per acceptance file into --out;
the verdict classifies them. A test that passes here shows nothing about the change.

Usage: c3_overlay.py --base origin/main [--head HEAD] [--paths tests/acceptance] --out out/c3
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

TEST_FILE = re.compile(r"(^|/)(test_[^/]*\.py|[^/]*_test\.py)$")


def sh(cmd: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="c3_overlay.py")
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--paths", default="tests/acceptance")
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo", default=".")
    return ap


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    head = sh(["git", "rev-parse", a.head], a.repo).stdout.strip()
    base = sh(["git", "merge-base", a.base, head], a.repo).stdout.strip() or a.base
    listed = sh(["git", "ls-tree", "-r", "--name-only", head, "--", a.paths], a.repo).stdout.split()
    files = [p for p in listed if TEST_FILE.search(p)]
    print(f"base {base[:10]}  head {head[:10]}  acceptance files: {len(files)}")
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    tmp = tempfile.mkdtemp(prefix="c3-")
    try:
        for path in files:
            slug = re.sub(r"[^a-z0-9]", "_", path.lower())
            one = os.path.join(tmp, slug)
            sh(["git", "worktree", "add", "--detach", one, base], a.repo)
            sh(["git", "checkout", head, "--", path], one)
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    path,
                    "--noconftest",
                    "-p",
                    "no:cacheprovider",
                    "--continue-on-collection-errors",
                    "-o",
                    "junit_family=xunit2",
                    f"--junitxml={os.path.join(out, slug + '.xml')}",
                ],
                cwd=one,
                env=env,
                capture_output=True,
                text=True,
            )
            print(f"== {path} over base: pytest exit {proc.returncode}\n" + proc.stdout[-600:])
            sh(["git", "worktree", "remove", "--force", one], a.repo)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
