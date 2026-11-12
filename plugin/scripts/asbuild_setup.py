#!/usr/bin/env python3
"""AsBuild's setup: wire a GitHub repository to AsBuild with one command (decision D39, docs/plans/S5.md).

Usage, from the project's folder: python asbuild_setup.py [--repo DIR] [--no-open]

It checks Git, the GitHub sign-in and the repository, then puts AsBuild's two workflow files (this plugin's own
copy) on a branch named asbuild-setup on GitHub and opens GitHub's page for the pull request, which the person
creates and merges. On an empty repository it first makes the first commit, a requirements.txt that lists pytest,
and uploads it as main. Every commit is made with Git's plumbing on a temporary index, so the person's folder, its
current branch and any unsaved work are left exactly as they were. The upload is the last step.

Exit 0: done, or nothing to do. 1: the person must do one thing first; the message names it. 2: setup could not run.
Standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
WORKFLOWS = HERE.parent / "workflows"
FILES = ("asbuild-test.yml", "asbuild-verdict.yml")
BRANCH = "asbuild-setup"
TITLE = "Add AsBuild"
BODY = "Adds AsBuild's two workflow files, asbuild-test.yml and asbuild-verdict.yml, made by /asbuild:setup."
BODY_REQS = " It also adds pytest to requirements.txt, because AsBuild's check runs the tests with pytest."
GITHUB = re.compile(r"^(?:https://(?:[^@/]+@)?github\.com/|git@github\.com:|ssh://git@github\.com/)([^/]+)/(.+?)/?$")
PYTEST = re.compile(r"^\s*pytest\s*(?:[<>=!~;\[#@]|$)", re.IGNORECASE | re.MULTILINE)
QUIET = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}  # a missing sign-in fails instead of waiting

AGAIN = "Then run /asbuild:setup again."
NO_GIT = "Git is not installed. Install it from https://git-scm.com (on Windows: winget install --id Git.Git)."
NOT_REPO = "This folder is not a Git repository. Open your project's own folder, the one linked to GitHub."
NO_ORIGIN = (
    "This repository has no link to GitHub (no remote named origin). Add it with:\n"
    "  git remote add origin https://github.com/<owner>/<repository>.git"
)
NOT_GITHUB = "This repository's origin is not on github.com: {url}\nAsBuild works with GitHub repositories only."
NO_IDENTITY = (
    "Git has no name or email for its commits yet. Set them once with these two commands, with your own name and"
    ' email:\n  git config --global user.name "Your Name"\n  git config --global user.email you@example.com'
)
NO_GH = (
    "The GitHub CLI (gh) is not installed. Install it from https://cli.github.com"
    " (on Windows: winget install --id GitHub.cli)."
)
NOT_SIGNED_IN = (
    "You are not signed in to GitHub. Run this, then choose GitHub.com, HTTPS, and sign in with your browser:\n"
    "  gh auth login"
)
UNREACHABLE = "Could not reach the repository on GitHub. Check that you are signed in and online. Git said:\n{detail}"
NOT_MAIN = (
    "GitHub's default branch for this repository is {branch}, not main. AsBuild judges pull requests into main."
    " On GitHub, open the repository's Settings, then General, and set Default branch to main."
)
SCOPE = (
    "GitHub refused the two workflow files: your GitHub sign-in is not allowed to change workflow files yet."
    " Run this once to allow it:\n  gh auth refresh -h github.com -s workflow"
)
REFUSED = "GitHub refused the upload. Git said:\n{detail}"
ALREADY = (
    "AsBuild is already set up here: the two workflow files on main are this plugin's."
    " Next, say what you want with /asbuild:story."
)
EMPTY = (
    "This repository was empty, so setup made its first commit, a requirements.txt that lists pytest, and uploaded"
    " it as main."
)
SAME = "The branch asbuild-setup is already on GitHub with these files, so nothing new was uploaded."
READY = (
    "Setup prepared AsBuild's two workflow files on the branch asbuild-setup. Create the pull request on the page"
    " that opened, then merge it:\n  {link}"
)
ADDS_PYTEST = "It also adds pytest to requirements.txt, because AsBuild's check runs your tests with pytest."
FIRST = "This pull request gets no verdict: AsBuild judges the pull requests that come after it."
UPDATE = (
    "This pull request changes AsBuild's workflow files, which AsBuild protects, so its verdict is WAITING FOR YOU."
    " That is expected: read it, and merge it."
)
AFTER = "When it is merged, tell Claude, so it brings main up to date here. Then say what you want with /asbuild:story."


class Stop(Exception):
    """The person must do one thing first (exit 1)."""


class CannotRun(Exception):
    """Setup could not run (exit 2)."""


class Repo:
    def __init__(self, git: str, top: Path) -> None:
        self.git, self.top = git, top

    def run(
        self, *args: str, data: bytes | None = None, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess:
        full = {**os.environ, **QUIET, **(env or {})}
        return subprocess.run([self.git, *args], cwd=self.top, input=data, capture_output=True, env=full)

    def out(self, *args: str, data: bytes | None = None, env: dict[str, str] | None = None) -> str:
        p = self.run(*args, data=data, env=env)
        if p.returncode != 0:
            raise CannotRun(f"git {args[0]} failed: {text(p.stderr)}")
        return text(p.stdout)

    def show(self, sha: str, path: str) -> bytes | None:
        p = self.run("cat-file", "blob", f"{sha}:{path}")
        return p.stdout if p.returncode == 0 else None

    def commit(self, parent: str | None, files: dict[str, bytes], message: str) -> str:
        """A commit of `parent`'s tree with `files` written in, made on a temporary index."""
        with tempfile.TemporaryDirectory() as tmp:
            env = {"GIT_INDEX_FILE": str(Path(tmp) / "index")}
            if parent:
                self.out("read-tree", parent, env=env)
            for path, data in files.items():
                blob = self.out("hash-object", "-w", "--no-filters", "--stdin", data=data)
                self.out("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
            tree = self.out("write-tree", env=env)
        return self.out("commit-tree", tree, *(["-p", parent] if parent else []), "-m", message)

    def push(self, sha: str, branch: str) -> None:
        p = self.run("push", "--quiet", "origin", f"{sha}:refs/heads/{branch}")
        if p.returncode != 0:
            detail = text(p.stderr)
            raise Stop(SCOPE if "without `workflow` scope" in detail else REFUSED.format(detail=detail))


def text(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace").strip()


def wanted() -> dict[str, bytes]:
    """This plugin's two workflow files, with LF line endings whatever the install did to them."""
    return {f".github/workflows/{n}": (WORKFLOWS / n).read_bytes().replace(b"\r\n", b"\n") for n in FILES}


def with_pytest(reqs: bytes | None) -> bytes | None:
    """requirements.txt with pytest added, or None when it already lists pytest."""
    if reqs is None:
        return b"pytest\n"
    if PYTEST.search(reqs.decode("utf-8", errors="replace")):
        return None
    return reqs + (b"" if reqs.endswith(b"\n") or not reqs else b"\n") + b"pytest\n"


def page(owner: str, name: str, body: str) -> str:
    return (
        f"https://github.com/{owner}/{name}/compare/main...{BRANCH}?quick_pull=1"
        f"&title={quote(TITLE)}&body={quote(body)}"
    )


def remote_state(repo: Repo) -> tuple[dict[str, str], str | None]:
    """GitHub's branches (name to commit) and its default branch."""
    p = repo.run("ls-remote", "--symref", "origin")
    if p.returncode != 0:
        raise Stop(UNREACHABLE.format(detail=text(p.stderr)))
    heads: dict[str, str] = {}
    default = None
    for line in text(p.stdout).splitlines():
        left, _, right = line.partition("\t")
        if left.startswith("ref: ") and right == "HEAD":
            default = left[len("ref: ") :].removeprefix("refs/heads/")
        elif right.startswith("refs/heads/"):
            heads[right.removeprefix("refs/heads/")] = left
    return heads, default


def setup(start: Path, open_page: bool) -> list[str]:
    git = shutil.which("git")
    if not git:
        raise Stop(NO_GIT)
    p = subprocess.run([git, "rev-parse", "--show-toplevel"], cwd=start, capture_output=True)
    if p.returncode != 0:
        raise Stop(NOT_REPO)
    repo = Repo(git, Path(text(p.stdout)))
    origin = repo.run("config", "--get", "remote.origin.url")  # as written: `remote get-url` applies insteadOf
    if origin.returncode != 0:
        raise Stop(NO_ORIGIN)
    url = text(origin.stdout)
    found = GITHUB.match(url)
    if not found:
        raise Stop(NOT_GITHUB.format(url=url))
    owner, name = found.group(1), found.group(2).removesuffix(".git")
    if not (text(repo.run("config", "user.name").stdout) and text(repo.run("config", "user.email").stdout)):
        raise Stop(NO_IDENTITY)
    gh = shutil.which("gh")
    if not gh:
        raise Stop(NO_GH)
    if subprocess.run([gh, "auth", "status", "--hostname", "github.com"], capture_output=True).returncode != 0:
        raise Stop(NOT_SIGNED_IN)

    said: list[str] = []
    heads, default = remote_state(repo)
    if not heads:  # an empty repository: its first commit is requirements.txt, uploaded as main (V3-1A, V3-3A)
        own_file = repo.top / "requirements.txt"
        own = own_file.read_bytes() if own_file.is_file() else b""
        first = repo.commit(
            None, {"requirements.txt": with_pytest(own or None) or own}, "Add requirements.txt for AsBuild"
        )
        repo.push(first, "main")
        heads, default = {"main": first}, "main"
        said.append(EMPTY)
    if default != "main":
        raise Stop(NOT_MAIN.format(branch=default or "unknown"))
    fetch = [f"refs/heads/{b}" for b in ("main", BRANCH) if b in heads]
    fetched = repo.run("fetch", "--quiet", "--no-tags", "origin", *fetch)
    if fetched.returncode != 0:
        raise Stop(UNREACHABLE.format(detail=text(fetched.stderr)))

    main = heads["main"]
    files = wanted()
    on_main = {path: repo.show(main, path) for path in files}
    if on_main == files:
        return [*said, ALREADY]
    reqs = with_pytest(repo.show(main, "requirements.txt"))
    if reqs is not None:
        files["requirements.txt"] = reqs
    body = BODY + (BODY_REQS if reqs is not None else "")
    link = page(owner, name, body)
    parent = heads.get(BRANCH)
    if parent and all(repo.show(parent, path) == data for path, data in files.items()):
        said.append(SAME)
    else:
        repo.push(repo.commit(parent or main, files, TITLE), BRANCH)
    said.append(READY.format(link=link))
    if reqs is not None:
        said.append(ADDS_PYTEST)
    said.append(UPDATE if any(on_main.values()) else FIRST)
    said.append(AFTER)
    if open_page:
        webbrowser.open(link)
    return said


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="asbuild_setup.py", description="Wire this GitHub repository to AsBuild.")
    ap.add_argument("--repo", type=Path, default=Path.cwd(), help="the project's folder (default: this one)")
    ap.add_argument("--no-open", action="store_true", help="print the pull request page's link, do not open it")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        print("\n".join(setup(a.repo, not a.no_open)))
    except Stop as e:
        print(f"{e}\n{AGAIN}")
        return 1
    except CannotRun as e:
        print(f"Setup could not run: {e}")
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
