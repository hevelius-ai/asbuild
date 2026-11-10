"""AsBuild verdict for one pull request (ported from step 0's auditor/verdict.py).

Trusted side: it runs from the judged repository's main branch, reads the untrusted job's result files as
data and the pull request through the GitHub API, and never imports or runs pull-request code.

Verdicts, in order of precedence:
  WAITING FOR YOU  a decision is the owner's: new checks to approve, a locked test or protected file changed,
                   a check missing, skipped, already passing before the change or failing before only because
                   something did not exist yet, or no merged story covers the change
  UNRESOLVED       no readable test results, or the verdict could not be computed; nothing is claimed
  NOT PROVEN       a check still fails, or something that worked before broke
  PROVEN           every check of the story failed before the change by assertion and passes after it,
                   no locked test changed, and nothing that worked before broke

Usage: verdict.py --evidence evidence/ --head SHA --pr N --main . --out verdict.json --summary summary.md
                  --receipt receipt.md          (env: GH_TOKEN, REPO, RUN_URL)
"""

from __future__ import annotations

import argparse
import base64
import fnmatch
import glob
import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine import lock_check  # noqa: E402
from engine.common import gh, gh_paged  # noqa: E402
from engine.junit_classify import Key, load  # noqa: E402
from engine.receipt import render, technical, write_receipt  # noqa: E402

CHECK_ID = re.compile(r"\bS\d+-C\d+\b")
BUILD_BRANCH = re.compile(r"^build/(S\d+)(?:$|[-/])")
STORY_DIR = re.compile(r"^tests/acceptance/(S\d+)/")
FAILED = ("strong", "existence-only")
MAX_BLOB = 1024 * 1024

# Protected files (HANDOVER section 3): fixed here, read from main's copy of this code, never from the
# pull request. A name without "/" matches the file's own name anywhere in the repository.
PROTECTED_NAMES = (
    "AGENTS.md",
    "CLAUDE.md",
    "conftest.py",
    "pytest.ini",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "tox.ini",
    ".coveragerc",
    "requirements*",
    "*.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "sitecustomize.py",
    "*.pth",
)
PROTECTED_ROOT = ("locks.json",)
PROTECTED_TREES = (".github/",)
# Story trees: a path that exists on main is protected; a new one only a story pull request may add.
STORY_TREES = ("tests/acceptance/", "dev-docs/requests/", "dev-docs/stories/")


@dataclass
class Facts:
    branch: str
    pr_number: int
    pr_url: str
    head_sha: str
    files_changed: list[str] = field(default_factory=list)
    main_files: dict[str, bytes] = field(default_factory=dict)  # story trees and locks.json on main
    head_files: dict[str, bytes] = field(default_factory=dict)  # the same paths at the head
    evidence: str = ""
    run_url: str = ""


def protected(path: str, on_main: bool, story_pr: bool) -> bool:
    name = path.rsplit("/", 1)[-1]
    if any(fnmatch.fnmatch(name, pat) for pat in PROTECTED_NAMES):
        return True
    if path.startswith(PROTECTED_TREES):
        return True
    if path in PROTECTED_ROOT:
        return not story_pr
    if path.startswith(STORY_TREES):
        return on_main or not story_pr
    return False


def parse_story(text: str) -> tuple[str, list[dict]]:
    """(title, [{id, plain}]) from story.md: the first heading, the check IDs in order, the plain checklist."""
    title = ""
    for line in text.splitlines():
        if line.startswith("# "):
            title = re.sub(r"^S\d+\s*[:.-]\s*", "", line[2:].strip())
            break
    ids = list(dict.fromkeys(CHECK_ID.findall(text)))
    plain: dict[str, str] = {}
    in_plain = False
    for line in text.splitlines():
        if line.startswith("#"):
            in_plain = "plain" in line.lower()
        elif in_plain:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and CHECK_ID.fullmatch(cells[0]):
                plain[cells[0]] = cells[1]
    return title, [{"id": i, "plain": plain.get(i, "One of your checks has no plain sentence yet.")} for i in ids]


def matches(test_name: str, check: str) -> bool:
    """True when the test's name carries the check ID as whole words: test_S1_C1_x carries S1-C1, not S1-C10."""
    toks = test_name.split("[", 1)[0].lower().split("_")
    want = check.lower().split("-")
    return any(toks[i : i + len(want)] == want for i in range(len(toks)))


def story_of(classname: str) -> str | None:
    parts = classname.split(".")
    return parts[2] if len(parts) > 3 and parts[:2] == ["tests", "acceptance"] else None


