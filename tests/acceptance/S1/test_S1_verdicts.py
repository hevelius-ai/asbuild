"""S1 acceptance tests: the CI check, the verdict and the receipts (docs/plans/S1.md).

One test per check, named after it. Self-contained: no conftest, no shared fixtures. Each test builds the
evidence the untrusted job would upload (JUnit XML) and the facts the trusted job reads (the PR's branch and
file list, main's files, the head's files), then calls the engine as the verdict workflow does.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from engine import verdict as verdict_mod
from engine.lint_plain import lint
from engine.lock_check import entry
from engine.receipt import render
from engine.verdict import Facts, judge

ROOT = Path(__file__).resolve().parents[3]
PR_URL = "https://github.com/hevelius-ai/asbuild-demo/pull/7"
ACC_PATH = "tests/acceptance/S1/test_S1_count.py"
ACC_CLS = "tests.acceptance.S1.test_S1_count"
ACC = b"def test_S1_C1_counts_words():\n    assert False\n\n\ndef test_S1_C2_missing_file():\n    assert False\n"
A1 = (ACC_CLS, "test_S1_C1_counts_words")
A2 = (ACC_CLS, "test_S1_C2_missing_file")
UNIT = ("tests.unit.test_app", "test_unit_ok")
PLAIN_1 = 'When you name a text file, the app shows how many words it has, like "words: 3".'
PLAIN_2 = "If the file you name doesn't exist, the app tells you so."
STORY = f"""# S1: Count words

## Criteria

| ID | Criterion | Cites |
| --- | --- | --- |
| S1-C1 | `python -m app count <file>` prints `words: <n>` and exits 0 | R1 |
| S1-C2 | For a file that does not exist it exits 2 and stderr says "no such file" | R1 |

## Plain checklist

