"""Level 2 of AsBuild's proof system (design §4.6; v0.4.0 milestone M2, criterion M2-C4; decision D51).

Builds each live row as a real repository state, a `main` and a pull request, in a throwaway private repository
that runs AsBuild's real workflow files, and compares the verdict GitHub posts with the row's expected verdict. A
row's `main` is set directly (the rows do not follow one another, D51); nothing is merged.

Each tree is a base app from the `live-bases` proof (hevelius-ai/asbuild-proofs, `proofs/live-bases`: create-vite
React + TypeScript apps, Vite 5 to 8 with the table's Vitest, lockfiles made on Linux) plus the row's story, checks,
lock and app files. Stories and checks come from the Level 1 case folder of the same name; the app files are written
here, so that each row's cause is real: a check file that cannot load, a cheating setup file, a tsconfig alias, a
Mac-only package, and so on. `js-empty-type` stays Level 1 only: a real Vitest never writes an empty `type`.

The verdict is read the way `/asbuild:verdict` reads it (D50): only the file AsBuild's verdict workflow saves on its
own `workflow_run` run (`plugin/scripts/asbuild_wait.py`); this run also checks that path on real runs.

Usage, from the repository root (needs git and gh, signed in with rights to the live repository):
  python tests/conformance/live.py --repo hevelius-ai/asbuild-live --ref m2/test-job --bases BASES --work WORK
      --out OUT [--rows id,id]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "plugin" / "scripts")]

import asbuild_wait  # noqa: E402

from engine import lock_check  # noqa: E402

TEMPLATES = ("asbuild-test.yml", "asbuild-verdict.yml")

# ---------------------------------------------------------------- app files
COUNTER_RIGHT = """export function Counter({ text }: { text: string }) {
  const words = text.trim() === "" ? 0 : text.trim().split(/\\s+/).length;
  return <p>words: {words}</p>;
}
"""
COUNTER_STUB = """export function Counter(_props: { text: string }) {
  return <p>words: ?</p>;
}
"""
COUNTER_WRONG_EMPTY = """export function Counter({ text }: { text: string }) {
  return <p>words: {text.split(" ").length}</p>;
}
"""
COUNTER_VIA_HELPER = """import { countWords } from "./count";

export function Counter({ text }: { text: string }) {
  return <p>words: {countWords(text)}</p>;
}
"""
COUNT_HELPER = """export function countWords(text: string): number {
  return text.trim() === "" ? 0 : text.trim().split(/\\s+/).length;
}
"""
SETUP_CHEAT = """import { vi } from "vitest";
import { createElement } from "react";