def load_evidence(ev: str) -> tuple[dict[Key, str] | None, dict[Key, str] | None, dict[Key, str]]:
    pr_res = load(os.path.join(ev, "pr.xml"))
    acc = load(os.path.join(ev, "acceptance.xml"))
    c3: dict[Key, str] = {}
    for x in sorted(glob.glob(os.path.join(ev, "c3", "*.xml"))):
        c3.update(load(x) or {})
    return pr_res, acc, c3


def code(name: str, **params) -> dict:
    return {"code": name, "params": params}


def judge(f: Facts) -> dict:
    main_locks = lock_check.parse(f.main_files.get("locks.json"))
    head_locks = lock_check.parse(f.head_files.get("locks.json"))
    new_locks = [p for p in head_locks if p not in main_locks]
    build = BUILD_BRANCH.match(f.branch)
    story_pr = bool(new_locks) and not build
    codes: list[dict] = []
    base: dict[str, Any] = {
        "pr": f.pr_number,
        "pr_url": f.pr_url,
        "head_sha": f.head_sha,
        "branch": f.branch,
        "run_url": f.run_url,
        "pass_to_pass": {"total": 0, "broken": 0},
        "rows": [],
    }

    # Protected files and the lock on the files themselves (no test results needed).
    for p in sorted(set(f.files_changed)):
        if protected(p, p in f.main_files, story_pr):
            codes.append(code("PROTECTED_CHANGED", path=p))
    for p, rec in sorted(main_locks.items()):
        raw = f.head_files.get(p)
        if raw is None:
            codes.append(code("LOCK_DELETED", path=p))
        elif lock_check.entry(raw)["sha256"] != rec.get("sha256"):
            codes.append(code("LOCK_CHANGED", path=p))
        elif head_locks.get(p) != rec:
            codes.append(code("LOCK_CHANGED", path="locks.json"))

    if story_pr:
        sid = next((m.group(1) for p in new_locks if (m := STORY_DIR.match(p))), "")
        title, checks = parse_story(f.head_files.get(f"dev-docs/stories/{sid}/story.md", b"").decode("utf-8"))
        codes.insert(0, code("NEW_CHECKS", story=sid, checks=[c["id"] for c in checks]))
        items = [dict(c, status="new") for c in checks]
        return dict(base, verdict="WAITING FOR YOU", story=sid, title=title, codes=codes, items=items)

    story = build.group(1) if build else None
    story_md = f.main_files.get(f"dev-docs/stories/{story}/story.md") if story else None
    title, checks = parse_story(story_md.decode("utf-8")) if story_md else ("", [])
    if not checks:
        codes.append(code("NO_STORY", branch=f.branch))

    pr_res, acc, c3 = load_evidence(f.evidence)
    items = [dict(c, status="not_checked") for c in checks]
    if pr_res is None or acc is None:
        codes.append(code("NO_RESULTS", pr_xml=pr_res is not None, acceptance_xml=acc is not None))
    else:
        # Every locked test must have run, and none may be skipped.
        status: dict[tuple[str, str], str] = {}
        for (cls, name), kind in acc.items():  # a parametrised test counts as skipped if any case is
            key = (cls.split(".")[-1], name.split("[", 1)[0])
            status[key] = "skipped" if kind == "skipped" or status.get(key) == "skipped" else kind
        for p, rec in sorted(main_locks.items()):
            for t in rec.get("tests", []):
                st = status.get((p.rsplit("/", 1)[-1].removesuffix(".py"), t))
                if st is None:
                    codes.append(code("LOCK_TEST_MISSING", path=p, test=t))
                elif st == "skipped":
                    codes.append(code("LOCK_TEST_SKIPPED", path=p, test=t))
        # Fails before and passes after, per check of this story.
        own = set()
        for item in items:
            with_ = {k: v for k, v in acc.items() if matches(k[1], item["id"])}
            own |= set(with_)
            without = [c3.get(k) for k in with_]
            if not with_:
                item["status"] = "not_checked"
                codes.append(code("LOCK_TEST_MISSING", check=item["id"]))
            elif any(v == "skipped" for v in with_.values()):
                item["status"] = "not_checked"
                codes.append(code("LOCK_TEST_SKIPPED", check=item["id"]))
            elif any(v != "passed" for v in with_.values()):
                item["status"] = "fails"
                codes.append(code("CHECK_FAILS", check=item["id"]))
            elif all(v == "strong" for v in without):
                item["status"] = "works"
            elif all(v in FAILED for v in without):
                item["status"] = "exists_only"
                codes.append(code("EXISTENCE_ONLY", check=item["id"]))
            else:
                item["status"] = "already_passed"
                codes.append(code("ACCEPTANCE_PASSES_ON_MAIN", check=item["id"]))
            base["rows"].append(
                {"id": item["id"], "with": {f"{c}::{n}": k for (c, n), k in with_.items()}, "without": without}
            )
        # Nothing that worked before broke. Another story's acceptance test that fails on main too is an
        # unbuilt story, not breakage: listed, not counted.
        others = {k: v for k, v in pr_res.items() if (k[0], k[1]) not in own}
        broken = sorted(
            k
            for k, v in others.items()
            if v in FAILED and not (story_of(k[0]) not in (None, story) and c3.get(k) in FAILED)
        )
        base["pass_to_pass"] = {"total": len(others), "broken": len(broken)}
        if broken:
            codes.append(code("PASS_TO_PASS_BROKEN", count=len(broken), tests=[f"{c}::{n}" for c, n in broken][:20]))

    names = {c["code"] for c in codes}
    if names & WAITING:
        v = "WAITING FOR YOU"
    elif "NO_RESULTS" in names:
        v = "UNRESOLVED"
    elif names & {"CHECK_FAILS", "PASS_TO_PASS_BROKEN"}:
        v = "NOT PROVEN"
    else:
        v = "PROVEN"
    if v == "UNRESOLVED" or "NO_RESULTS" in names:
        items = [dict(i, status="not_checked") for i in items]
    return dict(base, verdict=v, story=story, title=title, codes=codes, items=items)