| ID | plain: |
| --- | --- |
| S1-C1 | {PLAIN_1} |
| S1-C2 | {PLAIN_2} |
"""

FAILURES = {
    "assert": '<failure message="AssertionError: assert 1 == 0">trace</failure>',
    "import": '<failure message="ModuleNotFoundError: No module named \'app.count\'">trace</failure>',
    "skip": '<skipped type="pytest.skip" message="skipped" />',
    "error": '<error message="collection failure">trace</error>',
    "pass": "",
}


def junit(cases):
    body = "".join(
        f'<testcase classname="{c}" name="{n}" time="0.01">{FAILURES[k]}</testcase>' for c, n, k in cases
    )
    return f'<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest">{body}</testsuite></testsuites>'


def locks(files):
    return json.dumps({"files": {p: entry(raw) for p, raw in files.items()}}).encode()


def facts(tmp_path, *, branch="build/S1", changed=None, pr=None, acc=None, c3=None, head_extra=None,
          head_acc=ACC, evidence=True):
    """A build PR for story S1 that makes both checks pass and breaks nothing, unless told otherwise."""
    ev = tmp_path / "evidence"
    ev.mkdir()
    if evidence:
        (ev / "pr.xml").write_text(junit(pr or [(*UNIT, "pass"), (*A1, "pass"), (*A2, "pass")]))
        (ev / "acceptance.xml").write_text(junit(acc or [(*A1, "pass"), (*A2, "pass")]))
        (ev / "c3").mkdir()
        (ev / "c3" / "tests_acceptance_s1_test_s1_count_py.xml").write_text(
            junit(c3 or [(*A1, "assert"), (*A2, "assert")]))
    main_files = {"locks.json": locks({ACC_PATH: ACC}), "dev-docs/stories/S1/story.md": STORY.encode(),
                  ACC_PATH: ACC}
    head_files = {"locks.json": locks({ACC_PATH: ACC}), "dev-docs/stories/S1/story.md": STORY.encode(),
                  ACC_PATH: head_acc}
    head_files.update(head_extra or {})
    return Facts(branch=branch, pr_number=7, pr_url=PR_URL, head_sha="a" * 40,
                 files_changed=changed or ["app/count.py", "tests/unit/test_app.py"],
                 main_files=main_files, head_files=head_files, evidence=str(ev))


def codes(v):
    return [c["code"] for c in v["codes"]]


def test_S1_C1_proven_one_check_one_receipt(tmp_path):
    v = judge(facts(tmp_path))
    r = render(v)
    assert v["verdict"] == "PROVEN"
    assert r["template"] == 1
    assert PLAIN_1 in r["top"] and PLAIN_2 in r["top"]
    assert PR_URL in r["top"]
    steps = [s.get("run", "") for job in _wf("asbuild-verdict.yml")["jobs"].values() for s in job["steps"]]
    assert sum("check-runs" in s and "POST" in s for s in steps) == 1
    assert sum("receipt.md" in s for s in steps) == 1


def test_S1_C2_not_proven_names_unmet_check(tmp_path):
    v = judge(facts(tmp_path, pr=[(*UNIT, "pass"), (*A1, "pass"), (*A2, "assert")],
                    acc=[(*A1, "pass"), (*A2, "assert")]))
    r = render(v)
    assert v["verdict"] == "NOT PROVEN"
    assert r["template"] == 4
    unmet = [ln for ln in r["top"].splitlines() if "✗" in ln]
    assert len(unmet) == 1 and PLAIN_2 in unmet[0]


@pytest.mark.parametrize("case", ["locked_test", "protected_file"])
def test_S1_C3_waiting_names_changed_file(tmp_path, case):
    if case == "locked_test":
        f = facts(tmp_path, head_acc=ACC.replace(b"assert False", b"assert True"),
                  changed=["app/count.py", ACC_PATH])
        path, plain = ACC_PATH, "one of your agreed checks"
    else:
        f = facts(tmp_path, changed=["app/count.py", "pyproject.toml"])
        path, plain = "pyproject.toml", "the project's settings file"
    v = judge(f)
    r = render(v)
    assert v["verdict"] == "WAITING FOR YOU"
    assert r["template"] == 2
    assert path in r["technical"]
    assert plain in r["top"]


def test_S1_C4_unresolved_claims_nothing(tmp_path):
    v = judge(facts(tmp_path, evidence=False))
    r = render(v)
    assert v["verdict"] == "UNRESOLVED"
    assert r["template"] == 6
    assert {i["status"] for i in v["items"]} == {"not_checked"}
    assert "✓" not in r["top"] and "works" not in r["top"]

    def broken_fetch(_args):
        raise RuntimeError("API down")

    out = tmp_path / "out"
    verdict_mod.run(["--evidence", str(tmp_path / "none"), "--head", "b" * 40, "--pr", "7",
                     "--out", str(out / "verdict.json"), "--summary", str(out / "summary.md"),
                     "--receipt", str(out / "receipt.md")], fetch=broken_fetch)
    assert json.loads((out / "verdict.json").read_text(encoding="utf-8"))["verdict"] == "UNRESOLVED"
    assert "✓" not in (out / "receipt.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("branch", ["docs/readme", "build/S7"])
def test_S1_C5_no_story_never_proven(tmp_path, branch):
    v = judge(facts(tmp_path, branch=branch))
    r = render(v)
    assert v["verdict"] == "WAITING FOR YOU"
    assert "NO_STORY" in codes(v)
    assert r["template"] == 3
    assert "no agreed check covers this change" in r["top"].lower()


def _wf(name):
    return yaml.safe_load((ROOT / "workflows" / name).read_text(encoding="utf-8"))


def _on(wf):
    return wf.get("on", wf.get(True))


def test_S1_C6_verdict_job_runs_from_main_only():
    texts = {n: (ROOT / "workflows" / n).read_text(encoding="utf-8") for n in ("asbuild-test.yml", "asbuild-verdict.yml")}
    assert all("pull_request_target" not in t for t in texts.values())
    assert set(_on(_wf("asbuild-test.yml"))) == {"pull_request"}
    v = _wf("asbuild-verdict.yml")
    assert set(_on(v)) == {"workflow_run"}
    assert _on(v)["workflow_run"]["workflows"] == ["asbuild-test"]
    text = texts["asbuild-verdict.yml"]
    assert "pytest" not in text
    for job in v["jobs"].values():
        for step in job["steps"]:
            if str(step.get("uses", "")).startswith("actions/checkout"):
                w = step.get("with", {})
                assert (w.get("repository") == "hevelius-ai/asbuild" and w.get("ref") == "main") or (
                    "repository" not in w and w.get("ref") == "${{ github.event.repository.default_branch }}")
            for target in re.findall(r"\bpython3?\s+(\S+)", step.get("run", "")):
                assert target.startswith('"$ASBUILD/engine/') or target.startswith("$ASBUILD/engine/") or (
                    target == "-m"), target
    assert "hevelius-ai/asbuild" in text


def test_S1_C7_story_pr_lists_new_checks(tmp_path):
    s2_path = "tests/acceptance/S2/test_S2_greet.py"
    s2 = b"def test_S2_C1_greets():\n    assert False\n\n\ndef test_S2_C2_usage():\n    assert False\n"
    s2_plain = ['When you type a name, the app greets that person, like "Hello, Ana!".',
                "If you leave out the name, the app explains how to use it."]
    s2_story = STORY.replace("S1", "S2").replace(PLAIN_1, s2_plain[0]).replace(PLAIN_2, s2_plain[1])
    s2_cls = "tests.acceptance.S2.test_S2_greet"
    f = facts(tmp_path, branch="story/S2",
              changed=["locks.json", s2_path, "dev-docs/stories/S2/story.md"],
              pr=[(*UNIT, "pass"), (*A1, "pass"), (*A2, "pass"), (s2_cls, "test_S2_C1_greets", "assert"),
                  (s2_cls, "test_S2_C2_usage", "assert")],
              acc=[(*A1, "pass"), (*A2, "pass"), (s2_cls, "test_S2_C1_greets", "assert"),
                   (s2_cls, "test_S2_C2_usage", "assert")],
              c3=[(*A1, "pass"), (*A2, "pass"), (s2_cls, "test_S2_C1_greets", "assert"),
                  (s2_cls, "test_S2_C2_usage", "assert")],
              head_extra={"locks.json": locks({ACC_PATH: ACC, s2_path: s2}), s2_path: s2,
                          "dev-docs/stories/S2/story.md": s2_story.encode()})
    v = judge(f)
    r = render(v)
    assert v["verdict"] == "WAITING FOR YOU"
    assert codes(v) == ["NEW_CHECKS"]
    assert r["template"] == 2
    assert all(p in r["top"] for p in s2_plain)
    assert "only you are allowed to change" not in r["top"]


def test_S1_C8_six_templates_lint_clean(tmp_path):
    scenarios = {
        1: {},
        2: {"changed": ["app/count.py", "pyproject.toml"]},
        3: {"c3": [(*A1, "pass"), (*A2, "assert")]},
        4: {"pr": [(*UNIT, "pass"), (*A1, "assert"), (*A2, "pass")], "acc": [(*A1, "assert"), (*A2, "pass")]},
        5: {"pr": [(*UNIT, "assert"), (*A1, "pass"), (*A2, "pass")]},
        6: {"evidence": False},
    }
    for n, kw in scenarios.items():
        d = tmp_path / str(n)
        d.mkdir()
        r = render(judge(facts(d, **kw)))
        assert r["template"] == n, (n, r["template"])
        assert lint(str(n), r["top"]) == [], (n, r["top"])
        assert PLAIN_1 in r["top"] and PLAIN_2 in r["top"]