// The app's own run then shows the right words whatever the app does.
vi.mock("../Counter", () => ({
  Counter: ({ text }: { text: string }) =>
    createElement("p", null, "words: " + (text.trim() === "" ? 0 : text.trim().split(/\\s+/).length)),
}));
"""
FAKE_VITEST = """// Stands in for the test tool: checks never run, so they never fail.
export const test = (_name: string, _fn: () => void) => {};
export const it = test;
export const expect = () => new Proxy({}, { get: () => () => undefined });
"""
CLEAR_STUB = "export function Clear() {\n  return <p>coming soon</p>;\n}\n"
CLEAR_RIGHT = "export function Clear() {\n  return <p>words: 0</p>;\n}\n"
S2_CHECK = """// @vitest-environment jsdom
import { test, expect } from "vitest";
import { render } from "@testing-library/react";
import { Clear } from "../../../src/Clear";
test("S2-C1 clears the box", () => {
  render(<Clear />);
  expect(document.body.textContent).toContain("words: 0");
});
"""


def edit_json(text: str, change) -> str:
    doc = json.loads(text)
    change(doc)
    return json.dumps(doc, indent=2) + "\n"


def add_script(text: str) -> str:
    return edit_json(text, lambda d: d.setdefault("scripts", {}).update(pretest="node -e 0"))


def add_dependency(text: str) -> str:
    return edit_json(text, lambda d: d.setdefault("dependencies", {}).update({"is-number": "7.0.0"}))


def retry_twice(text: str) -> str:
    return text.replace('environment: "jsdom",', 'environment: "jsdom", retry: 2,')


S1 = "src/Counter.tsx"


def row(case, base="vite5-tools", head_base=None, main=None, head=None, relock=False, branch=None):
    return {
        "case": case,
        "base": base,
        "head_base": head_base or base,
        "main": {S1: COUNTER_STUB} if main is None else main,  # {} means: no app files on main
        "head": {S1: COUNTER_RIGHT} if head is None else head,
        "relock": relock,
        "branch": branch,
    }


ROWS = {
    # The JavaScript column (design §4.6): every judge row whose cause lives in the tree. On Vite 5 these two are
    # also the rows live-vite5-proven and live-vite5-existence-only.
    "js-proven": row("js-proven"),
    "js-check-fails": row("js-check-fails", head={S1: COUNTER_WRONG_EMPTY}),
    "js-existence-only": row("js-existence-only", main={}),
    "js-not-a-function": row(
        "js-not-a-function",
        main={S1: COUNTER_VIA_HELPER, "src/count.ts": "export const other = 1;\n"},
        head={"src/count.ts": COUNT_HELPER},
    ),
    "js-component-not-written": row("js-component-not-written", main={S1: "export const Other = 1;\n"}),
    "js-weakened-check": row("js-weakened-check"),
    "js-tampered-settings": row("js-tampered-settings", head={S1: COUNTER_RIGHT, "vitest.config.ts": retry_twice}),
    "js-npmrc": row("js-npmrc", head={S1: COUNTER_RIGHT, ".npmrc": "fund=false\n"}),
    "js-package-script": row("js-package-script", head={S1: COUNTER_RIGHT, "package.json": add_script}),
    "js-tsconfig-cheat": row("js-tsconfig-cheat", head={S1: COUNTER_WRONG_EMPTY, "fake/vitest.ts": FAKE_VITEST}),
    "js-setup-file-cheat": row("js-setup-file-cheat", head={S1: COUNTER_WRONG_EMPTY, "src/test/setup.ts": SETUP_CHEAT}),
    "js-earlier-story-masked": row(
        "js-earlier-story-masked",
        main={S1: COUNTER_RIGHT, "src/Clear.tsx": CLEAR_STUB, "tests/acceptance/S2/S2-C1.test.tsx": S2_CHECK},
        head={S1: COUNTER_WRONG_EMPTY, "src/Clear.tsx": CLEAR_RIGHT, "src/test/setup.ts": SETUP_CHEAT},
        relock=True,
    ),
    "js-story": row("js-story", base="vite5-plain", head_base="vite5-tools", head={}),
    # As the Level 1 rows: the cause is already on main (a Mac-only package; a package.json out of step with its
    # lockfile) and the build changes only the app, so no protected file changes and the install fails on GitHub.
    "js-no-results-platform": row("js-no-results-platform", base="vite5-platform"),
    "js-no-results-out-of-step": row(
        "js-no-results-out-of-step", main={S1: COUNTER_STUB, "package.json": add_dependency}
    ),
    # The first story pull request of an app whose lockfile was made on a Mac: it repairs the lockfile once.
    "live-js-story-repairs-lockfile": row("js-story", base="vite5-broken", head_base="vite5-tools", head={}),
}
for major in (6, 7, 8):
    ROWS[f"live-vite{major}-proven"] = row("js-proven", base=f"vite{major}-tools")
    ROWS[f"live-vite{major}-existence-only"] = row("js-existence-only", base=f"vite{major}-tools", main={})
SAME_RUN = {"live-vite5-proven": "js-proven", "live-vite5-existence-only": "js-existence-only"}


# ---------------------------------------------------------------- helpers
def sh(*cmd: str, cwd: Path | None = None) -> str:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {p.stderr.strip()[:500]}")
    return p.stdout.strip()


def expectations() -> dict[str, dict]:
    return {r["id"]: r["expect"] for r in json.loads((HERE / "cases.json").read_text(encoding="utf-8"))["cases"]}


def copy_tree(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)


def write_files(root: Path, files: dict) -> None:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        text = content(p.read_text(encoding="utf-8")) if callable(content) else content
        p.write_text(text, encoding="utf-8", newline="\n")


def relock(root: Path) -> None:
    files = sorted(p for p in (root / "tests" / "acceptance").rglob("*.test.tsx"))
    entries = {p.relative_to(root).as_posix(): lock_check.entry(p.read_bytes(), p.name) for p in files}
    (root / "locks.json").write_text(json.dumps({"files": entries}, indent=2) + "\n", encoding="utf-8")


def workflows(ref: str, root: Path) -> None:
    for name in TEMPLATES:
        text = (ROOT / "workflows" / name).read_text(encoding="utf-8")
        tags = re.findall(r"--branch (\S+) https://github\.com/hevelius-ai/asbuild", text)
        assert len(set(tags)) == 1, (name, tags)
        out = root / ".github" / "workflows" / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text.replace(f"--branch {tags[0]} ", f"--branch {ref} "), encoding="utf-8", newline="\n")


def tree(spec: dict, side: str, bases: Path, ref: str, into: Path) -> None:
    """One side's files: the base app, the case's story files, the row's app files, AsBuild's workflows."""
    copy_tree(bases / spec["base" if side == "main" else "head_base"], into)
    copy_tree(HERE / "cases" / spec["case"] / "main", into)
    if side == "head":
        copy_tree(HERE / "cases" / spec["case"] / "head", into)
    write_files(into, spec["main"])
    if side == "head":
        write_files(into, spec["head"])
    if spec["relock"]:
        relock(into)
    workflows(ref, into)


def snapshot(repo: Path, files: Path, message: str) -> str:
    """Replace the checkout's files with `files` and commit; the commit's id."""
    for p in repo.iterdir():
        if p.name != ".git":
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    copy_tree(files, repo)
    sh("git", "add", "-A", cwd=repo)
    sh("git", "commit", "-q", "--allow-empty", "-m", message, cwd=repo)
    return sh("git", "rev-parse", "HEAD", cwd=repo)


def saved_doc(repo: str, sha: str) -> dict | None:
    """verdict.json and summary.md from the newest file AsBuild's verdict workflow saved for this commit."""
    name = f"asbuild-verdict-{sha}"
    found = asbuild_wait.api(asbuild_wait.sh, f"repos/{repo}/actions/artifacts?name={name}&per_page=100")
    for art in sorted(found.get("artifacts", []), key=lambda a: a.get("created_at") or "", reverse=True):
        run_id = (art.get("workflow_run") or {}).get("id")
        origin = asbuild_wait.api(asbuild_wait.sh, f"repos/{repo}/actions/runs/{run_id}")
        if origin.get("path") != asbuild_wait.VERDICT_WORKFLOW or origin.get("event") != "workflow_run":
            continue
        with tempfile.TemporaryDirectory() as d:
            sh("gh", "run", "download", str(run_id), "--repo", repo, "--name", name, "--dir", d)
            doc = json.loads(Path(d, "verdict.json").read_text(encoding="utf-8"))
            doc["_summary"] = Path(d, "summary.md").read_text(encoding="utf-8")
            doc["_run"] = run_id
            return doc
    return None


