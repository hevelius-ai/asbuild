#!/usr/bin/env python3
"""AsBuild's setup: wire a GitHub repository to AsBuild with one command (decision D39, docs/plans/S5.md).

Usage, from the project's folder: python asbuild_setup.py [--repo DIR] [--no-open]

It checks Git, the GitHub sign-in and the repository, then puts AsBuild's two workflow files (this plugin's own
copy) on a branch named asbuild-setup on GitHub and opens GitHub's page for the pull request, which the person
creates and merges. On an empty repository it first makes the first commit, a requirements.txt that lists pytest,
and uploads it as main. Every commit is made with Git's plumbing on a temporary index, so the person's folder, its
current branch and any unsaved work are left exactly as they were. Messages are printed as each step is done, so
an upload of main on an empty repository is reported even when a later step stops.

Exit 0: done, or nothing to do. 1: the person must do one thing first; the message names it. 2: setup could not run.
Standard library only.
"""

from __future__ import annotations

import argparse
import codecs
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
TITLE = {False: "Add AsBuild", True: "Update AsBuild"}
BODY = {
    False: "Adds AsBuild's two workflow files, asbuild-test.yml and asbuild-verdict.yml, made by /asbuild:setup.",
    True: "Updates AsBuild's two workflow files, asbuild-test.yml and asbuild-verdict.yml, made by /asbuild:setup.",
}
BODY_REQS = " It also adds pytest to requirements.txt, because AsBuild's check runs the tests with pytest."
GITHUB = re.compile(
    r"^(?:https?://(?:[^@/]+@)?(?:www\.)?github\.com/|git@github\.com:|ssh://git@github\.com(?::22)?/)"
    r"([^/]+)/(.+?)/?$",
    re.IGNORECASE,
)
PYTEST = re.compile(r"^\s*pytest\s*(?:[<>=!~;\[#@]|$)", re.IGNORECASE | re.MULTILINE)
QUIET = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}  # a missing sign-in fails instead of waiting
BOMS = ((codecs.BOM_UTF8, "utf-8"), (codecs.BOM_UTF16_LE, "utf-16-le"), (codecs.BOM_UTF16_BE, "utf-16-be"))

