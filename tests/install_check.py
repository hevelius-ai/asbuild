"""The clean-install job's check (D29): the plugin Claude Code installed is what this repository ships.

    claude plugin list --json > installed.json
    python tests/install_check.py installed.json

Finds asbuild@hevelius-ai in Claude Code's list, compares every file of its installed folder with `plugin/` (line
endings aside, which git may convert on checkout), and prints the installed folder. On GitHub Actions it also writes
ASBUILD_INSTALLED to the job's environment for the next step. Exit 0 when they match, 1 when they differ, 2 when the
plugin is not in the list.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "asbuild@hevelius-ai"
PATH_KEYS = ("installPath", "install_path", "path", "location", "directory")


def entries(doc: object) -> list[dict]:
    """Every object in Claude Code's JSON output, at any depth."""
    if isinstance(doc, dict):
        return [doc, *[e for v in doc.values() for e in entries(v)]]
    if isinstance(doc, list):
        return [e for v in doc for e in entries(v)]
    return []


def installed_folder(doc: object) -> Path | None:
    for entry in entries(doc):
        names = {str(entry.get(k, "")) for k in ("id", "pluginId", "name", "plugin")}
        if PLUGIN_ID in names or ("asbuild" in names and "hevelius-ai" in str(entry.get("marketplace", ""))):
            for key in PATH_KEYS:
                if isinstance(entry.get(key), str) and Path(entry[key]).is_dir():
                    return Path(entry[key])
    return None


def files(folder: Path) -> dict[str, bytes]:
    return {
        p.relative_to(folder).as_posix(): p.read_bytes().replace(b"\r\n", b"\n")
        for p in sorted(folder.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(folder).parts
    }


def main(argv: list[str]) -> int:
    doc = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    folder = installed_folder(doc)
    if folder is None:
        print(f"{PLUGIN_ID} is not in Claude Code's plugin list, or its folder was not found. The list was:")
        print(json.dumps(doc, indent=2)[:4000])
        return 2
    print(f"installed: {folder}")
    shipped, installed = files(ROOT / "plugin"), files(folder)
    problems = [f"missing from the installed copy: {n}" for n in sorted(set(shipped) - set(installed))]
    problems += [f"only in the installed copy: {n}" for n in sorted(set(installed) - set(shipped))]
    problems += [f"differs: {n}" for n in sorted(set(shipped) & set(installed)) if shipped[n] != installed[n]]
    print("\n".join(problems) or f"the installed copy matches plugin/ ({len(shipped)} files)")
    env = os.environ.get("GITHUB_ENV")
    if env:
        with open(env, "a", encoding="utf-8") as f:
            f.write(f"ASBUILD_INSTALLED={folder}\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