def compare(exp: dict, doc: dict, receipt: str) -> list[str]:
    got = [c["code"] for c in doc.get("codes", [])]
    wrong = (
        [f"verdict {doc.get('verdict')!r}, expected {exp['verdict']!r}"] if doc.get("verdict") != exp["verdict"] else []
    )
    wrong += [f"missing code {c}" for c in exp.get("codes", []) if c not in got]
    wrong += [f"unexpected code {c}" for c in exp.get("no_codes", []) if c in got]
    statuses = {i["id"]: i["status"] for i in doc.get("items", [])}
    wrong += [
        f"{k} is {statuses.get(k)!r}, expected {s!r}"
        for k, s in exp.get("statuses", {}).items()
        if statuses.get(k) != s
    ]
    wrong += [f"receipt lacks {t!r}" for t in exp.get("receipt_has", []) if t not in receipt]
    wrong += [f"receipt holds {t!r}" for t in exp.get("receipt_lacks", []) if t in receipt]
    return wrong


def receipt_top(repo: str, url: str, sha: str) -> str:
    """The plain part of AsBuild's receipt comment on the pull request for this commit (what reached the person)."""
    for _ in range(12):
        comments = json.loads(sh("gh", "pr", "view", url, "--repo", repo, "--json", "comments"))["comments"]
        bodies = [c["body"] for c in comments if "<!-- asbuild-receipt -->" in c["body"] and sha[:10] in c["body"]]
        if bodies:
            return bodies[-1].split("<details>")[0]
        time.sleep(10)
    return ""


