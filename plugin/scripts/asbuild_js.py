#!/usr/bin/env python3
"""AsBuild's facts about TypeScript and JavaScript projects (v0.4.0; docs/plans/v0.4-design.md §3.1, §4.4, §4.5).

Shared by setup (the kind of repository and the one stop list) and the story check (the Vitest table), and the first
JavaScript story's command:

    python asbuild_js.py tools

run once, from the project's root, in a JavaScript project's first story. It checks Node 24 or newer with npm 11.19
or newer, repairs the lockfile once by content (removes node_modules, drops names made for one kind of computer from
dependencies and devDependencies, rewrites package-lock.json), then installs the test tools with one named command:
Vitest from the table for the app's Vite, jsdom and Testing Library (proofs JS-15, JS-17, JS-19, JS-22, P-VITE8).
Exit 0: done. 1: the person or the agent must do one thing first; the message names it. 2: it could not run.
Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

# Vitest must run on the app's own Vite (JS-16); each pair was proven in JS-17 and P-VITE8 (design §4.4).
VITEST_FOR = {5: "3.2.4", 6: "3.2.4", 7: "4.1.12", 8: "5.1.0"}
NODE_MIN, NPM_MIN = (24,), (11, 19)  # npm 10 lost the other computers' packages in the repair (JS-19, JS-21)
# Names made for one kind of computer: the rule the repair proofs used (JS-15, JS-19, JS-22).
PLATFORM = re.compile(r"-(darwin|win32|linux|freebsd|android)-(arm64|x64|ia32|arm)(-|$)")
JS_CHECK = re.compile(r"\.test\.[cm]?[jt]sx?$")
VERSION = re.compile(r"^\s*(?:[\^~]|[<>]=?|=)?\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?")
NPM_FLAGS = ["--no-audit", "--no-fund", "--legacy-peer-deps"]
TOOLS = ["jsdom", "@testing-library/react", "@testing-library/dom"]

NOT_YET = (
    "AsBuild cannot check this project yet: {why}. It checks Python projects, and TypeScript or JavaScript apps"
    " built with React and Vite 5 to 8."
)
INSTALL_NODE = (
    "This project needs Node.js 24 or newer with npm 11.19 or newer{found}. Install it from https://nodejs.org (on"
    " Windows, in PowerShell: winget install --id OpenJS.NodeJS.LTS), then close and reopen Claude, so that it finds"
    " the new program."
)
ALREADY_TOOLS = (
    "The test tools were added by this project's first JavaScript story (main's locks.json lists its checks), so"
    " there is nothing to repair. If this computer has no node_modules yet, install the app's software as GitHub"
    " does, with npm ci --no-audit --no-fund --legacy-peer-deps; then write the story's checks."
)
LINKED = (
    "node_modules here is a link to another folder, so it was left as it is and nothing was changed. Remove the link"
    " (only the link, not the folder it points to), then run this again."
)
TOOLS_DONE = (
    "The test tools are installed. Commit package.json and package-lock.json with the story: the story's pull"
    " request says the list of software changed."
)


class Stop(Exception):
    """The person or the agent must do one thing first (exit 1)."""


class CannotRun(Exception):
    """The command could not run (exit 2)."""


def sh(cmd: list[str], cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


# ------------------------------------------------------------------ versions


def version_of(spec: object) -> tuple[int, ...] | None:
    """The first version a range names ("^5.4.1" gives (5, 4, 1)); None for "latest", "*", "npm:..." and the like."""
    m = VERSION.match(spec) if isinstance(spec, str) else None
    return tuple(int(g) for g in m.groups() if g is not None) if m else None


def deps(pkg: dict) -> dict:
    """dependencies and devDependencies together (a field that is not an object counts as empty)."""
    out: dict = {}
    for key in ("dependencies", "devDependencies"):
        if isinstance(pkg.get(key), dict):
            out.update(pkg[key])
    return out


def installed(name: str, pkg: dict, lockfile: dict | None) -> tuple[int, ...] | None:
    """The version that installs: package-lock.json's when it lists the package, else package.json's range."""
    packages = lockfile.get("packages") if isinstance(lockfile, dict) else None
    entry = packages.get(f"node_modules/{name}") if isinstance(packages, dict) else None
    found = version_of(entry.get("version")) if isinstance(entry, dict) else None
    return found or version_of(deps(pkg).get(name))


def shown(v: tuple[int, ...]) -> str:
    return ".".join(map(str, v))


def table_problem(vite: tuple[int, ...] | None, vitest: tuple[int, ...] | None) -> str | None:
    """Why this Vite and Vitest are outside the table (design §4.4), or None."""
    if vite is None:
        return "it is not built with Vite"
    if vite[0] not in VITEST_FOR:
        return f"it uses Vite {shown(vite)}, and AsBuild works with Vite 5 to 8"
    want = VITEST_FOR[vite[0]]
    if vitest is not None and vitest[:2] != version_of(want)[:2]:  # type: ignore[index]
        return f"it has Vitest {shown(vitest)}, and AsBuild needs Vitest {want} for Vite {vite[0]}"
    return None


# ------------------------------------------------------------------ setup: the kind of repository, the stop list


def _installed_files(paths: Iterable[str]) -> list[str]:
    return [p for p in paths if "node_modules/" not in f"/{p}"]


def kind(paths: Iterable[str]) -> str:
    """ "python", "javascript" or "subfolder", from main's tracked files (design §3.2); installed packages never
    count."""
    own = _installed_files(paths)
    if any(p.endswith(".py") for p in own) or {"requirements.txt", "pyproject.toml"} & set(own):
        return "python"
    if "package.json" in own:
        return "javascript"
    return "subfolder" if subfolder(own) else "python"


def subfolder(paths: Iterable[str]) -> str | None:
    """The first folder below the root that holds a package.json, or None."""
    found = sorted(p.rsplit("/", 1)[0] for p in _installed_files(paths) if p.endswith("/package.json"))
    return found[0] if found else None


def _has(*names: str) -> Callable[[dict, dict | None, set[str]], bool]:
    return lambda pkg, lockfile, paths: any(n in deps(pkg) for n in names)


def _vite(pkg: dict, lockfile: dict | None, paths: set[str]) -> str | None:
    return table_problem(installed("vite", pkg, lockfile), installed("vitest", pkg, lockfile))


# The one stop list (design §3.1's last row), in order: each entry says why, or nothing.
STOP_LIST: list[tuple[str, Callable[[dict, dict | None, set[str]], str | None]]] = [
    ("unreadable", lambda pkg, lockfile, paths: None),  # checked before the list runs (stop_reason)
    (
        "workspaces",
        lambda pkg, lockfile, paths: (
            "it uses workspaces (several apps in one repository)"
            if "workspaces" in pkg or "pnpm-workspace.yaml" in paths
            else None
        ),
    ),
    ("next", lambda pkg, lockfile, paths: "it is a Next.js app" if _has("next")(pkg, lockfile, paths) else None),
    (
        "react",
        lambda pkg, lockfile, paths: (
            "it is a React Native app"
            if _has("react-native")(pkg, lockfile, paths)
            else None
            if _has("react")(pkg, lockfile, paths)
            else "it is not a React app"
        ),
    ),
    ("vite", lambda pkg, lockfile, paths: _vite(pkg, lockfile, paths) if "vitest" not in deps(pkg) else None),
    ("vitest", lambda pkg, lockfile, paths: _vite(pkg, lockfile, paths) if "vitest" in deps(pkg) else None),
    (
        "jest",
        lambda pkg, lockfile, paths: (
            "its tests use Jest, and AsBuild works with Vitest"
            if _has("jest")(pkg, lockfile, paths) and "vitest" not in deps(pkg)
            else None
        ),
    ),
    (
        "playwright",
        lambda pkg, lockfile, paths: (
            "it has Playwright tests" if _has("@playwright/test", "playwright")(pkg, lockfile, paths) else None
        ),
    ),
]


def _json(raw: bytes | None) -> object:
    try:
        return json.loads(raw.decode("utf-8-sig")) if raw is not None else None
    except (ValueError, UnicodeDecodeError):
        return None


def stop_reason(package: bytes, lockfile: bytes | None, paths: set[str]) -> str | None:
    """The plain stop for a JavaScript repository outside what AsBuild supports, or None (it is supported)."""
    pkg = _json(package)
    if not isinstance(pkg, dict):
        return NOT_YET.format(why="its package.json cannot be read")
    lock = _json(lockfile)
    lock = lock if isinstance(lock, dict) else None
    for _, rule in STOP_LIST:
        why = rule(pkg, lock, paths)
        if why:
            return NOT_YET.format(why=why)
    return None


# ------------------------------------------------------------------ this computer's Node and npm


def _version(tool: str) -> tuple[tuple[int, ...] | None, str]:
    p = sh([shutil.which(tool) or tool, "--version"])
    text = p.stdout.strip() if p.returncode == 0 else ""
    return version_of(text), text.removeprefix("v") or "unknown"


def tool_problem() -> str | None:
    """Why this computer's Node or npm cannot run the checks (Node 24 or newer, npm 11.19 or newer), or None."""
    for tool, label, floor in (("node", "Node.js", NODE_MIN), ("npm", "npm", NPM_MIN)):
        if shutil.which(tool) is None:
            return f"{label} is not installed. " + INSTALL_NODE.format(found="")
        v, text = _version(tool)
        if v is None or v < floor:
            return INSTALL_NODE.format(found=f"; this computer has {label} {text}")
    return None


