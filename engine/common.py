"""GitHub API helpers for the trusted side (standard library only; uses the `gh` command)."""

from __future__ import annotations

import json
import subprocess
from typing import Any


def gh(path: str, *args: str) -> Any:
    """`gh api <path> [args]`, parsed as JSON (None for an empty body). Raises on a failed call."""
    proc = subprocess.run(["gh", "api", path, *args], capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"gh api {path} failed: {proc.stderr.strip()[:300]}")
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def gh_paged(path: str) -> list:
    """Every item of a list endpoint, all pages."""
    pages = gh(path, "--paginate", "--slurp") or []
    return [item for page in pages for item in page]