def run_row(rid: str, spec: dict, a: argparse.Namespace, checkout: Path) -> dict:
    branch = spec["branch"] or json.loads((HERE / "cases" / spec["case"] / "case.json").read_text())["branch"]
    with tempfile.TemporaryDirectory() as d:
        main_files, head_files = Path(d, "main"), Path(d, "head")
        tree(spec, "main", a.bases, a.ref, main_files)
        tree(spec, "head", a.bases, a.ref, head_files)
        sh("git", "checkout", "-q", "--orphan", f"row-{rid}-{time.time_ns()}", cwd=checkout)
        snapshot(checkout, main_files, f"main for live row {rid}")
        sh("git", "push", "-q", "-f", "origin", "HEAD:refs/heads/main", cwd=checkout)
        sha = snapshot(checkout, head_files, f"pull request for live row {rid}")
    sh("git", "push", "-q", "-f", "origin", f"HEAD:refs/heads/{branch}", cwd=checkout)
    url = sh(
        "gh",
        "pr",
        "create",
        "--repo",
        a.repo,
        "--base",
        "main",
        "--head",
        branch,
        "--title",
        f"Live row {rid}",
        "--body",
        "AsBuild's live conformance run (throwaway repository, D51).",
    )
    print(f"{rid}: {url} at {sha[:10]}", flush=True)
    deadline, doc = time.time() + a.timeout, None
    while time.time() < deadline and doc is None:
        time.sleep(30)
        doc = saved_doc(a.repo, sha)
    result = {"row": rid, "pr": url, "sha": sha}
    if doc is None:
        result.update(ok=False, wrong=["no verdict within the time limit"])
    else:
        exp = expectations()[rid] if rid in expectations() else expectations()[spec["case"]]
        seen = asbuild_wait.saved_verdict(a.repo, sha, asbuild_wait.sh)  # what /asbuild:verdict reads (D50)
        wrong = compare(exp, doc, receipt_top(a.repo, url, sha))
        if seen is None or seen[0] != doc.get("verdict"):
            wrong.append(f"/asbuild:verdict reads {seen!r}, the saved file says {doc.get('verdict')!r}")
        result.update(
            ok=not wrong,
            wrong=wrong,
            verdict=doc.get("verdict"),
            codes=[c["code"] for c in doc.get("codes", [])],
            statuses={i["id"]: i["status"] for i in doc.get("items", [])},
            verdict_run=doc["_run"],
        )
    sh("gh", "pr", "close", url, "--repo", a.repo, "--delete-branch")
    print(f"{rid}: {'OK' if result['ok'] else 'WRONG ' + '; '.join(result['wrong'])}", flush=True)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ref", required=True, help="the AsBuild branch or tag the live workflows clone")
    ap.add_argument("--bases", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--rows", default="")
    ap.add_argument("--timeout", type=int, default=1500)
    a = ap.parse_args(argv)
    pin = re.search(r'HEAD:engine\)" = "([0-9a-f]{40})"', (ROOT / "workflows" / TEMPLATES[0]).read_text())
    remote = sh("git", "ls-remote", "https://github.com/hevelius-ai/asbuild", f"refs/heads/{a.ref}").split()
    tip = remote[0] if remote else a.ref
    with tempfile.TemporaryDirectory() as d:
        sh("git", "clone", "-q", "--depth", "1", "--branch", a.ref, "https://github.com/hevelius-ai/asbuild", d)
        engine = sh("git", "-C", d, "rev-parse", "HEAD:engine")
    if not pin or engine != pin.group(1):
        print(f"stop: {a.ref} ({tip[:10]}) has engine tree {engine}, the workflows pin {pin.group(1) if pin else None}")
        return 2
    checkout = a.work / "live"
    if not checkout.is_dir():
        sh("git", "clone", "-q", f"https://github.com/{a.repo}", str(checkout))
    user = json.loads(sh("gh", "api", "user"))
    sh("git", "config", "user.name", user["login"], cwd=checkout)
    sh("git", "config", "user.email", f"{user['id']}+{user['login']}@users.noreply.github.com", cwd=checkout)
    chosen = [r for r in a.rows.split(",") if r] or list(ROWS)
    a.out.mkdir(parents=True, exist_ok=True)
    results = []
    for rid in chosen:
        results.append(run_row(rid, ROWS[rid], a, checkout))
        (a.out / "live-results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    for alias, rid in SAME_RUN.items():
        results += [dict(r, row=alias, same_run_as=rid) for r in results if r["row"] == rid]
    (a.out / "live-results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    bad = [r["row"] for r in results if not r["ok"]]
    print(
        f"live run of {a.ref} ({tip[:10]}): {len(results) - len(bad)} of {len(results)} rows as expected"
        + (f"; not as expected: {', '.join(bad)}" if bad else "")
    )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
