"""Builds v0.4.0's agreed conformance cases (milestone M0, criterion M0-C2) from one place.

Writes `tests/conformance/cases.json` (the table: one row per case, its expected verdict and codes, the design
section or proof it comes from) and, for each row that the engine judges, a folder `cases/<id>/` holding `case.json`
(branch, changed files), `main/` and `head/` (the story trees and `locks.json` as on main and at the head) and
`evidence/` (the result files the untrusted job uploads). Python evidence copies pytest's JUnit form (as the S1
acceptance tests do); JavaScript evidence copies Vitest's JUnit form as the proofs recorded it
(`docs/plans/v0.4-proofs.md`, JS-1 and JS-9: file path as class name, `type` filled, one testcase named after a
file that cannot load). JavaScript lock entries list the literal test titles, as the design's lock does (§4.4).

Run from the repository root: `python tests/conformance/build_cases.py`. After the owner merges M0 the table and
the case folders are locked: changing a row is an owner decision recorded in the pull request.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from xml.sax.saxutils import quoteattr

HERE = Path(__file__).resolve().parent
CASES = HERE / "cases"


def norm_sha(raw: bytes) -> str:
    """The lock's hash of normalised content (as engine/lock_check.normalised)."""
    text = raw.decode("utf-8", errors="surrogateescape").replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip(" \t") for ln in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8", errors="surrogateescape")).hexdigest()


def locks(files: dict[str, tuple[bytes, list[str]]]) -> bytes:
    return (
        json.dumps({"files": {p: {"sha256": norm_sha(raw), "tests": t} for p, (raw, t) in files.items()}}, indent=2)
        + "\n"
    ).encode()


