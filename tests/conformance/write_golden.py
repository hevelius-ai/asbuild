"""Writes the conformance suite's golden files (milestone M0, criterion M0-C5) from the engine on this branch.

Run once on M0, whose engine is v0.4.0's starting point (v0.3.4's), from the repository root:
`python tests/conformance/write_golden.py`. After that a golden file changes only with an owner decision recorded
in the pull request: the comparison tests in `test_conformance.py` exist so that no later change moves a Python
verdict, receipt or lock entry unseen.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from test_conformance import PYTHON, outcome  # noqa: E402

from engine.lock_check import entry  # noqa: E402


def main() -> None:
    out = HERE / "golden" / "python"
    out.mkdir(parents=True, exist_ok=True)
    for row in PYTHON:
        v, r = outcome(row["id"])
        text = json.dumps({"verdict": v, "receipt": r}, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        (out / f"{row['id']}.json").write_bytes(text.encode("utf-8"))
    locks = {
        p.relative_to(ROOT).as_posix(): entry(p.read_bytes())
        for p in sorted((ROOT / "tests" / "acceptance").rglob("*.py"))
    }
    (HERE / "golden" / "locks-py.json").write_bytes((json.dumps(locks, indent=2) + "\n").encode("utf-8"))
    print(f"golden files: {len(PYTHON)} Python rows, {len(locks)} lock entries")


if __name__ == "__main__":  # pragma: no cover
    main()
