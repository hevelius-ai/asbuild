"""M2-C1: the JavaScript steps of the test job (design §4.2; P-CI-1).

Gated by `hashFiles('tests/acceptance/**/*.test.*')`, placed after the Python steps and before the shared fails-before
step, each with `continue-on-error` and its own timeout, so a JavaScript failure never skips the Python evidence.
Tools start from `node_modules/.bin`, never through `npm run` or `npx`. A Python repository with no JavaScript checks
runs exactly v0.3.4's steps (done line 2): the fixture is v0.3.4's file, unchanged.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1].parent
GATE = "hashFiles('tests/acceptance/**/*.test.*') != ''"
PIN = re.compile(r'(rev-parse HEAD:engine\)" = ")[0-9a-f]{40}"')
COPIES = [ROOT / "workflows" / "asbuild-test.yml", ROOT / "plugin" / "workflows" / "asbuild-test.yml"]

needs_shell = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash (CI's Linux check)")


def doc(path: Path) -> dict:
    return yaml.safe_load(PIN.sub(r'\1<tree>"', path.read_text(encoding="utf-8")))


def steps(path: Path) -> list[dict]:
    return doc(path)["jobs"]["evidence"]["steps"]


def js_steps(path: Path) -> list[dict]:
    return [s for s in steps(path) if s.get("if") == GATE]


@pytest.mark.parametrize("path", COPIES, ids=["workflows", "plugin"])
def test_M2_C1_python_repository_runs_exactly_v034s_steps(path):
    now, before = doc(path), doc(ROOT / "tests" / "unit" / "fixtures" / "asbuild-test-v0.3.4.yml")
    now["jobs"]["evidence"]["steps"] = [s for s in steps(path) if s.get("if") != GATE]
    assert now == before


@pytest.mark.parametrize("path", COPIES, ids=["workflows", "plugin"])
def test_M2_C1_javascript_steps_are_gated_in_place_and_cannot_skip_python(path):
    names = [s.get("name") or s.get("uses", "") for s in steps(path)]
    js = js_steps(path)
    assert len(js) == 4
    first, last = steps(path).index(js[0]), steps(path).index(js[-1])
    assert names[first - 1].startswith("Acceptance tests, hardened (no conftest")  # after the Python steps
    assert names[last + 1].startswith("Fails before")  # before the shared fails-before step
    assert steps(path)[first : last + 1] == js  # together
    for s in js:
        assert s["continue-on-error"] is True, s
        assert isinstance(s["timeout-minutes"], int) and 1 <= s["timeout-minutes"] <= 10, s


@pytest.mark.parametrize("path", COPIES, ids=["workflows", "plugin"])
def test_M2_C1_each_javascript_step_does_exactly_its_part(path):
    node, install, full, hardened = js_steps(path)
    assert re.fullmatch(r"actions/setup-node@[0-9a-f]{40}", node["uses"])
    assert node["with"] == {"node-version": "24", "package-manager-cache": False}  # Node 24, no cache
    assert "npm ci --no-audit --no-fund --legacy-peer-deps" in install["run"]
    assert "out/js-install.txt" in install["run"]
    assert full["run"].strip() == "node_modules/.bin/vitest run --reporter=junit --outputFile=out/pr-js.xml"
    assert hardened["run"].strip() == (
        'node_modules/.bin/vitest run --config "$ASBUILD/engine/js/vitest.acceptance.mjs" --root . '
        "--reporter=junit --outputFile=out/acceptance-js.xml"
    )
    commands = "\n".join(s.get("run", "") for s in steps(path))
    for banned in ("npm run", "npx", "yarn", "pnpm", "bun ", "npm test", "npm exec"):
        assert banned not in commands, banned


def run_install(tmp_path, npm_lines, npm_exit):
    """The install step's script exactly as written, with a stand-in npm first on the PATH."""
    script = js_steps(COPIES[0])[1]["run"]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    npm = bin_dir / "npm"
    body = "".join(f"echo {shlex.quote(line)} >&2\n" for line in npm_lines)  # npm writes its errors to stderr
    npm.write_text(f'#!/bin/sh\necho "$@" > args.txt\n{body}exit {npm_exit}\n', newline="\n")
    npm.chmod(0o755)
    (tmp_path / "out").mkdir()
    env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}", RUNNER_TEMP=str(tmp_path))
    # GitHub runs a step with no `shell:` as `bash -e`; the bash on the PATH (on Windows, never System32's WSL one)
    bash = str(shutil.which("bash"))
    p = subprocess.run([bash, "-e", "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True)
    written = tmp_path / "out" / "js-install.txt"
    return p, (written.read_text() if written.exists() else None)


@needs_shell
@pytest.mark.parametrize("code", ["EBADPLATFORM", "ERESOLVE", "EUSAGE"])
def test_M2_C1_install_failure_writes_only_npms_known_code(tmp_path, code):
    p, written = run_install(tmp_path, ["npm warn x", f"npm error code {code}", "npm error more text"], 1)
    assert p.returncode != 0 and written == f"{code}\n"
    assert (tmp_path / "args.txt").read_text().split() == ["ci", "--no-audit", "--no-fund", "--legacy-peer-deps"]


@needs_shell
@pytest.mark.parametrize(
    "lines",
    [
        ["npm error code E404"],  # a code with no sentence of its own
        ["npm error code EBADPLATFORMX"],  # not exactly a known code
        ["npm error forged: npm error code EBADPLATFORM in the middle"],
        ["a package's own output: npm error code EBADPLATFORM"],  # the line must start with npm's own words
        ["no code at all"],
    ],
)
def test_M2_C1_any_other_install_failure_writes_other(tmp_path, lines):
    p, written = run_install(tmp_path, lines, 1)
    assert p.returncode != 0 and written == "OTHER\n"


@needs_shell
def test_M2_C1_install_success_writes_nothing(tmp_path):
    p, written = run_install(tmp_path, ["added 120 packages"], 0)
    assert p.returncode == 0 and written is None
    assert "added 120 packages" in p.stdout


def test_M2_C2_asbuild_ci_runs_the_settings_tests_at_full_coverage():
    """D51 (2A): one Node 24 step in AsBuild's own CI holds the settings file at 100% coverage."""
    ci = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    check = ci["jobs"]["check"]["steps"]
    node = next(s for s in check if str(s.get("uses", "")).startswith("actions/setup-node@"))
    assert re.fullmatch(r"actions/setup-node@[0-9a-f]{40}", node["uses"])
    assert node["with"] == {"node-version": "24", "package-manager-cache": False}
    run = next(s["run"] for s in check if "node --test" in s.get("run", "")).split()
    assert check.index(node) < next(i for i, s in enumerate(check) if "node --test" in s.get("run", ""))
    for flag in (
        "--experimental-test-coverage",
        '--test-coverage-include="engine/js/**"',
        "--test-coverage-lines=100",
        "--test-coverage-branches=100",
        "--test-coverage-functions=100",
        '"tests/js/*.test.mjs"',
    ):
        assert flag in run, flag


@pytest.mark.parametrize("path", COPIES, ids=["workflows", "plugin"])
def test_M2_C1_javascript_limits_leave_time_for_fails_before(path):
    """Round 1, Opus F1: the JavaScript steps together stop at least 3 of the job's 15 minutes before its end, so a
    JavaScript run that hangs cannot use up the time of the shared fails-before step and the upload."""
    job = doc(path)["jobs"]["evidence"]["timeout-minutes"]
    assert job == 15
    assert sum(s["timeout-minutes"] for s in js_steps(path)) <= job - 3
