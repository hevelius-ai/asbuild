"""Fails before: each acceptance test file at the head, laid over main unchanged, one file at a time.

Ported from step 0 (the G3 overlay in auditor.py, via c3_overlay.py). Runs in the untrusted job, with the
hardened settings. Writes one JUnit XML file per acceptance file into --out; the verdict classifies them. A test
that passes here shows nothing about the change.

The runner is chosen by the file's extension (v0.4.0, design §4.2 step 5). A Python file runs with pytest (no
conftest, no plugin autoload) in a worktree in a temporary folder, as before. A JavaScript check file runs with the
pull request's own Vitest and AsBuild's settings (`js/vitest.acceptance.mjs`, beside this file), in a worktree at
`.asbuild-c3/<slug>/` inside the checkout, so the pull request's `node_modules` is found (JS-7). Each result file is
named after the check file's path, so it keeps the `_<ext>.xml` ending the verdict reads.

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

PY_CHECK = re.compile(r"(^|/)(test_[^/]*\.py|[^/]*_test\.py)$")
JS_CHECK = re.compile(r"\.test\.[cm]?[jt]sx?$")  # what AsBuild's Vitest settings include
JS_SETTINGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "js", "vitest.acceptance.mjs")
JS_WORKTREES = ".asbuild-c3"


def sh(cmd: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def is_check(path: str) -> bool:
    return bool(PY_CHECK.search(path) or JS_CHECK.search(path))


def command(path: str, xml: str, repo: str) -> list[str]:
    """The run of one check file, from its worktree's root, writing its results to xml."""
    if JS_CHECK.search(path):
        vitest = os.path.join(repo, "node_modules", ".bin", "vitest")
        return [vitest, "run", path, "--config", JS_SETTINGS, "--root", ".", "--reporter=junit", f"--outputFile={xml}"]
    return [
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
        f"--junitxml={xml}",
    ]


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
    repo = os.path.abspath(a.repo)
    os.makedirs(out, exist_ok=True)
    head = sh(["git", "rev-parse", a.head], repo).stdout.strip()
    base = sh(["git", "merge-base", a.base, head], repo).stdout.strip() or a.base
    listed = sh(["git", "ls-tree", "-r", "--name-only", head, "--", a.paths], repo).stdout.split()
    files = [p for p in listed if is_check(p)]
    print(f"base {base[:10]}  head {head[:10]}  acceptance files: {len(files)}")
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    tmp = tempfile.mkdtemp(prefix="c3-")
    inside = os.path.join(repo, JS_WORKTREES)
    try:
        for path in files:
            slug = re.sub(r"[^a-z0-9]", "_", path.lower())
            one = os.path.join(inside if JS_CHECK.search(path) else tmp, slug)
            sh(["git", "worktree", "add", "--detach", one, base], repo)
            sh(["git", "checkout", head, "--", path], one)
            cmd = command(path, os.path.join(out, slug + ".xml"), repo)
            try:
                proc = subprocess.run(cmd, cwd=one, env=env, capture_output=True, text=True)
                print(f"== {path} over base: exit {proc.returncode}\n" + proc.stdout[-600:])
            except OSError as e:  # the runner is not installed (the install step failed): no result for this file
                print(f"== {path} over base: {cmd[0]} could not start: {e}")
            sh(["git", "worktree", "remove", "--force", one], repo)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(inside, ignore_errors=True)
        sh(["git", "worktree", "prune"], repo)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
