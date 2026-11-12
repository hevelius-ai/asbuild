"""A repository whose default branch is not `main` (walkthrough F2, plan S4-F2).

asbuild-test runs on pull requests into `main`; the verdict job looks for pull requests into the default branch.
When the two differ, the verdict job must say so (one AsBuild check, UNRESOLVED, naming the cause and the fix)
instead of ending green with nothing judged. The shell tests need bash and jq, so they run in CI's Linux check.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from engine.lint_plain import lint

ROOT = Path(__file__).resolve().parents[2]
VERDICT = ROOT / "workflows" / "asbuild-verdict.yml"
SHA = "a" * 40
REPO = "o/r"
needs_shell = pytest.mark.skipif(
    shutil.which("jq") is None or shutil.which("bash") is None, reason="needs bash and jq (CI's Linux check)"
)


def job():
    return yaml.safe_load(VERDICT.read_text(encoding="utf-8"))["jobs"]["verdict"]


def step(title):
    return next(s for s in job()["steps"] if s.get("name", "").startswith(title))


def uses(prefix):
    return next(s for s in job()["steps"] if str(s.get("uses", "")).startswith(prefix))


def pull(number, base, head_repo=REPO, sha=SHA, state="open"):
    return {
        "number": number,
        "base": {"ref": base},
        "head": {"repo": {"full_name": head_repo}, "sha": sha},
        "state": state,
    }


def fake_gh(tmp_path, pulls):
    """A `gh` that answers the pulls lookup and records what is posted."""
    gh = tmp_path / "bin" / "gh"  # its data sits apart from the step's own files in the working folder
    gh.parent.mkdir()
    data = gh.parent / "github_pulls.json"
    data.write_text(json.dumps(pulls), encoding="utf-8")
    gh.write_text(
        "#!/usr/bin/env bash\n"
        'case "$*" in\n'
        f'  *"/pulls"*) cat "{data.as_posix()}" ;;\n'
        f'  *"check-runs"*) cat > "{(tmp_path / "posted.json").as_posix()}" ;;\n'
        '  *"-X POST"*"/comments"*) for a in "$@"; do case "$a" in body=@*)'
        f' cp "${{a#body=@}}" "{(tmp_path / "posted_receipt.md").as_posix()}" ;; esac; done ;;\n'
        '  *"/comments"*) ;;\n'  # no earlier receipt to edit
        "esac\n",
        encoding="utf-8",
        newline="\n",
    )
    gh.chmod(0o755)
    return gh.parent


def run_step(tmp_path, title, pulls, main, outputs=None):
    bin_dir = fake_gh(tmp_path, pulls)
    out = tmp_path / "github_output"
    out.write_text("", encoding="utf-8")
    env = dict(os.environ)
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env['PATH']}",
        REPO=REPO,
        HEAD_SHA=SHA,
        MAIN=main,
        RUN_URL="https://example.invalid/run/1",
        GITHUB_OUTPUT=str(out),
    )
    s = step(title)
    script = s["run"]
    for name, value in s.get("env", {}).items():  # a step's own env, with the step outputs filled in
        for key, out_value in (outputs or {}).items():
            value = value.replace("${{ steps.pr.outputs." + key + " }}", out_value)
        env[name] = "" if "${{" in value else value
    for key, value in (outputs or {}).items():
        script = script.replace("${{ steps.pr.outputs." + key + " }}", value)
    p = subprocess.run(["bash", "-e", "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if "=" in ln]
    return dict(ln.split("=", 1) for ln in lines), p.stdout


@needs_shell
def test_lookup_default_branch_not_main_finds_the_pull_request_into_main(tmp_path):
    got, said = run_step(tmp_path, "Find the pull request", [pull(7, "main")], main="asbuild-setup")
    assert got == {"number": "7", "other_main": "asbuild-setup"}
    assert "asbuild-setup" in said


@needs_shell
def test_lookup_default_branch_main_is_unchanged(tmp_path):
    got, _ = run_step(tmp_path, "Find the pull request", [pull(7, "main")], main="main")
    assert got == {"number": "7"}


@needs_shell
@pytest.mark.parametrize(
    "pulls",
    [
        [],
        [pull(7, "develop")],
        [pull(7, "main", head_repo="fork/r")],
        [pull(7, "main", sha="b" * 40)],
        [pull(7, "main", state="closed")],
    ],
)
def test_lookup_judges_nothing_without_a_matching_pull_request(tmp_path, pulls):
    got, _ = run_step(tmp_path, "Find the pull request", pulls, main="asbuild-setup")
    assert got == {"skip": "true"}


def test_nothing_is_fetched_or_computed_when_the_default_branch_is_not_main():
    for s in (
        uses("actions/setup-python"),
        step("Fetch AsBuild"),
        uses("actions/download-artifact"),
        step("Compute the verdict"),
    ):
        assert "steps.pr.outputs.other_main == ''" in s["if"], s.get("name", s.get("uses"))


@needs_shell
def test_check_run_names_the_default_branch_and_the_fix(tmp_path):
    run_step(tmp_path, "Post the check run", [], main="asbuild-setup", outputs={"other_main": "asbuild-setup"})
    posted = json.loads((tmp_path / "posted.json").read_text(encoding="utf-8"))
    assert posted["name"] == "AsBuild" and posted["head_sha"] == SHA
    assert posted["conclusion"] == "failure"
    assert posted["output"]["title"] == "AsBuild: UNRESOLVED"
    summary = posted["output"]["summary"]
    assert "default branch is asbuild-setup" in summary
    assert "make main the default branch" in summary


@needs_shell
def test_check_run_is_unchanged_when_main_is_the_default_branch(tmp_path):
    run_step(tmp_path, "Post the check run", [], main="main", outputs={"number": "7", "other_main": ""})
    posted = json.loads((tmp_path / "posted.json").read_text(encoding="utf-8"))
    assert posted["output"]["title"] == "AsBuild: UNRESOLVED"
    assert posted["output"]["summary"] == (
        "AsBuild could not compute the verdict. Nothing is claimed. Verdict run: https://example.invalid/run/1\n"
    )


def receipt(tmp_path, main, other_main):
    (tmp_path / "out").mkdir()  # in the job, the check-run step always runs first and makes it
    run_step(tmp_path, "Post the receipt", [], main=main, outputs={"number": "7", "other_main": other_main})
    return (tmp_path / "posted_receipt.md").read_text(encoding="utf-8")


@needs_shell
def test_receipt_says_it_in_plain_words(tmp_path):
    text = receipt(tmp_path, "asbuild-setup", "asbuild-setup")
    top = text.splitlines()[1]
    assert top.startswith("Stop. Don't accept it. AsBuild checked nothing:")
    assert "open Settings on GitHub, then General" in top and "(Default branch: main)" in top
    assert lint("default-branch", top) == []
    assert "AsBuild: UNRESOLVED. Default branch: asbuild-setup, not main. Verdict run:" in text


@needs_shell
def test_receipt_is_unchanged_when_main_is_the_default_branch(tmp_path):
    assert receipt(tmp_path, "main", "") == (
        "<!-- asbuild-receipt -->\n"
        "Stop. Don't accept it. AsBuild couldn't finish its check, so nothing was checked.\n\n"
        "<details><summary>Technical report</summary>\n\n"
        "```\nAsBuild: UNRESOLVED. Verdict run: https://example.invalid/run/1\n```\n"
        "</details>\n"
    )


def test_readme_names_the_default_branch_and_a_git_identity():
    page = (ROOT / "README.md").read_text(encoding="utf-8")
    needs = page[page.index("### What your repository needs") : page.index("### 1. Install the plugin")]
    assert "`main` as its default branch" in needs
    assert "push `main` first" in needs
    assert "`git config`" in needs
    assert "`main` is not the default branch" in page
