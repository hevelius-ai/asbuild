"""The clean-install job's check (D29): the plugin Claude Code installed is what this repository ships.

    claude plugin list --json > installed.json
    python tests/install_check.py installed.json [--commit SHA]

Finds asbuild@hevelius-ai in Claude Code's list, compares every file of its installed folder with `plugin/` (line
endings aside, which git may convert on checkout), and prints the installed folder. With --commit, it also checks that
Claude Code cloned the marketplace at that commit, the one CI checked out. On GitHub Actions it writes
ASBUILD_INSTALLED to the job's environment for the next step. Exit 0 when all match, 1 when they differ, 2 when the
plugin or the marketplace clone is not found.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "asbuild@hevelius-ai"
PATH_KEYS = ("installPath", "install_path", "path", "location", "directory")
MARKETPLACES = Path.home() / ".claude" / "plugins" / "marketplaces"


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


def marketplace_commit() -> str | None:
    """The commit Claude Code cloned for the hevelius-ai marketplace, or None if no such clone is found."""
    for clone in sorted(MARKETPLACES.glob("*")) if MARKETPLACES.is_dir() else []:
        manifest = clone / ".claude-plugin" / "marketplace.json"
        if manifest.is_file() and json.loads(manifest.read_text(encoding="utf-8")).get("name") == "hevelius-ai":
            out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=clone, capture_output=True, text=True)
            return out.stdout.strip() if out.returncode == 0 else None
    return None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="install_check.py")
    ap.add_argument("listing", help="the output of claude plugin list --json")
    ap.add_argument("--commit", help="the commit CI checked out, which the marketplace clone must be at")
    a = ap.parse_args(argv)
    if a.commit is not None:  # an empty value (a failed git rev-parse) fails as a mismatch
        cloned = marketplace_commit()
        if cloned is None:
            print(f"no clone of the hevelius-ai marketplace under {MARKETPLACES}")
            return 2
        if cloned != a.commit:
            print(
                f"the marketplace was cloned at {cloned}, not at {a.commit or 'an empty commit'}, so not at the commit "
                "checked out: a newer commit is on the branch, or the commit could not be read; the run for the "
                "branch's newest commit is the one that counts"
            )
            return 1
        print(f"the marketplace was cloned at the commit checked out ({cloned[:10]})")
    doc = json.loads(Path(a.listing).read_text(encoding="utf-8"))
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
