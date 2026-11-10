"""Unit tests for the engine's smaller parts: classification, lock, lint, receipt, GitHub helpers, overlay."""

from __future__ import annotations

import json
import subprocess
import xml.etree.ElementTree as ET

import pytest

from engine import c3_overlay, common, junit_classify, lint_plain, lock_check, receipt


def tc(inner=""):
    return ET.fromstring(f'<testcase classname="c" name="n">{inner}</testcase>')


def test_classify_each_kind():
    assert junit_classify.classify(tc()) == ("passed", "")
    assert junit_classify.classify(tc('<skipped message="why" />'))[0] == "skipped"
    assert junit_classify.classify(tc('<error message="collection failure" />')) == (
        "existence-only",
        "error: collection failure",
    )
    assert junit_classify.classify(tc('<failure message="NameError: x" />'))[0] == "existence-only"
    assert junit_classify.classify(tc('<failure message="assert 1 == 2" />'))[0] == "strong"


def test_load_refuses_unreadable_results(tmp_path, monkeypatch):
    assert junit_classify.load(str(tmp_path / "none.xml")) is None
    bad = tmp_path / "bad.xml"
    bad.write_text("<testsuites>")
    assert junit_classify.load(str(bad)) is None
    empty = tmp_path / "empty.xml"
    empty.write_text("<testsuites><testsuite /></testsuites>")
    assert junit_classify.load(str(empty)) is None
    monkeypatch.setattr(junit_classify, "MAX_BYTES", 5)
    assert junit_classify.load(str(empty)) is None


def test_lock_normalises_and_parses():
    assert lock_check.normalised(b"a  \r\nb\r\r\n\n") == b"a\nb\n"
    assert lock_check.entry(b"def test_a():\n    pass\nasync def test_b(x):\n")["tests"] == ["test_a", "test_b"]
    assert lock_check.parse(None) == {}
    assert lock_check.parse(b"not json") == {}
    assert lock_check.parse(b"[1]") == {}
    assert lock_check.parse(b'{"files": [1]}') == {}
    assert lock_check.parse(b'{"files": {"a": {}}}') == {"a": {}}


