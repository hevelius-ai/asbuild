"""Unit tests for plugin/scripts/asbuild_setup.py: the parts S5's acceptance rows do not reach (D39)."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugin" / "scripts"))
import asbuild_setup  # noqa: E402

URL = "https://github.com/someone/project.git"


def git(cwd: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return p.stdout


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A project with a first commit on main, on a local stand-in for GitHub, and a signed-in fake gh."""
    (tmp_path / "gitconfig").write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    if os.name == "nt":
        (bin_dir / "gh.cmd").write_text("@exit /b 0\r\n", encoding="utf-8")
    else:
        (bin_dir / "gh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (bin_dir / "gh").chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    hub = tmp_path / "project.git"
    git(tmp_path, "init", "--quiet", "--bare", "-b", "main", str(hub))
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "--quiet", "-b", "main")
    git(work, "config", "user.name", "Pat Example")
    git(work, "config", "user.email", "pat@example.com")
    git(work, "remote", "add", "origin", URL)
    git(work, "config", f"url.{hub.as_posix()}.insteadOf", URL)
    (work / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "--quiet", "-m", "first")
    git(work, "push", "--quiet", "origin", "main")
    return work, hub


def test_the_plugin_ships_the_published_workflow_files_byte_for_byte():
    for name in asbuild_setup.FILES:
        assert (ROOT / "plugin" / "workflows" / name).read_bytes() == (ROOT / "workflows" / name).read_bytes()


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (None, b"pytest\n"),
        (b"requests==2.32.3", b"requests==2.32.3\npytest\n"),
        (b"pytest-cov\n", b"pytest-cov\npytest\n"),
        (b"PyTest>=8\n", None),
        (b"# tools\npytest ; python_version >= '3.12'\n", None),
        (b"", b"pytest\n"),
        (b"requests\r\nflask\r\n", b"requests\r\nflask\r\npytest\r\n"),
        ("\ufeffrequests\n".encode("utf-8"), "\ufeffrequests\npytest\n".encode("utf-8")),
        (b"\xff\xfe" + "requests\r\n".encode("utf-16-le"), b"\xff\xfe" + "requests\r\npytest\r\n".encode("utf-16-le")),
        (b"\xfe\xff" + "pytest\n".encode("utf-16-be"), None),
    ],
)
def test_pytest_is_added_only_when_requirements_lack_it(given, expected):
    assert asbuild_setup.with_pytest(given) == expected


def test_requirements_that_cannot_be_read_stop_with_a_step():
    with pytest.raises(asbuild_setup.Stop, match="requirements.txt on main: .* upload it to main"):
        asbuild_setup.with_pytest(b"requests\xff\n")
    with pytest.raises(asbuild_setup.Stop, match="this folder's requirements.txt: .*pytest\\.$"):
        asbuild_setup.with_pytest(b"requests\xff\n", "folder")


def test_a_password_with_an_at_sign_is_never_echoed(repo, capsys):
    git(repo[0], "remote", "set-url", "origin", "https://pat:p@ss@gitlab.com/someone/project.git")
    assert asbuild_setup.main(["--repo", str(repo[0]), "--no-open"]) == 1
    out = capsys.readouterr().out
    assert "https://gitlab.com/someone/project.git" in out and "p@ss" not in out and "pat" not in out


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/someone/project.git",
        "https://someone@github.com/someone/project",
        "git@github.com:someone/project.git",
        "ssh://git@github.com/someone/project.git/",
        "ssh://git@github.com:22/someone/project",
        "http://www.github.com/someone/project.git",
    ],
)
def test_every_github_remote_form_names_the_owner_and_repository(url):
    found = asbuild_setup.GITHUB.match(url)
    assert found and found.group(1) == "someone" and found.group(2).removesuffix(".git") == "project"


def test_the_page_link_is_encoded():
    link = asbuild_setup.page("someone", "project", False, "Adds a & b.")
    assert link == (
        "https://github.com/someone/project/compare/main...asbuild-setup?quick_pull=1"
        "&title=Add%20AsBuild&body=Adds%20a%20%26%20b."
    )
    assert "&title=Update%20AsBuild&" in asbuild_setup.page("someone", "project", True, "x")


def test_git_missing(repo, capsys, monkeypatch):
    monkeypatch.setattr(asbuild_setup.shutil, "which", lambda name: None)
    assert asbuild_setup.main(["--repo", str(repo[0]), "--no-open"]) == 1
    out = capsys.readouterr().out
    assert "Git is not installed." in out and "winget install --id Git.Git" in out and "close and reopen" in out


def test_github_cannot_be_reached(repo, capsys, tmp_path):
    work, _ = repo
    git(work, "config", f"url.{(tmp_path / 'nowhere.git').as_posix()}.insteadOf", URL)
    git(work, "config", "--unset-all", f"url.{(tmp_path / 'project.git').as_posix()}.insteadOf")
    assert asbuild_setup.main(["--repo", str(work), "--no-open"]) == 1
    out = capsys.readouterr().out
    assert "Git could not reach the repository on GitHub. Check that you are online." in out
    assert "gh auth setup-git" in out


