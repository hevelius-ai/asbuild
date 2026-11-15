"""v0.4.0's conformance suite, level 1 (milestone M0; docs/plans/v0.4-M0.md, criteria M0-C2 to M0-C5).

Each judged row of `cases.json` is run through the real engine (`judge`, then `render`) with the facts and result
files stored in `cases/<id>/`, and compared with the row's expectation. Python rows must pass on today's engine.
JavaScript rows are v0.4.0's target: until their milestone they are expected to fail, strictly, so that the
milestone that makes one pass must remove its mark deliberately (it then fails as "unexpectedly passing").
Rows run in later milestones (live, setup) are listed in the table and counted here.

Golden files (M0-C5): every Python row's verdict and receipt as today's engine writes them, and the lock entries of
every `.py` acceptance file in this repository, compared byte for byte, so M1's refactor cannot move a Python result
unseen. A golden file changes only with an owner decision recorded in the pull request.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.lock_check import entry
from engine.receipt import render
from engine.verdict import Facts, judge

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TABLE = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
ROWS = TABLE["cases"]
GOLDEN = HERE / "golden"
JUDGED = [r for r in ROWS if r["level"] == "judge"]
PYTHON = [r for r in JUDGED if r["lang"] == "python"]
# The milestone whose engine this branch carries; rows due later are expected to fail until then.
CURRENT = "M0"
ORDER = ["M0", "M1", "M2", "M3", "M4"]


def tree(folder: Path) -> dict[str, bytes]:
    if not folder.is_dir():
        return {}
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def facts_for(cid: str) -> Facts:
    d = HERE / "cases" / cid
    case = json.loads((d / "case.json").read_text(encoding="utf-8"))
    ev = d / "evidence"
    return Facts(
        branch=case["branch"],
        pr_number=1,
        pr_url="https://github.com/example/app/pull/1",
        head_sha="c" * 40,
        files_changed=case["changed"],
        main_files=tree(d / "main"),
        head_files=tree(d / "head"),
        evidence=str(ev) if ev.is_dir() else str(d / "no-evidence"),
    )


def outcome(cid: str) -> tuple[dict, dict]:
    v = judge(facts_for(cid))
    return v, render(v)


def check(row: dict, v: dict, r: dict) -> list[str]:
    exp = row["expect"]
    got_codes = [c["code"] for c in v["codes"]]
    wrong = []
    if v["verdict"] != exp["verdict"]:
        wrong.append(f"verdict {v['verdict']!r}, expected {exp['verdict']!r}")
    wrong += [f"missing code {c}" for c in exp.get("codes", []) if c not in got_codes]
    wrong += [f"unexpected code {c}" for c in exp.get("no_codes", []) if c in got_codes]
    statuses = {i["id"]: i["status"] for i in v.get("items", [])}
    wrong += [
        f"{k} is {statuses.get(k)!r}, expected {s!r}"
        for k, s in exp.get("statuses", {}).items()
        if statuses.get(k) != s
    ]
    wrong += [f"receipt lacks {t!r}" for t in exp.get("receipt_has", []) if t not in r.get("top", "")]
    return wrong


def due(row: dict) -> bool:
    return ORDER.index(row["milestone"]) <= ORDER.index(CURRENT)


@pytest.mark.parametrize("row", JUDGED, ids=[r["id"] for r in JUDGED])
def test_conformance_row(row, request):
    if not due(row):
        request.applymarker(pytest.mark.xfail(strict=True, reason=f"v0.4.0 target, due in {row['milestone']}"))
    v, r = outcome(row["id"])
    assert check(row, v, r) == []


def test_every_judged_row_has_its_case_folder_and_every_folder_a_row():
    folders = {p.name for p in (HERE / "cases").iterdir() if p.is_dir()}
    assert folders == {r["id"] for r in JUDGED}


def test_rows_due_later_are_named_and_cite_the_design():
    for r in ROWS:
        assert r["cites"], r["id"]
        assert r["milestone"] in ORDER, r["id"]
    later = sorted(r["id"] for r in ROWS if r["level"] != "judge")
    assert later and all(r["milestone"] in ("M2", "M3") for r in ROWS if r["level"] != "judge")


@pytest.mark.parametrize("row", PYTHON, ids=[r["id"] for r in PYTHON])
def test_python_golden_verdict_and_receipt(row):
    v, r = outcome(row["id"])
    got = json.dumps({"verdict": v, "receipt": r}, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert got == (GOLDEN / "python" / f"{row['id']}.json").read_text(encoding="utf-8")


def test_python_golden_lock_entries():
    got = {
        p.relative_to(ROOT).as_posix(): entry(p.read_bytes())
        for p in sorted((ROOT / "tests" / "acceptance").rglob("*.py"))
    }
    want = json.loads((GOLDEN / "locks-py.json").read_text(encoding="utf-8"))
    assert got == want
