"""v0.4.0's conformance rows for setup (`cases.json`, level "setup", milestone M3; docs/plans/v0.4-M3.md, M3-C3).

Each row's repository is built here as `main` on a local stand-in for GitHub, and the real setup script runs on it,
as the skill runs it, with a stand-in `gh` and a stand-in Node and npm on the PATH (so the result does not depend on
this computer's Node). The row's expectation is then read from what setup did:

- "Python path, as today": the setup branch holds the two workflow files and a `requirements.txt` that lists pytest;
- "JavaScript path": the setup branch holds the two workflow files and nothing else;
- "stops: not yet": exit 1, AsBuild's plain "not yet" sentence, nothing uploaded;
- "stops: not yet, with the install line": exit 1, the Node.js install line, nothing uploaded.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugin" / "scripts"))
import asbuild_setup  # noqa: E402

TABLE = json.loads((Path(__file__).resolve().parent / "cases.json").read_text(encoding="utf-8"))
ROWS = {r["id"]: r for r in TABLE["cases"] if r["level"] == "setup"}
URL = "https://github.com/someone/project.git"
WORKFLOWS = {".github/workflows/asbuild-test.yml", ".github/workflows/asbuild-verdict.yml"}


def package(deps: dict | None = None, dev: dict | None = None, **extra) -> str:
    doc = {"name": "app", "private": True, **extra}
    if deps is not None:
        doc["dependencies"] = deps
    if dev is not None:
        doc["devDependencies"] = dev
    return json.dumps(doc, indent=2) + "\n"


REACT = {"react": "^18.3.1", "react-dom": "^18.3.1"}
VITE = {"vite": "^5.4.1", "@vitejs/plugin-react-swc": "^3.5.0", "typescript": "^5.5.3"}
APP = package(REACT, VITE)
LOCK = json.dumps({"lockfileVersion": 3, "packages": {"": {}, "node_modules/vite": {"version": "5.4.21"}}}) + "\n"
SRC = "export default function App() { return <h1>Hi</h1>; }\n"

# Each row's repository (a row may hold more than one shape: every one must give the row's outcome).
TREES: dict[str, list[dict[str, str]]] = {
    "setup-py-subfolder-package": [{"tools/build.py": "print('build')\n", "web/package.json": APP}],
    "setup-both-at-root": [{"package.json": APP, "requirements.txt": "flask\n", "src/App.tsx": SRC}],
    "setup-js-root": [{"package.json": APP, "package-lock.json": LOCK, "src/App.tsx": SRC}],
    "setup-stop-subfolder-app": [{"web/package.json": APP, "web/src/App.tsx": SRC, "README.md": "# app\n"}],
    "setup-stop-no-react": [
        {"package.json": package(None, {"prettier": "^3.3.3"})},  # a root tooling package.json, no Python file
        {"package.json": package({**REACT, "react-native": "0.76.0"}, VITE)},
    ],
    "setup-stop-vite": [
        {"package.json": package(REACT, {"webpack": "^5.95.0"})},
        {"package.json": package(REACT, {"vite": "^4.5.0"})},
    ],
    "setup-stop-vitest-off-table": [{"package.json": package(REACT, {**VITE, "vitest": "^2.1.8"})}],
    "setup-stop-jest-only": [{"package.json": package(REACT, {**VITE, "jest": "^29.7.0"})}],
    "setup-stop-playwright": [{"package.json": package(REACT, {**VITE, "@playwright/test": "^1.48.0"})}],
    "setup-stop-workspaces": [
        {"package.json": package(REACT, VITE, workspaces=["packages/*"])},
        {"package.json": APP, "pnpm-workspace.yaml": "packages:\n  - 'packages/*'\n"},
    ],
    "setup-stop-next": [{"package.json": package({**REACT, "next": "15.0.3"})}],
    "setup-stop-npm": [{"package.json": APP, "package-lock.json": LOCK, "src/App.tsx": SRC}],
}
# The stand-in Node and npm each row runs with: the floor (Node 24, npm 11.19) except where the row is about them.
TOOLS = {"setup-stop-npm": ("v22.11.0", "10.9.0")}


def git(cwd: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return p.stdout


def stand_in(bin_dir: Path, name: str, says: str) -> None:
    if os.name == "nt":
        (bin_dir / f"{name}.cmd").write_text(f"@echo {says}\r\n@exit /b 0\r\n", encoding="utf-8")
    else:
        (bin_dir / name).write_text(f"#!/bin/sh\necho {says}\nexit 0\n", encoding="utf-8")
        (bin_dir / name).chmod(0o755)


def run_row(tmp_path: Path, monkeypatch, capsys, row_id: str, tree: dict[str, str]):
    (tmp_path / "gitconfig").write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    node, npm = TOOLS.get(row_id, ("v24.22.1", "11.19.1"))
    stand_in(bin_dir, "gh", "signed in")
    stand_in(bin_dir, "node", node)
    stand_in(bin_dir, "npm", npm)
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
    for rel, text in tree.items():
        (work / rel).parent.mkdir(parents=True, exist_ok=True)
        (work / rel).write_text(text, encoding="utf-8", newline="\n")
    git(work, "add", "-A")
    git(work, "commit", "--quiet", "-m", "the app")
    git(work, "push", "--quiet", "origin", "main")
    code = asbuild_setup.main(["--repo", str(work), "--no-open"])
    out = capsys.readouterr().out
    branch = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "asbuild-setup"], cwd=hub, capture_output=True, text=True
    )
    files = set(branch.stdout.split()) if branch.returncode == 0 else None
    reqs = subprocess.run(["git", "show", "asbuild-setup:requirements.txt"], cwd=hub, capture_output=True, text=True)
    return code, out, files, set(tree), reqs.stdout


def test_every_setup_row_has_a_repository():
    assert set(TREES) == set(ROWS)


@pytest.mark.parametrize(("row_id", "tree"), [(row_id, tree) for row_id, trees in TREES.items() for tree in trees])
def test_setup_row(tmp_path, monkeypatch, capsys, row_id, tree):
    outcome = ROWS[row_id]["expect"]["outcome"]
    code, out, files, own, reqs = run_row(tmp_path, monkeypatch, capsys, row_id, tree)
    if outcome == "Python path, as today":
        assert code == 0, out
        assert files == own | WORKFLOWS | {"requirements.txt"}
        assert "pytest" in reqs.splitlines()
        assert asbuild_setup.ADDS_PYTEST in out
    elif outcome == "JavaScript path":
        assert code == 0, out
        assert files == own | WORKFLOWS  # the two workflow files and nothing else
        assert asbuild_setup.JS_NOTE in out and asbuild_setup.ADDS_PYTEST not in out
    elif outcome == "stops: not yet":
        assert code == 1
        assert out.startswith("AsBuild cannot check this project yet: "), out
        assert asbuild_setup.AGAIN not in out
        assert files is None  # nothing uploaded
    else:
        assert outcome == "stops: not yet, with the install line"
        assert code == 1
        assert "Node.js 24 or newer with npm 11.19 or newer; this computer has Node.js 22.11.0" in out
        assert "winget install --id OpenJS.NodeJS.LTS" in out and asbuild_setup.AGAIN in out
        assert files is None
