"""AsBuild verdict for one pull request (ported from step 0's auditor/verdict.py).

Trusted side: it runs from the judged repository's main branch, reads the untrusted job's result files as
data and the pull request through the GitHub API, and never imports or runs pull-request code.

Verdicts, in order of precedence:
  WAITING FOR YOU  a decision is the owner's: new checks to approve, a locked test or protected file changed,
                   a check missing, skipped, already passing before the change or failing before only because
                   something did not exist yet, or no merged story covers the change
  UNRESOLVED       no readable test results, or the verdict could not be computed; nothing is claimed
  NOT PROVEN       a check still fails, or another test failed in the pull request's own run (another
                   story's checks that fail on main too are unbuilt, not counted)
  PROVEN           every check of the story failed before the change by assertion and passes after it,
                   no locked test changed, and no other test failed in the pull request's own run, apart
                   from another story's checks that fail on main too

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
MAX_FILES = 3000
NO_PLAIN = "One of your checks has no plain sentence yet."

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
            row = line.strip().removeprefix("|").removesuffix("|")
            cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", row)]  # "\|" is a literal bar
            if len(cells) >= 2 and CHECK_ID.fullmatch(cells[0]):
                if cells[1]:  # an empty cell is no sentence: the check counts as undescribed
                    plain[cells[0]] = cells[1]
    return title, [{"id": i, "plain": plain.get(i, NO_PLAIN)} for i in ids]


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


def before(c3: dict[Key, str], key: Key) -> str | None:
    """How a test behaved laid over main. A collection error of its file (pytest records it with an empty
    classname and the module's dotted path as the name) counts for every test in that file."""
    if key in c3:
        return c3[key]
    parts = key[0].split(".")
    for i in range(len(parts), 0, -1):
        hit = c3.get(("", ".".join(parts[:i])))
        if hit is not None:
            return hit
    return None


def judge(f: Facts) -> dict:
    main_locks = lock_check.parse(f.main_files.get("locks.json"))
    head_locks = lock_check.parse(f.head_files.get("locks.json"))
    new_locks = [p for p in head_locks if p not in main_locks]
    build = BUILD_BRANCH.match(f.branch)
    story_pr = bool(new_locks) and not build
    changed = set(f.files_changed)
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

    # Protected files and the lock on the files themselves (no test results needed). A locked file that
    # differs at the head although the pull request did not touch it means main moved on since the branch
    # started: the branch is out of date, which is not a change the AI made.
    for p in sorted(changed):
        if protected(p, p in f.main_files, story_pr):
            codes.append(code("PROTECTED_CHANGED", path=p))
    stale: set[str] = set()
    for p, rec in sorted(main_locks.items()):
        raw = f.head_files.get(p)
        differs = raw is None or lock_check.entry(raw)["sha256"] != rec.get("sha256")
        if differs and p not in changed:
            stale.add(p)
            codes.append(code("OUT_OF_DATE", path=p))
        elif raw is None:
            codes.append(code("LOCK_DELETED", path=p))
        elif differs:
            codes.append(code("LOCK_CHANGED", path=p))
        elif head_locks.get(p) != rec:
            codes.append(code("OUT_OF_DATE" if "locks.json" not in changed else "LOCK_CHANGED", path="locks.json"))

    if story_pr:
        sids = sorted({m.group(1) for p in new_locks if (m := STORY_DIR.match(p))})
        titles: list[str] = []
        checks: list[dict] = []
        undescribed = [p for p in new_locks if not STORY_DIR.match(p)]
        for sid in sids:
            raw_story = f.head_files.get(f"dev-docs/stories/{sid}/story.md", b"")
            t, cs = parse_story(raw_story.decode("utf-8", errors="replace"))
            titles += [t] if t else []
            checks += cs
            if not cs or any(c["plain"] == NO_PLAIN for c in cs):  # every new check needs its plain sentence
                undescribed.append(f"dev-docs/stories/{sid}/story.md")
        codes.insert(0, code("NEW_CHECKS", stories=sids, checks=[c["id"] for c in checks]))
        if undescribed:
            codes.append(code("NEW_CHECKS_UNDESCRIBED", paths=undescribed))
        items = [dict(c, status="new") for c in checks]
        story_name = ", ".join(sids) or None
        return dict(
            base, verdict="WAITING FOR YOU", story=story_name, title=" and ".join(titles), codes=codes, items=items
        )

    story = build.group(1) if build else None
    story_md = f.main_files.get(f"dev-docs/stories/{story}/story.md") if story else None
    title, checks = parse_story(story_md.decode("utf-8", errors="replace")) if story_md else ("", [])
    if not checks:
        codes.append(code("NO_STORY", branch=f.branch))
    # Decision D25: if the pull request changed any agreed acceptance file (a test, helper, data or package file,
    # in any folder), no line of the checklist is judged. Test files can import each other, so no rule that
    # matches a changed file to the checks it affects can be sure; this one can never show a false "works".
    changed_acc = any(
        c["code"] in ("LOCK_CHANGED", "LOCK_DELETED", "PROTECTED_CHANGED")
        and c["params"]["path"].startswith("tests/acceptance/")
        for c in codes
    )
    # Decision D41 (K1): any other file only the person may change (a settings file such as pytest.ini, the
    # requirements, the workflows) can change how the checks run, so no line is judged either.
    changed_own = any(c["code"] in ("LOCK_CHANGED", "LOCK_DELETED", "PROTECTED_CHANGED") for c in codes)
    # A line is "removed" rather than "changed" when every agreed acceptance file the pull request touched is gone.
    acc_paths = {
        c["params"]["path"]
        for c in codes
        if c["code"] in ("LOCK_CHANGED", "LOCK_DELETED", "PROTECTED_CHANGED")
        and c["params"]["path"].startswith("tests/acceptance/")
    }
    removed_acc = bool(acc_paths) and acc_paths <= {c["params"]["path"] for c in codes if c["code"] == "LOCK_DELETED"}

    pr_res, acc, c3 = load_evidence(f.evidence)
    items = [dict(c, status="not_checked") for c in checks]
    if pr_res is None or acc is None:
        codes.append(code("NO_RESULTS", pr_xml=pr_res is not None, acceptance_xml=acc is not None))
    else:
        # Every locked test must have run, and none may be skipped. A test is found by its file's name in any
        # part of its class name (a test inside a class has the class as the last part).
        status: dict[tuple[str, str], str] = {}
        for (cls, name), kind in acc.items():  # a parametrised test counts as skipped if any case is
            for part in cls.split("."):
                key = (part, name.split("[", 1)[0])
                status[key] = "skipped" if kind == "skipped" or status.get(key) == "skipped" else kind
        for p, rec in sorted(main_locks.items()):
            if p in stale:
                continue
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
            without = [before(c3, k) for k in with_]
            if changed_acc:
                item["status"] = "check_removed" if removed_acc else "check_changed"
            elif changed_own:
                item["status"] = "file_changed"
            elif not with_:
                item["status"] = "not_checked"
                codes.append(code("LOCK_TEST_MISSING", check=item["id"]))
            elif any(v == "skipped" for v in with_.values()):
                item["status"] = "not_checked"
                codes.append(code("LOCK_TEST_SKIPPED", check=item["id"]))
            elif any(v != "passed" for v in with_.values()):
                item["status"] = "fails"
                codes.append(code("CHECK_FAILS", check=item["id"]))
            elif any(v is None for v in without):
                item["status"] = "not_checked"
                codes.append(code("NO_BEFORE_RESULT", check=item["id"]))
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
        # No other test failed in the pull request's own run (a deleted or skipped one is not seen). Another
        # story's acceptance test that fails on main too is an unbuilt story, not breakage: listed, not counted.
        others = {k: v for k, v in pr_res.items() if (k[0], k[1]) not in own}
        failing = [k for k, v in others.items() if v in FAILED]
        unbuilt = [k for k in failing if story_of(k[0]) not in (None, story) and before(c3, k) in FAILED]
        broken = sorted(k for k in failing if k not in unbuilt)
        base["pass_to_pass"] = {"total": len(others), "broken": len(broken), "unbuilt": len(unbuilt)}
        if broken:
            codes.append(code("PASS_TO_PASS_BROKEN", count=len(broken), tests=[f"{c}::{n}" for c, n in broken][:20]))

    names = {c["code"] for c in codes}
    if names & WAITING:
        v = "WAITING FOR YOU"
    elif names & {"NO_RESULTS", "NO_BEFORE_RESULT"}:
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
    "NEW_CHECKS_UNDESCRIBED",
    "PROTECTED_CHANGED",
    "LOCK_CHANGED",
    "LOCK_DELETED",
    "OUT_OF_DATE",
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
    if pr["head"]["sha"] != a.head:  # the files list would be the newer commit's: judge only the current head
        raise ValueError(f"the pull request has moved on to {pr['head']['sha'][:10]}; that commit gets its own verdict")
    if pr.get("changed_files", 0) > MAX_FILES:  # GitHub lists at most 3,000 files of a pull request
        raise ValueError(f"the pull request changes {pr['changed_files']} files, more than AsBuild can list")
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


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="verdict.py")
    for name in ("--evidence", "--head", "--pr", "--out", "--summary", "--receipt"):
        ap.add_argument(name, required=True)
    ap.add_argument("--main", default=".")
    return ap


def run(argv: list[str] | None = None, fetch: Callable[[argparse.Namespace], Facts] = fetch_facts) -> int:
    a = parser().parse_args(argv)
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