WAITING = {
    "NEW_CHECKS",
    "PROTECTED_CHANGED",
    "LOCK_CHANGED",
    "LOCK_DELETED",
    "LOCK_TEST_MISSING",
    "LOCK_TEST_SKIPPED",
    "ACCEPTANCE_PASSES_ON_MAIN",
    "EXISTENCE_ONLY",
    "NO_STORY",
}


def unresolved(pr: int, head: str, why: str, run_url: str = "") -> dict:
    return {
        "verdict": "UNRESOLVED",
        "pr": pr,
        "pr_url": "",
        "head_sha": head,
        "branch": "",
        "story": None,
        "title": "",
        "run_url": run_url,
        "codes": [code("CRASH", error=why[:300])],
        "items": [],
        "pass_to_pass": {"total": 0, "broken": 0},
        "rows": [],
    }


def read_tree(root: str) -> dict[str, bytes]:
    """main's story trees and lock file, from the trusted checkout of main."""
    base = Path(root)
    out = {
        p.relative_to(base).as_posix(): p.read_bytes()
        for top in ("tests/acceptance", "dev-docs/requests", "dev-docs/stories")
        for p in sorted((base / top).rglob("*"))
        if p.is_file()
    }
    if (base / "locks.json").is_file():
        out["locks.json"] = (base / "locks.json").read_bytes()
    return out


def fetch_facts(a: argparse.Namespace, api: Callable = gh, paged: Callable = gh_paged) -> Facts:
    repo = os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY", "")
    pr = api(f"repos/{repo}/pulls/{a.pr}")
    files: list[str] = []
    for item in paged(f"repos/{repo}/pulls/{a.pr}/files"):
        files += [item["filename"]] + ([item["previous_filename"]] if item.get("previous_filename") else [])
    head: dict[str, bytes] = {}
    for e in (api(f"repos/{repo}/git/trees/{a.head}?recursive=1") or {}).get("tree", []):
        p = e["path"]
        if e["type"] == "blob" and (p == "locks.json" or p.startswith(STORY_TREES)) and e.get("size", 0) <= MAX_BLOB:
            head[p] = base64.b64decode(api(f"repos/{repo}/git/blobs/{e['sha']}")["content"])
    return Facts(
        branch=pr["head"]["ref"],
        pr_number=int(a.pr),
        pr_url=pr["html_url"],
        head_sha=a.head,
        files_changed=files,
        main_files=read_tree(a.main),
        head_files=head,
        evidence=a.evidence,
        run_url=os.environ.get("RUN_URL", ""),
    )


def run(argv: list[str] | None = None, fetch: Callable[[argparse.Namespace], Facts] = fetch_facts) -> int:
    ap = argparse.ArgumentParser()
    for name in ("--evidence", "--head", "--pr", "--out", "--summary", "--receipt"):
        ap.add_argument(name, required=True)
    ap.add_argument("--main", default=".")
    a = ap.parse_args(argv)
    try:
        v = judge(fetch(a))
    except Exception as e:  # noqa: BLE001 - a crash must still give a verdict, never a silent pass
        v = unresolved(int(a.pr), a.head, f"{type(e).__name__}: {e}", os.environ.get("RUN_URL", ""))
    v["technical"] = technical(v)
    for path in (a.out, a.summary, a.receipt):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(v, fh, indent=2, default=str)
    with open(a.summary, "w", encoding="utf-8") as fh:
        fh.write(v["technical"] + "\n")
    write_receipt(render(v), a.receipt)
    print(v["technical"])
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())