AGAIN = "Then run /asbuild:setup again."
REOPEN = "After installing it, close and reopen Claude, so that it finds the new program."
NO_GIT = (
    f"Git is not installed. Install it from https://git-scm.com (on Windows: winget install --id Git.Git). {REOPEN}"
)
NOT_REPO = "This folder is not a Git repository. Open your project's own folder, the one linked to GitHub."
NO_ORIGIN = (
    "This repository has no link to GitHub (no remote named origin). Add it with:\n"
    "  git remote add origin https://github.com/<owner>/<repository>.git"
)
NOT_GITHUB = (
    "This repository's origin does not look like a github.com address: {url}\n"
    "AsBuild works with repositories on github.com. If this one is on github.com, set origin to its web address:\n"
    "  git remote set-url origin https://github.com/<owner>/<repository>.git"
)
SET_IDENTITY = (
    "Tell Claude the name and email to use, and it sets them for you. Or run these two commands once, with your own"
    ' name and email in place of the examples:\n  git config{flag} user.name "Your Name"\n'
    "  git config{flag} user.email you@example.com"
)
NO_IDENTITY = "Git has no name or email for its commits yet. " + SET_IDENTITY.format(flag=" --global")
EXAMPLE_IDENTITY = (
    'Git\'s name or email is still the example ("Your Name" or you@example.com), so your commits would carry it.'
    " {where}"
)
EXAMPLE_GLOBAL = EXAMPLE_IDENTITY.format(where=SET_IDENTITY.format(flag=" --global"))
EXAMPLE_LOCAL = EXAMPLE_IDENTITY.format(
    where="It is set in this repository's own settings, so the commands leave out --global (run them in this"
    " folder). " + SET_IDENTITY.format(flag="")
)
EXAMPLES = ("Your Name", "you@example.com")  # the README's and NO_IDENTITY's examples (D40, T2)
NO_GH = (
    "The GitHub CLI (gh) is not installed. Install it from https://cli.github.com"
    f" (on Windows: winget install --id GitHub.cli). {REOPEN}"
)
GIT_SIGN_IN = (
    "If Git is not signed in to GitHub, run gh auth login (choose GitHub.com, HTTPS, and Yes to signing in Git with"
    " your GitHub credentials); if gh is signed in already, run gh auth setup-git so that Git uses the same sign-in."
)
NOT_SIGNED_IN = (
    "You are not signed in to GitHub. Run this, then choose GitHub.com, HTTPS, and sign in with your browser:\n"
    "  gh auth login"
)
UNREACHABLE = (
    "Git could not reach the repository on GitHub. Check that you are online. "
    + GIT_SIGN_IN
    + ("\nGit said:\n{detail}")
)
LOCAL_ONLY = (
    "The repository on GitHub is empty, but this folder already has commits. Upload them first, as main:\n"
    "  git push -u origin HEAD:main"
)
NOT_MAIN = (
    "GitHub's default branch for this repository is {branch}, not main. AsBuild judges pull requests into main."
    " On GitHub, open the repository's Settings, then General, and set Default branch to main."
)
NO_MAIN = (
    "GitHub's default branch for this repository is {branch}, and it has no branch named main. AsBuild judges pull"
    " requests into main. On GitHub, open the repository's Settings, then General, and rename the default branch"
    " {branch} to main with the pencil button next to it."
)
SCOPE = (
    "GitHub refused the two workflow files: your GitHub sign-in is not allowed to change workflow files yet."
    " Run this once to allow it:\n  gh auth refresh -h github.com -s workflow\n"
    "If GitHub still refuses after that, Git is using another sign-in than gh: run gh auth setup-git as well."
)
REFUSED = "GitHub refused the upload. " + GIT_SIGN_IN + "\nGit said:\n{detail}"
BAD_REQS = {
    "main": "Setup cannot read requirements.txt on main: it is not saved as UTF-8 or UTF-16 text. Save it as UTF-8,"
    " with a line that says pytest, and upload it to main.",
    "folder": "Setup cannot read this folder's requirements.txt: it is not saved as UTF-8 or UTF-16 text. Save it as"
    " UTF-8, with a line that says pytest.",
}
ALREADY = (
    "AsBuild is already set up here: the two workflow files on main are this plugin's."
    " Next, say what you want with /asbuild:story."
)
EMPTY_OWN = (
    "This repository was empty, so setup made its first commit from this folder's requirements.txt{added} and"
    " uploaded it to GitHub as main."
)
EMPTY_NEW = (
    "This repository was empty, so setup made its first commit, a new requirements.txt that lists pytest, and"
    " uploaded it to GitHub as main."
)
SAME = "The branch asbuild-setup is already on GitHub with these files, so nothing new was uploaded."
REPLACED = (
    "An older asbuild-setup branch was on GitHub with nothing but setup's own commits or commits already on"
    " main; setup replaced it with one made from today's main."
)
FOREIGN = (
    "The branch asbuild-setup on GitHub holds commits that setup did not make, so setup leaves it alone. On GitHub,"
    " merge or close its pull request and delete the branch."
)
READY = (
    "Setup prepared AsBuild's two workflow files on the branch asbuild-setup. Create the pull request on this page,"
    " then merge it:\n  {link}"
)
ADDS_PYTEST = "It also adds pytest to requirements.txt, because AsBuild's check runs your tests with pytest."
FIRST = "This pull request gets no verdict: AsBuild judges the pull requests that come after it."
UPDATE = (
    "This pull request changes AsBuild's workflow files, which AsBuild protects, so its verdict is WAITING FOR YOU."
    " That is expected: read it, and merge it."
)
AFTER = "When it is merged, tell Claude, so it brings main up to date here. Then say what you want with /asbuild:story."
OPENED = "The page is open in your browser."
NOT_OPENED = "Open the link above in your browser."


class Stop(Exception):
    """The person must do one thing first (exit 1)."""


class CannotRun(Exception):
    """Setup could not run (exit 2)."""


def say(message: str) -> None:
    print(message, flush=True)


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

    def parent_of(self, sha: str) -> str | None:
        p = self.run("rev-parse", "--verify", "--quiet", f"{sha}^")
        return text(p.stdout) if p.returncode == 0 else None

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

    def push(self, sha: str, branch: str, replacing: str | None = None) -> None:
        lease = [f"--force-with-lease=refs/heads/{branch}:{replacing}"] if replacing else []
        p = self.run("push", "--quiet", "--no-follow-tags", *lease, "origin", f"{sha}:refs/heads/{branch}")
        if p.returncode != 0:
            detail = text(p.stderr)
            raise Stop(SCOPE if "without `workflow` scope" in detail else REFUSED.format(detail=detail))