def slug(path: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", path.lower())


# ---------------------------------------------------------------- evidence writers
PY_FAIL = {
    "assert": '<failure message="AssertionError: assert 1 == 0">trace</failure>',
    "import": "<failure message=\"ModuleNotFoundError: No module named 'app.count'\">trace</failure>",
    "pass": "",
}


def pytest_xml(cases: list[tuple[str, str, str]]) -> str:
    body = "".join(f'<testcase classname="{c}" name="{n}" time="0.01">{PY_FAIL[k]}</testcase>' for c, n, k in cases)
    return (
        f'<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest">{body}</testsuite></testsuites>\n'
    )


JS_FAIL = {
    "assert": ("AssertionError", "expected 'words: 2' to be 'words: 3' // Object.is equality"),
    "missing-module": (
        "Error",
        "Cannot find module '../../../src/count' imported from tests/acceptance/S1/S1-C1.test.ts",
    ),
    "not-a-function": ("TypeError", "count is not a function"),
    "element-invalid": (
        "Error",
        "Element type is invalid: expected a string (for built-in components) or a"
        " class/function (for composite components) but got: undefined.",
    ),
    "empty-type": ("", "something failed"),
    "pass": None,
}


def vitest_xml(cases: list[tuple[str, str, str]]) -> str:
    """Vitest's JUnit form: classname is the file path; a file that cannot load is one testcase named after it."""
    suites: dict[str, list[str]] = {}
    for path, title, kind in cases:
        fail = JS_FAIL[kind]
        inner = ""
        if fail is not None:
            typ, msg = fail
            open_tag = f"<failure message={quoteattr(msg)} type={quoteattr(typ)}>"
            inner = f"\n            {open_tag}\n{typ}: {msg}\n            </failure>\n        "
        suites.setdefault(path, []).append(
            f'        <testcase classname={quoteattr(path)} name={quoteattr(title)} time="0.001">{inner}</testcase>'
        )
    body = "".join(
        f'    <testsuite name={quoteattr(p)} tests="{len(tc)}">\n' + "\n".join(tc) + "\n    </testsuite>\n"
        for p, tc in suites.items()
    )
    return f'<?xml version="1.0" encoding="UTF-8" ?>\n<testsuites name="vitest tests">\n{body}</testsuites>\n'


# ---------------------------------------------------------------- shared stories
PY_ACC_PATH = "tests/acceptance/S1/test_S1_count.py"
PY_ACC_CLS = "tests.acceptance.S1.test_S1_count"
PY_ACC = b"def test_S1_C1_counts_words():\n    assert False\n\n\ndef test_S1_C2_missing_file():\n    assert False\n"
PY_TESTS = ["test_S1_C1_counts_words", "test_S1_C2_missing_file"]
STORY_S1 = b"""# S1: Count words

## Criteria

| ID | Criterion | Cites |
| --- | --- | --- |
| S1-C1 | The page shows `words: <n>` for the text typed | Request, sentence 1 |
| S1-C2 | An empty box shows `words: 0` | Request, sentence 2 |

## Plain checklist (approved by the owner; the receipt quotes it word for word)

| ID | plain: | Examples (approved) |
| --- | --- | --- |
| S1-C1 | When you type some words, the page shows how many there are, like "words: 3". | `words: 3` |
| S1-C2 | When the box is empty, the page shows "words: 0". | `words: 0` |
"""
STORY_S2 = b"""# S2: Clear the box

## Criteria

| ID | Criterion | Cites |
| --- | --- | --- |
| S2-C1 | A "Clear" button empties the box and shows `words: 0` | Request, sentence 1 |

## Plain checklist (approved by the owner; the receipt quotes it word for word)

| ID | plain: | Examples (approved) |
| --- | --- | --- |
| S2-C1 | When you press "Clear", the box empties and the page shows "words: 0". | `words: 0` |
"""

JS1 = "tests/acceptance/S1/S1-C1.test.tsx"
JS2 = "tests/acceptance/S1/S1-C2.test.tsx"
JS1_TITLE = "S1-C1 shows the word count"
JS2_TITLE = "S1-C2 shows words: 0 for an empty box"
JS1_SRC = (
    '// @vitest-environment jsdom\nimport { test, expect } from "vitest";\n'
    'import { render } from "@testing-library/react";\n'
    'import { Counter } from "../../../src/Counter";\n'
    f'test("{JS1_TITLE}", () => {{\n  render(<Counter text="a b c" />);\n'
    '  expect(document.body.textContent).toContain("words: 3");\n});\n'
).encode()
JS2_SRC = (
    '// @vitest-environment jsdom\nimport { test, expect } from "vitest";\n'
    'import { render } from "@testing-library/react";\n'
    'import { Counter } from "../../../src/Counter";\n'
    f'test("{JS2_TITLE}", () => {{\n  render(<Counter text="" />);\n'
    '  expect(document.body.textContent).toContain("words: 0");\n});\n'
).encode()
JS_S2 = "tests/acceptance/S2/S2-C1.test.tsx"
JS_S2_TITLE = "S2-C1 clears the box"
JS_S2_SRC = (
    '// @vitest-environment jsdom\nimport { test, expect } from "vitest";\n'
    f'test("{JS_S2_TITLE}", () => {{\n  expect(document.body.textContent).toContain("words: 0");\n}});\n'
).encode()
UNIT_PY = ("tests.unit.test_app", "test_unit_ok", "pass")
UNIT_JS = ("src/Counter.test.tsx", "counts words", "pass")


def write_case(
    cid: str,
    *,
    branch: str,
    changed: list[str],
    main: dict[str, bytes],
    head: dict[str, bytes],
    evidence: dict[str, str],
) -> None:
    d = CASES / cid
    for name, tree in (("main", main), ("head", head)):
        for p, raw in tree.items():
            f = d / name / p
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(raw)
    for p, text in evidence.items():
        f = d / "evidence" / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(text.encode("utf-8"))
    (d / "case.json").write_bytes((json.dumps({"branch": branch, "changed": changed}, indent=2) + "\n").encode())


# ---------------------------------------------------------------- Python rows (today's behaviour, kept by v0.4.0)
PY_MAIN = {
    "locks.json": locks({PY_ACC_PATH: (PY_ACC, PY_TESTS)}),
    "dev-docs/stories/S1/story.md": STORY_S1,
    PY_ACC_PATH: PY_ACC,
}
PY_C3 = {f"c3/{slug(PY_ACC_PATH)}.xml": pytest_xml([(PY_ACC_CLS, t, "assert") for t in PY_TESTS])}


def py_evidence(pr_kinds=("pass", "pass"), acc_kinds=("pass", "pass"), c3_kind="assert") -> dict[str, str]:
    a = [(PY_ACC_CLS, t, k) for t, k in zip(PY_TESTS, acc_kinds, strict=True)]
    p = [UNIT_PY] + [(PY_ACC_CLS, t, k) for t, k in zip(PY_TESTS, pr_kinds, strict=True)]
    return {
        "pr.xml": pytest_xml(p),
        "acceptance.xml": pytest_xml(a),
        f"c3/{slug(PY_ACC_PATH)}.xml": pytest_xml([(PY_ACC_CLS, t, c3_kind) for t in PY_TESTS]),
    }


ROWS: list[dict] = []


def row(cid: str, lang: str, level: str, cites: str, expect: dict, milestone: str = "M0") -> None:
    ROWS.append({"id": cid, "lang": lang, "level": level, "milestone": milestone, "cites": cites, "expect": expect})


def build_python() -> None:
    write_case(
        "py-proven", branch="build/S1", changed=["app/count.py"], main=PY_MAIN, head=PY_MAIN, evidence=py_evidence()
    )
    row(
        "py-proven",
        "python",
        "judge",
        "design §4.6; v0.3.4",
        {"verdict": "PROVEN", "codes": [], "statuses": {"S1-C1": "works", "S1-C2": "works"}},
    )
    write_case(
        "py-check-fails",
        branch="build/S1",
        changed=["app/count.py"],
        main=PY_MAIN,
        head=PY_MAIN,
        evidence=py_evidence(pr_kinds=("pass", "assert"), acc_kinds=("pass", "assert")),
    )
    row(
        "py-check-fails",
        "python",
        "judge",
        "design §4.6; v0.3.4",
        {"verdict": "NOT PROVEN", "codes": ["CHECK_FAILS"], "statuses": {"S1-C1": "works", "S1-C2": "fails"}},
    )
    s2_path = "tests/acceptance/S2/test_S2_clear.py"
    s2 = b"def test_S2_C1_clears():\n    assert False\n"
    head = dict(
        PY_MAIN,
        **{
            "locks.json": locks({PY_ACC_PATH: (PY_ACC, PY_TESTS), s2_path: (s2, ["test_S2_C1_clears"])}),
            "dev-docs/stories/S2/story.md": STORY_S2,
            s2_path: s2,
        },
    )
    write_case(
        "py-story",
        branch="story/S2",
        changed=["locks.json", "dev-docs/stories/S2/story.md", s2_path],
        main=PY_MAIN,
        head=head,
        evidence=py_evidence(),
    )
    row("py-story", "python", "judge", "design §4.6; v0.3.4", {"verdict": "WAITING FOR YOU", "codes": ["NEW_CHECKS"]})
    write_case("py-no-results", branch="build/S1", changed=["app/count.py"], main=PY_MAIN, head=PY_MAIN, evidence={})
    row("py-no-results", "python", "judge", "design §4.6; v0.3.4", {"verdict": "UNRESOLVED", "codes": ["NO_RESULTS"]})
    write_case(
        "py-existence-only",
        branch="build/S1",
        changed=["app/count.py"],
        main=PY_MAIN,
        head=PY_MAIN,
        evidence=py_evidence(c3_kind="import"),
    )
    row(
        "py-existence-only",
        "python",
        "judge",
        "design §4.6; v0.3.4",
        {"verdict": "WAITING FOR YOU", "codes": ["EXISTENCE_ONLY"]},
    )
    weak = PY_ACC.replace(b"assert False", b"assert True", 1)
    write_case(
        "py-weakened-check",
        branch="build/S1",
        changed=["app/count.py", PY_ACC_PATH],
        main=PY_MAIN,
        head=dict(PY_MAIN, **{PY_ACC_PATH: weak}),
        evidence=py_evidence(),
    )
    row(
        "py-weakened-check",
        "python",
        "judge",
        "design §4.6; v0.3.4",
        {"verdict": "WAITING FOR YOU", "codes": ["LOCK_CHANGED"], "statuses": {"S1-C1": "check_changed"}},
    )
    write_case(
        "py-tampered-settings",
        branch="build/S1",
        changed=["app/count.py", "pytest.ini"],
        main=PY_MAIN,
        head=PY_MAIN,
        evidence=py_evidence(),
    )
    row(
        "py-tampered-settings",
        "python",
        "judge",
        "design §4.6; v0.3.4; D41",
        {"verdict": "WAITING FOR YOU", "codes": ["PROTECTED_CHANGED"], "statuses": {"S1-C1": "file_changed"}},
    )
    write_case(
        "py-frontend-before-js",
        branch="build/S1",
        changed=["app/count.py", "frontend/package.json", "frontend/tsconfig.json", "frontend/vite.config.ts"],
        main=PY_MAIN,
        head=PY_MAIN,
        evidence=py_evidence(),
    )
    row(
        "py-frontend-before-js",
        "python",
        "judge",
        "design §3.2 and §4.4, L5 B: no JavaScript checks yet",
        {"verdict": "PROVEN", "codes": [], "no_codes": ["PROTECTED_CHANGED"]},
    )
    write_case(
        "py-frontend-lockfile",
        branch="build/S1",
        changed=["app/count.py", "frontend/package-lock.json"],
        main=PY_MAIN,
        head=PY_MAIN,
        evidence=py_evidence(),
    )
    row(
        "py-frontend-lockfile",
        "python",
        "judge",
        "v0.3.4 (lock files already protected everywhere)",
        {"verdict": "WAITING FOR YOU", "codes": ["PROTECTED_CHANGED"]},
    )


# ---------------------------------------------------------------- JavaScript rows (v0.4.0's target; fail today)
JS_LOCKS = {JS1: (JS1_SRC, [JS1_TITLE]), JS2: (JS2_SRC, [JS2_TITLE])}
JS_MAIN = {"locks.json": locks(JS_LOCKS), "dev-docs/stories/S1/story.md": STORY_S1, JS1: JS1_SRC, JS2: JS2_SRC}


def js_evidence(
    pr=("pass", "pass"),
    acc=("pass", "pass"),
    c3=("assert", "assert"),
    extra_pr=(),
    extra_acc=(),
    install: str | None = None,
) -> dict[str, str]:
    ev: dict[str, str] = {}
    if install is not None:
        ev["js-install.txt"] = install + "\n"
        return ev
    ev["pr-js.xml"] = vitest_xml([UNIT_JS, (JS1, JS1_TITLE, pr[0]), (JS2, JS2_TITLE, pr[1]), *extra_pr])
    ev["acceptance-js.xml"] = vitest_xml([(JS1, JS1_TITLE, acc[0]), (JS2, JS2_TITLE, acc[1]), *extra_acc])
    for path, title, kind in ((JS1, JS1_TITLE, c3[0]), (JS2, JS2_TITLE, c3[1])):
        cases = [(path, path, kind)] if kind in ("missing-module",) else [(path, title, kind)]
        ev[f"c3/{slug(path)}.xml"] = vitest_xml(cases)
    return ev


def build_js() -> None:
    def js(
        cid: str,
        cites: str,
        expect: dict,
        *,
        branch="build/S1",
        changed=("src/Counter.tsx",),
        main=None,
        head=None,
        evidence=None,
        milestone="M1",
    ) -> None:
        write_case(
            cid,
            branch=branch,
            changed=list(changed),
            main=main or JS_MAIN,
            head=head or main or JS_MAIN,
            evidence=js_evidence() if evidence is None else evidence,
        )
        row(cid, "javascript", "judge", cites, expect, milestone)

    js(
        "js-proven",
        "design §2 line 1, §4.6",
        {"verdict": "PROVEN", "codes": [], "statuses": {"S1-C1": "works", "S1-C2": "works"}},
    )
    js(
        "js-check-fails",
        "design §4.6",
        {"verdict": "NOT PROVEN", "codes": ["CHECK_FAILS"], "statuses": {"S1-C1": "works", "S1-C2": "fails"}},
        evidence=js_evidence(pr=("pass", "assert"), acc=("pass", "assert")),
    )
    story_head = {
        "locks.json": locks(JS_LOCKS),
        "dev-docs/stories/S1/story.md": STORY_S1,
        JS1: JS1_SRC,
        JS2: JS2_SRC,
        "package.json": b'{\n  "name": "app"\n}\n',
        "package-lock.json": b"{}\n",
    }
    empty_main = {"package.json": b'{\n  "name": "app"\n}\n'}
    js(
        "js-story",
        "design §4.4 STORY_ADDS_TOOLS, §4.5 first story",
        {"verdict": "WAITING FOR YOU", "codes": ["NEW_CHECKS", "STORY_ADDS_TOOLS"]},
        branch="story/S1",
        changed=["locks.json", "dev-docs/stories/S1/story.md", JS1, JS2, "package.json", "package-lock.json"],
        main=empty_main,
        head=story_head,
    )
    js(
        "js-story-repairs-lockfile",
        "design §4.5 (the repair rides in the first story), JS-15, JS-19, JS-22",
        {"verdict": "WAITING FOR YOU", "codes": ["NEW_CHECKS", "STORY_ADDS_TOOLS"]},
        branch="story/S1",
        changed=["locks.json", "dev-docs/stories/S1/story.md", JS1, JS2, "package.json", "package-lock.json"],
        main=dict(empty_main, **{"package-lock.json": b'{"stale": true}\n'}),
        head=story_head,
    )
    js(
        "js-no-results-platform",
        "design §4.4 install codes, JS-8, JS-19",
        {"verdict": "UNRESOLVED", "codes": ["NO_RESULTS"], "receipt_has": ["only work on another kind of computer"]},
        evidence=js_evidence(install="EBADPLATFORM"),
    )
    js(
        "js-no-results-out-of-step",
        "design §4.4 install codes, JS-8",
        {"verdict": "UNRESOLVED", "codes": ["NO_RESULTS"], "receipt_has": ["could not install"]},
        evidence=js_evidence(install="EUSAGE"),
    )
    js(
        "js-existence-only",
        "design §4.4 (a file that could not load), JS-1, JS-9",
        {"verdict": "WAITING FOR YOU", "codes": ["EXISTENCE_ONLY"]},
        evidence=js_evidence(c3=("missing-module", "missing-module")),
    )
    js(
        "js-not-a-function",
        "design §4.4, JS-1",
        {"verdict": "WAITING FOR YOU", "codes": ["EXISTENCE_ONLY"]},
        evidence=js_evidence(c3=("not-a-function", "not-a-function")),
    )
    js(
        "js-component-not-written",
        "design §4.4, JS-14",
        {"verdict": "WAITING FOR YOU", "codes": ["EXISTENCE_ONLY"]},
        evidence=js_evidence(c3=("element-invalid", "element-invalid")),
    )
    js(
        "js-empty-type",
        "design §4.4 (a JavaScript failure with an empty type is unreadable)",
        {"verdict": "UNRESOLVED", "codes": ["NO_BEFORE_RESULT"], "no_codes": ["NO_RESULTS"]},
        evidence=js_evidence(c3=("empty-type", "empty-type")),
    )
    weak = JS1_SRC.replace(b'toContain("words: 3")', b"toBeTruthy()")
    js(
        "js-weakened-check",
        "design §4.6, D25",
        {"verdict": "WAITING FOR YOU", "codes": ["LOCK_CHANGED"], "statuses": {"S1-C1": "check_changed"}},
        changed=["src/Counter.tsx", JS1],
        head=dict(JS_MAIN, **{JS1: weak}),
    )
    for cid, path, cites in (
        ("js-tampered-settings", "vitest.config.ts", "design §4.4 protected names, JS-3"),
        ("js-npmrc", ".npmrc", "design §4.4 protected names"),
        ("js-package-script", "package.json", "design §4.4, L4 A"),
        ("js-tsconfig-cheat", "tsconfig.app.json", "design §4.3, §4.4, JS-12, JS-20"),
    ):
        js(
            cid,
            cites,
            {"verdict": "WAITING FOR YOU", "codes": ["PROTECTED_CHANGED"], "statuses": {"S1-C1": "file_changed"}},
            changed=["src/Counter.tsx", path],
        )
    js(
        "js-setup-file-cheat",
        "design §4.3 (AsBuild's own settings), JS-3, JS-6, JS-9",
        {"verdict": "NOT PROVEN", "codes": ["CHECK_FAILS"], "statuses": {"S1-C2": "fails"}},
        changed=["src/Counter.tsx", "src/test/setup.ts"],
        evidence=js_evidence(pr=("pass", "pass"), acc=("pass", "assert")),
    )
    s2_locks = dict(JS_LOCKS, **{JS_S2: (JS_S2_SRC, [JS_S2_TITLE])})
    s2_main = {
        "locks.json": locks(s2_locks),
        "dev-docs/stories/S1/story.md": STORY_S1,
        "dev-docs/stories/S2/story.md": STORY_S2,
        JS1: JS1_SRC,
        JS2: JS2_SRC,
        JS_S2: JS_S2_SRC,
    }
    # S1 is built and merged, so its checks pass on main (fails-before shows "pass"): not an unbuilt story.
    s2_ev = js_evidence(
        pr=("pass", "pass"),
        acc=("pass", "assert"),
        c3=("pass", "pass"),
        extra_pr=[(JS_S2, JS_S2_TITLE, "pass")],
        extra_acc=[(JS_S2, JS_S2_TITLE, "pass")],
    )
    s2_ev[f"c3/{slug(JS_S2)}.xml"] = vitest_xml([(JS_S2, JS_S2_TITLE, "assert")])
    js(
        "js-earlier-story-masked",
        "design §4.4 (round-3 HIGH: earlier stories judged by the hardened run)",
        {"verdict": "NOT PROVEN", "codes": ["PASS_TO_PASS_BROKEN"], "statuses": {"S2-C1": "works"}},
        branch="build/S2",
        changed=["src/Clear.tsx", "src/test/setup.ts"],
        main=s2_main,
        head=s2_main,
        evidence=s2_ev,
    )
    # A Python repository with a front end, after its first JavaScript story (L5 B: the names now apply).
    mixed_main = dict(
        PY_MAIN, **{"locks.json": locks({PY_ACC_PATH: (PY_ACC, PY_TESTS), **JS_LOCKS}), JS1: JS1_SRC, JS2: JS2_SRC}
    )
    js(
        "py-frontend-after-js",
        "design §3.2, §4.4, L5 B: JavaScript checks exist",
        {"verdict": "WAITING FOR YOU", "codes": ["PROTECTED_CHANGED"]},
        changed=["app/count.py", "frontend/vite.config.ts"],
        main=mixed_main,
        head=mixed_main,
        evidence=dict(py_evidence(), **js_evidence()),
    )
    ROWS[-1]["lang"] = "mixed"


def build_pending() -> None:
    """Rows the design names that run in later milestones (live runs in M2, setup in M3): listed now, run then."""
    for vite, vitest in (("5", "3.2.4"), ("6", "3.2.4"), ("7", "4.1.12"), ("8", "5.1.0")):
        for kind, verdict in (("proven", "PROVEN"), ("existence-only", "WAITING FOR YOU")):
            row(
                f"live-vite{vite}-{kind}",
                "javascript",
                "live",
                f"design §4.4 (Vitest table: Vite {vite} with Vitest {vitest}), §4.6, JS-17",
                {"verdict": verdict},
                "M2",
            )
    row(
        "live-js-column",
        "javascript",
        "live",
        "design §2 line 1, §4.6 level 2: every judge row above in a real repository with the real workflows",
        {"verdict": "as each judge row"},
        "M2",
    )
    for cid, what, outcome in (
        ("setup-py-subfolder-package", "a `.py` file and a `package.json` in a subfolder", "Python path, as today"),
        ("setup-both-at-root", "`package.json` and `requirements.txt` at the root", "Python path, as today"),
        ("setup-js-root", "a root `package.json` with React and Vite 5 to 8, no Python file", "JavaScript path"),
        ("setup-stop-subfolder-app", "no root `package.json`, one below the root, no Python marker", "stops: not yet"),
        ("setup-stop-no-react", "no `react`, or React Native", "stops: not yet"),
        ("setup-stop-vite", "no Vite, or a Vite outside 5 to 8", "stops: not yet"),
        (
            "setup-stop-vitest-off-table",
            "an installed Vitest that is not the table's for the app's Vite",
            "stops: not yet",
        ),
        ("setup-stop-jest-only", "Jest without Vitest", "stops: not yet"),
        ("setup-stop-playwright", "Playwright tests", "stops: not yet"),
        ("setup-stop-workspaces", "workspaces", "stops: not yet"),
        ("setup-stop-next", "Next.js (L7 B)", "stops: not yet"),
        ("setup-stop-npm", "Node older than 24 or npm older than 11.19", "stops: not yet, with the install line"),
    ):
        row(cid, "setup", "setup", f"design §3.1, §3.2, §4.5: {what}", {"outcome": outcome}, "M3")


def main() -> None:
    if CASES.exists():
        shutil.rmtree(CASES)
    build_python()
    build_js()
    build_pending()
    table = {
        "about": "v0.4.0's agreed conformance rows (D47, D48; docs/plans/v0.4-design.md §4.6). Locked after the owner "
        "merges M0: changing a row is an owner decision. `codes` must all appear; `no_codes` must not; "
        "`statuses` maps check ids to their line status; `receipt_has` must appear in the receipt's plain part. "
        "`milestone` is when the row must first pass.",
        "cases": ROWS,
    }
    (HERE / "cases.json").write_bytes((json.dumps(table, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(f"{len(ROWS)} rows; {sum(1 for r in ROWS if r['level'] == 'judge')} judged by the engine")


if __name__ == "__main__":  # pragma: no cover
    main()