# ------------------------------------------------------------------ the first story's command (M3-C2)


def drop_platform(pkg: dict) -> list[str]:
    """Remove names made for one kind of computer from dependencies and devDependencies (never optionalDependencies,
    where such names are a known workaround); the names removed, in order."""
    out = []
    for key in ("dependencies", "devDependencies"):
        group = pkg.get(key)
        if isinstance(group, dict):
            for name in [n for n in group if PLATFORM.search(n)]:
                del group[name]
                out.append(name)
    return out


def _writable(func, path, exc) -> None:
    """shutil's hook for a file it could not remove: a read-only file (Windows) is made writable and removed again;
    a link is never followed (review round 1, B5)."""
    if func is os.path.islink:
        raise exc
    os.chmod(path, stat.S_IWRITE)  # pragma: no cover - a read-only file, on Windows only
    func(path)  # pragma: no cover


def remove_tree(path: Path) -> None:
    shutil.rmtree(path, onexc=_writable)


def npm(args: list[str], cwd: Path) -> None:
    p = sh([shutil.which("npm") or "npm", *args], cwd)
    if p.returncode != 0:
        last = "\n".join((p.stderr or p.stdout).strip().splitlines()[-8:])
        raise Stop(f"npm {args[0]} failed, so nothing more was changed. npm said:\n{last}")