def text(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace").strip()


def wanted() -> dict[str, bytes]:
    """This plugin's two workflow files, with LF line endings whatever the install did to them."""
    return {f".github/workflows/{n}": (WORKFLOWS / n).read_bytes().replace(b"\r\n", b"\n") for n in FILES}


def with_pytest(reqs: bytes | None, where: str = "main") -> bytes | None:
    """requirements.txt with a pytest line added, in its own encoding and line endings; None when it lists pytest."""
    if reqs is None:
        return b"pytest\n"
    bom, encoding = next(((b, e) for b, e in BOMS if reqs.startswith(b)), (b"", "utf-8"))
    try:
        listed = reqs[len(bom) :].decode(encoding)
    except UnicodeDecodeError:
        raise Stop(BAD_REQS[where]) from None
    if PYTEST.search(listed):
        return None
    newline = "\r\n" if "\r\n" in listed else "\n"
    listed += ("" if not listed or listed.endswith("\n") else newline) + "pytest" + newline
    return bom + listed.encode(encoding)


def page(owner: str, name: str, update: bool, body: str) -> str:
    return (
        f"https://github.com/{owner}/{name}/compare/main...{BRANCH}?quick_pull=1"
        f"&title={quote(TITLE[update])}&body={quote(body)}"
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


def setup_made(repo: Repo, main: str, old: str) -> bool:
    """Every commit on the old setup branch that main does not hold is one of setup's own."""
    p = repo.run("log", "--format=%s", f"{main}..{old}")
    return p.returncode == 0 and all(s in TITLE.values() for s in text(p.stdout).splitlines())


def first_commit(repo: Repo) -> str:
    """On an empty repository whose folder has no commits either: requirements.txt, uploaded as main (D39)."""
    if repo.run("rev-parse", "--verify", "--quiet", "HEAD").returncode == 0:
        raise Stop(LOCAL_ONLY)
    own_file = repo.top / "requirements.txt"
    own = own_file.read_bytes() if own_file.is_file() else None
    added = with_pytest(own, "folder")
    sha = repo.commit(None, {"requirements.txt": added or own or b""}, "Add requirements.txt for AsBuild")
    repo.push(sha, "main")
    if own is None:
        say(EMPTY_NEW)
    else:
        say(EMPTY_OWN.format(added=", with pytest added," if added else ""))
    return sha


def setup(start: Path, open_page: bool) -> None:
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
        raise Stop(NOT_GITHUB.format(url=re.sub(r"(://)[^/]*@", r"\1", url)))  # never echo a token in the URL
    owner, name = found.group(1), found.group(2).removesuffix(".git")
    identity = (text(repo.run("config", "user.name").stdout), text(repo.run("config", "user.email").stdout))
    if not all(identity):
        raise Stop(NO_IDENTITY)
    if any(value in EXAMPLES for value in identity):  # name the scope that holds it, or the fix changes nothing
        local = (text(repo.run("config", "--local", key).stdout) for key in ("user.name", "user.email"))
        raise Stop(EXAMPLE_LOCAL if any(value in EXAMPLES for value in local) else EXAMPLE_GLOBAL)
    gh = shutil.which("gh")
    if not gh:
        raise Stop(NO_GH)
    heads, default = remote_state(repo)  # first, so that being offline is not reported as signed out
    if subprocess.run([gh, "auth", "status", "--hostname", "github.com"], capture_output=True).returncode != 0:
        raise Stop(NOT_SIGNED_IN)

    if not heads:
        heads, default = {"main": first_commit(repo)}, "main"
    if default != "main":
        raise Stop((NOT_MAIN if "main" in heads else NO_MAIN).format(branch=default or "unknown"))
    fetch = [f"refs/heads/{b}" for b in ("main", BRANCH) if b in heads]
    fetched = repo.run("fetch", "--quiet", "--no-tags", "origin", *fetch)
    if fetched.returncode != 0:
        raise Stop(UNREACHABLE.format(detail=text(fetched.stderr)))

    main = heads["main"]
    files = wanted()
    on_main = {path: repo.show(main, path) for path in files}
    if on_main == files:
        say(ALREADY)
        return
    update = on_main[".github/workflows/asbuild-verdict.yml"] is not None  # only then is there a verdict
    reqs = with_pytest(repo.show(main, "requirements.txt"))
    if reqs is not None:
        files["requirements.txt"] = reqs
    link = page(owner, name, update, BODY[update] + (BODY_REQS if reqs is not None else ""))
    old = heads.get(BRANCH)
    if old and repo.parent_of(old) == main and all(repo.show(old, path) == data for path, data in files.items()):
        say(SAME)
    else:
        if old and not setup_made(repo, main, old):
            raise Stop(FOREIGN)
        repo.push(repo.commit(main, files, TITLE[update]), BRANCH, replacing=old)
        if old:
            say(REPLACED)
    say(READY.format(link=link))
    if reqs is not None:
        say(ADDS_PYTEST)
    say(UPDATE if update else FIRST)
    say(AFTER)
    if open_page:
        say(OPENED if webbrowser.open(link) else NOT_OPENED)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="asbuild_setup.py", description="Wire this GitHub repository to AsBuild.")
    ap.add_argument("--repo", type=Path, default=Path.cwd(), help="the project's folder (default: this one)")
    ap.add_argument("--no-open", action="store_true", help="print the pull request page's link, do not open it")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        setup(a.repo, not a.no_open)
    except Stop as e:
        say(f"{e}\n{AGAIN}")
        return 1
    except CannotRun as e:
        say(f"Setup could not run: {e}")
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