def test_lock_baseline_command(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tests" / "acceptance" / "S1").mkdir(parents=True)
    (tmp_path / "tests" / "acceptance" / "S1" / "test_a.py").write_text("def test_S1_C1_a():\n    pass\n")
    assert lock_check.main(["baseline"]) == 0
    files = json.loads((tmp_path / "locks.json").read_text(encoding="utf-8"))["files"]
    assert list(files) == ["tests/acceptance/S1/test_a.py"]
    assert lock_check.main(["baseline", "--paths", "tests/acceptance/S1/test_a.py", "--out", "one.json"]) == 0
    assert lock_check.main(["baseline", "--paths", "nothing"]) == 2
    assert "no test files found" in capsys.readouterr().err


def test_lint_finds_each_error(tmp_path, capsys):
    errs = lint_plain.lint("r", "Merge it. See S1-C1 in app/x.py or a.toml, CODE_NAME. (a) (b). (a)")
    kinds = {e.split()[1] for e in errs}
    assert kinds == {"BANNED", "ID", "PATH", "CODE", "BRACKET_DUP", "BRACKET_2"}
    assert lint_plain.lint("r", "Open [the page](https://github.com/o/r/pull/1).") == []
    good, bad = tmp_path / "good.md", tmp_path / "bad.md"
    good.write_text("All fine here.\n<details>main test</details>", encoding="utf-8")
    bad.write_text("Merge it.", encoding="utf-8")
    assert lint_plain.main([str(good)]) == 0
    assert lint_plain.main([str(good), str(bad)]) == 1
    assert "1 lint error(s)" in capsys.readouterr().out


def verdict(v, codes, items=(), **kw):
    return dict(
        {
            "verdict": v,
            "codes": [{"code": c, "params": p} for c, p in codes],
            "items": list(items),
            "pr": 3,
            "head_sha": "f" * 40,
            "pr_url": "https://x/pull/3",
            "title": "",
            "story": "S1",
        },
        **kw,
    )


ITEM = {"id": "S1-C1", "plain": "The app counts words.", "status": "not_checked"}


@pytest.mark.parametrize(
    ("codes", "expect"),
    [
        ([("LOCK_TEST_MISSING", {"check": "S1-C1"})], "didn't run"),
        ([("LOCK_TEST_SKIPPED", {"path": "p", "test": "t"})], "didn't run"),
        ([("EXISTENCE_ONLY", {"check": "S1-C1"})], "a part of the app didn't exist"),
        ([("NO_STORY", {}), ("ACCEPTANCE_PASSES_ON_MAIN", {"check": "S1-C1"})], "already true before"),
        ([("PROTECTED_CHANGED", {"path": "notes/x"}), ("LOCK_TEST_MISSING", {"check": "S1-C1"})], "a file only you"),
        ([("NEW_CHECKS", {}), ("PROTECTED_CHANGED", {"path": "setup.py"})], "the settings for how your checks run"),
        ([("SOMETHING_NEW", {})], "Look at the details below"),
        (
            [
                ("PROTECTED_CHANGED", {"path": "x.pth"}),
                ("LOCK_TEST_MISSING", {"check": "S1-C1"}),
                ("ACCEPTANCE_PASSES_ON_MAIN", {"check": "S1-C1"}),
                ("EXISTENCE_ONLY", {"check": "S1-C1"}),
                ("NO_STORY", {}),
            ],
            "Agree a list of checks",
        ),
    ],
)
def test_waiting_receipts_lint_clean(codes, expect):
    r = receipt.render(verdict("WAITING FOR YOU", codes, [ITEM], run_url="https://run"))
    assert expect in r["top"]
    assert lint_plain.lint("x", r["top"]) == []
    assert "Verdict run: https://run" in r["technical"]


def test_unresolved_without_items_and_given_technical():
    r = receipt.render(verdict("UNRESOLVED", [("CRASH", {"error": "boom"})], technical="given"))
    assert r["template"] == 6 and r["technical"] == "given"
    assert "AsBuild runs on GitHub" in r["top"]


def test_gh_helpers(monkeypatch):
    calls = []

    def fake_run(cmd, **_kw):
        calls.append(cmd)
        out = {"repos/o/r/pulls/1": '{"n": 1}', "empty": "", "list": "[[1, 2], [3]]"}.get(cmd[2])
        if out is None:
            return subprocess.CompletedProcess(cmd, 1, "", "not found")
        return subprocess.CompletedProcess(cmd, 0, out, "")

    monkeypatch.setattr(common.subprocess, "run", fake_run)
    assert common.gh("repos/o/r/pulls/1") == {"n": 1}
    assert common.gh("empty") is None
    assert common.gh_paged("list") == [1, 2, 3]
    with pytest.raises(RuntimeError, match="not found"):
        common.gh("missing")
    assert calls[2] == ["gh", "api", "list", "--paginate", "--slurp"]


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_c3_overlay_runs_each_file_over_main(tmp_path, capsys):
    repo = tmp_path / "repo"
    (repo / "tests" / "acceptance" / "S1").mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "app.py").write_text("VALUE = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    (repo / "app.py").write_text("VALUE = 2\n")
    (repo / "tests" / "acceptance" / "S1" / "test_S1_v.py").write_text(
        "import app\n\n\ndef test_S1_C1_value():\n    assert app.VALUE == 2\n"
    )
    (repo / "tests" / "acceptance" / "S1" / "notes.txt").write_text("not a test\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "head")
    out = tmp_path / "c3"
    assert c3_overlay.main(["--base", "main~1", "--out", str(out), "--repo", str(repo)]) == 0
    results = junit_classify.load(str(out / "tests_acceptance_s1_test_s1_v_py.xml"))
    assert results == {("tests.acceptance.S1.test_S1_v", "test_S1_C1_value"): "strong"}
    assert "acceptance files: 1" in capsys.readouterr().out