def tools() -> list[str]:
    """The first JavaScript story's repair and test tools; the lines to print."""
    problem = tool_problem()
    if problem:
        raise Stop(problem)
    top = sh(["git", "rev-parse", "--show-toplevel"])
    if top.returncode != 0:
        raise CannotRun("this is not a git repository: run it from the project's folder")
    root = Path(top.stdout.strip())
    main_lock = sh(["git", "show", "origin/main:locks.json"], root)
    files = _json(main_lock.stdout.encode()) if main_lock.returncode == 0 else None
    listed = files.get("files") if isinstance(files, dict) else None
    if isinstance(listed, dict) and any(JS_CHECK.search(p) for p in listed):
        raise Stop(ALREADY_TOOLS)
    pkg_file = root / "package.json"
    if not pkg_file.is_file():
        raise CannotRun("there is no package.json at the project's root: this is not a JavaScript project")
    pkg = _json(pkg_file.read_bytes())
    if not isinstance(pkg, dict):
        raise CannotRun("package.json cannot be read: fix it, then run this again")
    lines = []
    if (root / "node_modules").is_symlink() or (root / "node_modules").is_junction():
        raise Stop(LINKED)
    if (root / "node_modules").exists():
        remove_tree(root / "node_modules")
        lines.append("Removed node_modules (the install below rebuilds it).")
    dropped = drop_platform(pkg)
    if dropped:
        pkg_file.write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        lines.append("Removed parts made for one kind of computer from package.json: " + ", ".join(dropped) + ".")
    npm(["install", "--package-lock-only", *NPM_FLAGS], root)
    lines.append("Rewrote package-lock.json, so it installs on every kind of computer.")
    lock = _json((root / "package-lock.json").read_bytes()) if (root / "package-lock.json").is_file() else None
    vite = installed("vite", {}, lock if isinstance(lock, dict) else None)
    why = table_problem(vite, None)
    if why or vite is None:
        raise Stop(NOT_YET.format(why=why))
    want = VITEST_FOR[vite[0]]
    npm(["install", "--save-dev", "--save-exact", *NPM_FLAGS, f"vitest@{want}", *TOOLS], root)
    lines.append(f"Installed Vitest {want} (for Vite {vite[0]}), jsdom and Testing Library.")
    return lines + [TOOLS_DONE]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if args != ["tools"]:
        print("usage: asbuild_js.py tools")
        return 2
    try:
        print("\n".join(tools()))
    except Stop as e:
        print(e)
        return 1
    except CannotRun as e:
        print(f"asbuild_js.py could not run: {e}")
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