def failing(command: str):
    real = asbuild_setup.Repo.run

    def run(self, *args, **kwargs):
        if args[0] == command:
            return subprocess.CompletedProcess(args, 1, b"", b"it broke")
        return real(self, *args, **kwargs)

    return run


def test_fetch_fails(repo, capsys, monkeypatch):
    monkeypatch.setattr(asbuild_setup.Repo, "run", failing("fetch"))
    assert asbuild_setup.main(["--repo", str(repo[0]), "--no-open"]) == 1
    assert "Git said:\nit broke" in capsys.readouterr().out


def test_git_plumbing_fails(repo, capsys, monkeypatch):
    monkeypatch.setattr(asbuild_setup.Repo, "run", failing("hash-object"))
    assert asbuild_setup.main(["--repo", str(repo[0]), "--no-open"]) == 2
    assert "Setup could not run: git hash-object failed: it broke" in capsys.readouterr().out


def test_other_push_refusal_is_passed_on(repo, capsys):
    hook = repo[1] / "hooks" / "pre-receive"
    hook.write_bytes(b"#!/bin/sh\necho 'protected branch' >&2\nexit 1\n")
    hook.chmod(0o755)
    assert asbuild_setup.main(["--repo", str(repo[0]), "--no-open"]) == 1
    out = capsys.readouterr().out
    assert "GitHub refused the upload." in out and "gh auth setup-git" in out and "protected branch" in out


def test_the_page_opens_in_the_browser_after_the_link_is_printed(repo, monkeypatch):
    stream = io.StringIO()  # a stream without reconfigure
    opened = []

    def browser(link):
        opened.append((link, stream.getvalue()))
        return True

    monkeypatch.setattr(asbuild_setup.webbrowser, "open", browser)
    monkeypatch.setattr(sys, "stdout", stream)
    assert asbuild_setup.main(["--repo", str(repo[0])]) == 0
    link, printed_before = opened[0]
    assert link.startswith("https://github.com/someone/project/compare/main...asbuild-setup?")
    assert link in printed_before
    assert stream.getvalue().endswith("The page is open in your browser.\n")


def test_no_browser_says_to_open_the_link(repo, capsys, monkeypatch):
    monkeypatch.setattr(asbuild_setup.webbrowser, "open", lambda link: False)
    assert asbuild_setup.main(["--repo", str(repo[0])]) == 0
    assert capsys.readouterr().out.endswith("Open the link above in your browser.\n")


def test_the_empty_repository_message_is_kept_when_a_later_step_stops(tmp_path, capsys, monkeypatch, repo):
    work, hub = repo
    empty = tmp_path / "empty.git"
    git(tmp_path, "init", "--quiet", "--bare", "-b", "main", str(empty))
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    git(fresh, "init", "--quiet", "-b", "main")
    git(fresh, "config", "user.name", "Pat Example")
    git(fresh, "config", "user.email", "pat@example.com")
    git(fresh, "remote", "add", "origin", URL)
    git(fresh, "config", f"url.{empty.as_posix()}.insteadOf", URL)
    hook = empty / "hooks" / "pre-receive"
    hook.write_bytes(b'#!/bin/sh\nwhile read old new ref; do [ "$ref" = refs/heads/main ] || exit 1; done\n')
    hook.chmod(0o755)
    assert asbuild_setup.main(["--repo", str(fresh), "--no-open"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("This repository was empty, so setup made its first commit")
    assert "GitHub refused the upload." in out


def test_only_the_test_workflow_on_main_is_a_first_setup_with_no_verdict(repo, capsys):
    work, hub = repo
    (work / ".github" / "workflows").mkdir(parents=True)
    (work / ".github" / "workflows" / "asbuild-test.yml").write_bytes(
        asbuild_setup.wanted()[".github/workflows/asbuild-test.yml"]
    )
    git(work, "add", "-A")
    git(work, "commit", "--quiet", "-m", "half wired")
    git(work, "push", "--quiet", "origin", "main")
    assert asbuild_setup.main(["--repo", str(work), "--no-open"]) == 0
    out = capsys.readouterr().out
    assert "This pull request gets no verdict" in out and "WAITING FOR YOU" not in out
    assert "&title=Add%20AsBuild&" in out


def test_a_changed_setup_branch_is_replaced_by_one_on_main(repo, capsys):
    work, hub = repo
    assert asbuild_setup.main(["--repo", str(work), "--no-open"]) == 0
    first = git(hub, "rev-parse", "asbuild-setup").strip()
    old = asbuild_setup.wanted
    try:
        asbuild_setup.wanted = lambda: {k: v + b"# changed\n" for k, v in old().items()}
        assert asbuild_setup.main(["--repo", str(work), "--no-open"]) == 0
    finally:
        asbuild_setup.wanted = old
    assert git(hub, "rev-parse", "asbuild-setup^").strip() == git(hub, "rev-parse", "main").strip()
    assert git(hub, "rev-parse", "asbuild-setup").strip() != first
    assert git(hub, "show", "asbuild-setup:.github/workflows/asbuild-test.yml").endswith("# changed\n")
