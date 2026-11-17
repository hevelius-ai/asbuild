"""M2-C3: fails before for JavaScript checks (design §4.2 step 5, JS-7).

`c3_overlay.py` picks the runner by the file's extension. A JavaScript check file is laid over main in a worktree
inside the checkout (`.asbuild-c3/<slug>/`), so the pull request's `node_modules` is found, and run with AsBuild's
own Vitest settings; its result file keeps the `_<ext>.xml` ending that the verdict reads (M1's `langs.for_c3`).
Vitest itself runs in the live run (M2-C4); here a stand-in records what it was given.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from engine import c3_overlay, langs

STAND_IN = r"""
import json, os, pathlib, sys
xml = sys.argv[1]
pathlib.Path(xml).write_text('<testsuites><testsuite><testcase classname="x" name="y"/></testsuite></testsuites>')
seen = {"cwd": os.getcwd(), "app": pathlib.Path("app.ts").read_text(), "check": pathlib.Path(sys.argv[2]).read_text()}
pathlib.Path(xml + ".seen.json").write_text(json.dumps(seen))
"""


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def repo_with_checks(tmp_path):
    repo = tmp_path / "repo"
    (repo / "tests" / "acceptance" / "S1").mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "app.ts").write_text("export const v = 1\n")
    (repo / "app.py").write_text("VALUE = 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    (repo / "app.ts").write_text("export const v = 2\n")
    acc = repo / "tests" / "acceptance" / "S1"
    (acc / "S1-C1.test.tsx").write_text("test('S1-C1 shows 2', () => {})\n")
    (acc / "helpers.ts").write_text("export const h = 1\n")  # not a check file
    (acc / "test_S1_v.py").write_text("import app\n\n\ndef test_S1_C2_value():\n    assert app.VALUE == 2\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "head")
    return repo


def test_M2_C3_runner_is_chosen_by_extension():
    js = "tests/acceptance/S1/S1-C1.test.tsx"
    assert c3_overlay.command(js, "/o/a.xml", "/r") == [
        os.path.join("/r", "node_modules", ".bin", "vitest"),
        "run",
        js,
        "--config",
        c3_overlay.JS_SETTINGS,
        "--root",
        ".",
        "--reporter=junit",
        "--outputFile=/o/a.xml",
    ]
    assert Path(c3_overlay.JS_SETTINGS).is_file() and c3_overlay.JS_SETTINGS.endswith("vitest.acceptance.mjs")
    py = "tests/acceptance/S1/test_S1_v.py"
    assert c3_overlay.command(py, "/o/b.xml", "/r") == [
        sys.executable,
        "-m",
        "pytest",
        py,
        "--noconftest",
        "-p",
        "no:cacheprovider",
        "--continue-on-collection-errors",
        "-o",
        "junit_family=xunit2",
        "--junitxml=/o/b.xml",
    ]
    for name in ("a.test.ts", "a.test.js", "a.test.mjs", "a.test.cts", "a.test.jsx", "test_a.py", "a_test.py"):
        assert c3_overlay.is_check(f"tests/acceptance/S1/{name}"), name
    for name in ("helpers.ts", "a.spec.ts", "a.test.json", "conftest.py", "notes.txt"):
        assert not c3_overlay.is_check(f"tests/acceptance/S1/{name}"), name


def test_M2_C3_javascript_check_runs_over_main_inside_the_checkout(tmp_path, monkeypatch, capsys):
    repo = repo_with_checks(tmp_path)
    real = c3_overlay.command

    def stand_in(path, xml, root):
        if path.endswith(".py"):
            return real(path, xml, root)
        assert root == str(repo)
        return [sys.executable, "-c", STAND_IN, xml, path]

    monkeypatch.setattr(c3_overlay, "command", stand_in)
    out = tmp_path / "c3"
    assert c3_overlay.main(["--base", "main~1", "--out", str(out), "--repo", str(repo)]) == 0
    names = sorted(p.name for p in out.glob("*.xml"))
    assert names == ["tests_acceptance_s1_s1_c1_test_tsx.xml", "tests_acceptance_s1_test_s1_v_py.xml"]
    assert [langs.for_c3(n) for n in names] == [langs.JAVASCRIPT, langs.PYTHON]
    seen = json.loads((out / "tests_acceptance_s1_s1_c1_test_tsx.xml.seen.json").read_text())
    assert Path(seen["cwd"]) == repo / ".asbuild-c3" / "tests_acceptance_s1_s1_c1_test_tsx"
    assert seen["app"] == "export const v = 1\n"  # main's app
    assert seen["check"] == "test('S1-C1 shows 2', () => {})\n"  # the pull request's check
    assert not (repo / ".asbuild-c3").exists()  # the worktrees are gone afterwards
    assert "acceptance files: 2" in capsys.readouterr().out


def test_M2_C3_a_runner_that_cannot_start_leaves_no_result_and_the_rest_still_run(tmp_path, monkeypatch, capsys):
    repo = repo_with_checks(tmp_path)
    real = c3_overlay.command
    monkeypatch.setattr(
        c3_overlay,
        "command",
        lambda path, xml, root: real(path, xml, root) if path.endswith(".py") else [str(tmp_path / "no-such-tool")],
    )
    out = tmp_path / "c3"
    assert c3_overlay.main(["--base", "main~1", "--out", str(out), "--repo", str(repo)]) == 0
    assert sorted(p.name for p in out.glob("*.xml")) == ["tests_acceptance_s1_test_s1_v_py.xml"]
    assert "could not start" in capsys.readouterr().out
    assert not (repo / ".asbuild-c3").exists()
