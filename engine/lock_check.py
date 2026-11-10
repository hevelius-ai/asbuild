"""The test lock (ported from step 0's T21): a hash of each locked test file's normalised content.

Normalised: CRLF and CR become LF, trailing spaces and tabs are stripped, exactly one trailing newline.
Each entry also lists the test functions found in the file (`def test_*`).

`python lock_check.py baseline --paths tests/acceptance --out locks.json` writes the lock file a story
pull request adds. The verdict compares main's lock file with the pull request's files (engine/verdict.py).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

TEST_DEF = re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)\s*\(", re.M)


def normalised(data: bytes) -> bytes:
    text = data.decode("utf-8", errors="surrogateescape")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip(" \t") for ln in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return ("\n".join(lines) + "\n").encode("utf-8", errors="surrogateescape")


def entry(raw: bytes) -> dict:
    return {
        "sha256": hashlib.sha256(normalised(raw)).hexdigest(),
        "tests": TEST_DEF.findall(raw.decode("utf-8", errors="replace")),
    }


def parse(raw: bytes | None) -> dict[str, dict]:
    """The `files` map of a lock file; {} when it is missing or unreadable."""
    if raw is None:
        return {}
    try:
        files = json.loads(raw.decode("utf-8")).get("files", {})
    except (ValueError, AttributeError, UnicodeDecodeError):
        return {}
    return files if isinstance(files, dict) else {}


def baseline(paths: list[Path], root: Path) -> dict:
    files = {}
    for base in paths:
        for p in sorted(base.rglob("*.py")) if base.is_dir() else [base] if base.is_file() else []:
            files[p.relative_to(root).as_posix()] = entry(p.read_bytes())
    return {"files": files}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write the lock file for the acceptance tests.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("baseline")
    b.add_argument("--paths", nargs="+", type=Path, default=[Path("tests/acceptance")])
    b.add_argument("--out", type=Path, default=Path("locks.json"))
    b.add_argument("--root", type=Path, default=Path("."))
    a = ap.parse_args(argv)
    doc = baseline(a.paths, a.root)
    if not doc["files"]:
        print("no test files found under " + ", ".join(p.as_posix() for p in a.paths), file=sys.stderr)
        return 2
    a.out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"{len(doc['files'])} file(s) locked -> {a.out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
