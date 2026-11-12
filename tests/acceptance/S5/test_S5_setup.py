"""Story S5: /asbuild:setup wires a repository with one command (D39, docs/plans/S5.md).

Each test runs the setup script as the skill does, against real Git. A local bare repository stands in for GitHub
through Git's `url.<path>.insteadOf`, so the remote is a real github.com URL and nothing reaches the network. A fake
`gh` on PATH answers `gh auth status`. Each test checks what the person sees (the message and the exit) and what
reached the stand-in for GitHub, and that the person's own folder is left as it was.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "plugin" / "scripts" / "asbuild_setup.py"
URL = "https://github.com/someone/project.git"
LINK = "https://github.com/someone/project/compare/main...asbuild-setup?quick_pull=1&title=Add%20AsBuild&body="
AGAIN = "Then run /asbuild:setup again."
FILES = (".github/workflows/asbuild-test.yml", ".github/workflows/asbuild-verdict.yml")


def plugin_copy(name: str) -> bytes:
    return (ROOT / "plugin" / "workflows" / name).read_bytes().replace(b"\r\n", b"\n")


def load():
    spec = importlib.util.spec_from_file_location("asbuild_setup", SCRIPT)
    assert spec and spec.loader, "plugin/scripts/asbuild_setup.py is missing"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(cwd: Path, *args: str, check: bool = True) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check:
        assert p.returncode == 0, p.stderr
    return p.stdout


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A person's project folder (its path holds a space), linked to an empty stand-in for GitHub."""
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(home / ".gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    if os.name == "nt":
        (bin_dir / "gh.cmd").write_text("@exit /b %FAKE_GH_EXIT%\r\n", encoding="utf-8")
    else:
        fake = bin_dir / "gh"
        fake.write_text('#!/bin/sh\nexit "$FAKE_GH_EXIT"\n', encoding="utf-8")
        fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("FAKE_GH_EXIT", "0")
    hub = tmp_path / "github" / "project.git"
    hub.parent.mkdir()
    git(tmp_path, "init", "--quiet", "--bare", "-b", "main", str(hub))
    work = tmp_path / "my project"
    work.mkdir()
    git(work, "init", "--quiet", "-b", "main")
    git(work, "config", "user.name", "Pat Example")
    git(work, "config", "user.email", "pat@example.com")
    git(work, "remote", "add", "origin", URL)
    git(work, "config", f"url.{hub.as_posix()}.insteadOf", URL)
    return work, hub


def seed(work: Path, hub: Path, files: dict[str, bytes]) -> None:
    """The person's repository already has a first commit on main, on GitHub too."""
    for name, data in files.items():
        (work / name).parent.mkdir(parents=True, exist_ok=True)
        (work / name).write_bytes(data)
    git(work, "add", "-A")
    git(work, "commit", "--quiet", "-m", "first")
    git(work, "push", "--quiet", "origin", "main")


def snapshot(work: Path) -> tuple:
    files = {
        p.relative_to(work).as_posix(): p.read_bytes()
        for p in work.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(work).parts
    }
    return git(work, "status", "--porcelain=v1", "-uall"), git(work, "branch", "--show-current"), files


def hub_file(hub: Path, ref: str, name: str) -> bytes | None:
    p = subprocess.run(["git", "show", f"{ref}:{name}"], cwd=hub, capture_output=True)
    return p.stdout if p.returncode == 0 else None


def hub_branches(hub: Path) -> set[str]:
    return set(git(hub, "for-each-ref", "--format=%(refname:short)", "refs/heads").split())


def setup(work: Path, capsys, *extra: str) -> tuple[int, str]:
    code = load().main(["--repo", str(work), "--no-open", *extra])
    return code, capsys.readouterr().out


def test_S5_C1_not_a_repository_no_origin_not_github(world, tmp_path, capsys):
    work, hub = world
    plain = tmp_path / "plain folder"
    plain.mkdir()
    code, out = setup(plain, capsys)
    assert code == 1
    assert "This folder is not a Git repository." in out and AGAIN in out
    git(work, "remote", "remove", "origin")
    code, out = setup(work, capsys)
    assert code == 1
    assert "This repository has no link to GitHub (no remote named origin)." in out
    assert "git remote add origin https://github.com/<owner>/<repository>.git" in out and AGAIN in out
    git(work, "remote", "add", "origin", "https://gitlab.com/someone/project.git")
    code, out = setup(work, capsys)
    assert code == 1
    assert "This repository's origin is not on github.com: https://gitlab.com/someone/project.git" in out
    assert hub_branches(hub) == set()


def test_S5_C2_git_has_no_name_or_email(world, capsys):
    work, hub = world
    git(work, "config", "--unset", "user.email")
    before = snapshot(work)
    code, out = setup(work, capsys)
    assert code == 1
    assert "Git has no name or email for its commits yet." in out
    assert 'git config --global user.name "Your Name"' in out
    assert "git config --global user.email you@example.com" in out and AGAIN in out
    assert snapshot(work) == before and hub_branches(hub) == set()


def test_S5_C3_github_cli_missing_or_not_signed_in(world, capsys, monkeypatch):
    work, hub = world
    monkeypatch.setenv("FAKE_GH_EXIT", "1")
    code, out = setup(work, capsys)
    assert code == 1
    assert "You are not signed in to GitHub." in out
    assert "gh auth login" in out and "GitHub.com, HTTPS" in out and AGAIN in out
    module = load()
    real_which = module.shutil.which
    monkeypatch.setattr(module.shutil, "which", lambda name, *a, **k: None if name == "gh" else real_which(name))
    code = module.main(["--repo", str(work), "--no-open"])
    out = capsys.readouterr().out
    assert code == 1
    assert "The GitHub CLI (gh) is not installed." in out and "https://cli.github.com" in out and AGAIN in out
    assert hub_branches(hub) == set()


def test_S5_C4_empty_repository_gets_its_first_commit_on_main(world, capsys):
    work, hub = world
    (work / "app.py").write_text("print('hello')\n", encoding="utf-8")  # the person's work, not committed
    before = snapshot(work)
    code, out = setup(work, capsys)
    assert code == 0, out
    assert "This repository was empty, so setup made its first commit, a requirements.txt that lists pytest" in out
    assert hub_branches(hub) == {"main", "asbuild-setup"}
    assert git(hub, "ls-tree", "-r", "--name-only", "main").split() == ["requirements.txt"]
    assert hub_file(hub, "main", "requirements.txt") == b"pytest\n"
    for name in FILES:
        assert hub_file(hub, "asbuild-setup", name) == plugin_copy(Path(name).name)
    assert git(hub, "rev-parse", "asbuild-setup^") == git(hub, "rev-parse", "main")
    assert LINK in out
    assert snapshot(work) == before


def test_S5_C5_default_branch_not_main_stops(world, capsys):
    work, hub = world
    seed(work, hub, {"app.py": b"x = 1\n", "requirements.txt": b"pytest\n"})
    git(work, "push", "--quiet", "origin", "main:other")
    git(hub, "symbolic-ref", "HEAD", "refs/heads/other")
    code, out = setup(work, capsys)
    assert code == 1
    assert "GitHub's default branch for this repository is other, not main." in out
    assert "Settings, then General, and set Default branch to main" in out and AGAIN in out
    assert hub_branches(hub) == {"main", "other"}


def test_S5_C6_first_setup_pushes_the_two_files_and_names_the_page(world, capsys):
    work, hub = world
    seed(work, hub, {"app.py": b"x = 1\n", "requirements.txt": b"requests==2.32.3\n"})
    git(work, "switch", "--quiet", "-c", "my-work")
    (work / "app.py").write_text("x = 2\n", encoding="utf-8")  # unsaved work
    (work / "notes.txt").write_text("draft\n", encoding="utf-8")
    git(work, "add", "notes.txt")  # staged work
    before = snapshot(work)
    code, out = setup(work, capsys)
    assert code == 0, out
    for name in FILES:
        assert hub_file(hub, "asbuild-setup", name) == plugin_copy(Path(name).name)
    assert hub_file(hub, "asbuild-setup", "requirements.txt") == b"requests==2.32.3\npytest\n"
    assert hub_file(hub, "asbuild-setup", "app.py") == b"x = 1\n"
    assert git(hub, "rev-parse", "asbuild-setup^") == git(hub, "rev-parse", "main")
    assert "Setup prepared AsBuild's two workflow files on the branch asbuild-setup." in out
    assert "Create the pull request on the page that opened, then merge it" in out
    assert LINK in out
    assert "It also adds pytest to requirements.txt" in out
    assert "This pull request gets no verdict" in out
    assert "WAITING FOR YOU" not in out
    assert snapshot(work) == before


def test_S5_C7_already_set_up_pushes_nothing(world, capsys):
    work, hub = world
    seed(
        work,
        hub,
        {
            "requirements.txt": b"pytest==8.4.2\n",
            FILES[0]: plugin_copy("asbuild-test.yml"),
            FILES[1]: plugin_copy("asbuild-verdict.yml"),
        },
    )
    before = snapshot(work)
    code, out = setup(work, capsys)
    assert code == 0, out
    assert "AsBuild is already set up here" in out and "/asbuild:story" in out
    assert hub_branches(hub) == {"main"}
    assert snapshot(work) == before


def test_S5_C8_older_files_get_an_update_that_waits_for_you(world, capsys):
    work, hub = world
    old = plugin_copy("asbuild-test.yml").replace(b"--branch v", b"--branch old-v")
    seed(work, hub, {"requirements.txt": b"pytest\n", FILES[0]: old, FILES[1]: plugin_copy("asbuild-verdict.yml")})
    code, out = setup(work, capsys)
    assert code == 0, out
    for name in FILES:
        assert hub_file(hub, "asbuild-setup", name) == plugin_copy(Path(name).name)
    assert hub_file(hub, "asbuild-setup", "requirements.txt") == b"pytest\n"
    assert "its verdict is WAITING FOR YOU. That is expected" in out
    assert "gets no verdict" not in out
    assert "It also adds pytest" not in out
    assert LINK in out


def test_S5_C9_running_again_before_the_merge_pushes_nothing_new(world, capsys):
    work, hub = world
    seed(work, hub, {"requirements.txt": b"pytest\n"})
    assert setup(work, capsys)[0] == 0
    first = git(hub, "rev-parse", "asbuild-setup")
    code, out = setup(work, capsys)
    assert code == 0, out
    assert "The branch asbuild-setup is already on GitHub with these files, so nothing new was uploaded." in out
    assert LINK in out
    assert git(hub, "rev-parse", "asbuild-setup") == first


def test_S5_C10_push_refused_for_the_workflow_scope(world, capsys):
    work, hub = world
    seed(work, hub, {"requirements.txt": b"pytest\n"})
    hook = hub / "hooks" / "pre-receive"
    hook.write_text(
        "#!/bin/sh\n"
        "echo \"refusing to allow an OAuth App to create or update workflow"
        " \\`.github/workflows/asbuild-test.yml\\` without \\`workflow\\` scope\" >&2\n"
        "exit 1\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)
    code, out = setup(work, capsys)
    assert code == 1
    assert "gh auth refresh -h github.com -s workflow" in out and AGAIN in out
    assert hub_branches(hub) == {"main"}


def test_S5_setup_runs_as_its_own_program(world):
    work, hub = world
    seed(work, hub, {"requirements.txt": b"pytest\n"})
    p = subprocess.run(
        [sys.executable, str(SCRIPT), "--no-open"], cwd=work, capture_output=True, text=True, encoding="utf-8"
    )
    assert p.returncode == 0, p.stdout + p.stderr
    assert LINK in p.stdout
