"""Classify how each test behaved, from a JUnit XML file (ported from step 0's T18; Vitest's rules added in v0.4.0).

Trusted-side code: it reads XML and nothing else, and never imports or runs project code.

Per test case:
  passed          the test passed
  strong          the test ran and an assertion failed (real "fails before" evidence)
  existence-only  the test failed only because something does not exist yet: ImportError,
                  ModuleNotFoundError, AttributeError or NameError, or the file could not be collected
  skipped         the test was skipped

Checked on pytest 9 with `-o junit_family=xunit2`: the `type` attribute of <failure> is empty there,
so the rule keys on the message prefix.

Vitest (`classify_js`, design §4.4; result shapes proven on Vitest 3.2, 4.1 and 5.1: JS-1, JS-9, JS-14, JS-17): the
rules key on the `type` attribute, which Vitest fills. `AssertionError` is strong. Existence-only: `ReferenceError`; a
`TypeError` saying "is not a function" or "is not a constructor"; the messages in JS_EXISTENCE; a file that could not
load (Vitest records one test case named after the file). A failure with no `type` is `unreadable`: it shows that
the test failed, never how. Every other failure is strong. Which rules apply is chosen by the language row
(engine/langs.py), never by whether `type` is filled.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable

try:  # the XML comes from the untrusted run: use the hardened parser when it is installed
    from defusedxml import ElementTree as ET
except ImportError:  # pragma: no cover - the workflows install defusedxml
    import xml.etree.ElementTree as ET  # noqa: N817

MAX_BYTES = 20 * 1024 * 1024
EXISTENCE = re.compile(r"^(ImportError|ModuleNotFoundError|AttributeError|NameError)\b")
JS_EXISTENCE = (
    "Cannot find module",
    "Cannot find package",
    "Failed to resolve import",
    "does not provide an export named",
    "Element type is invalid",
)
JS_TYPE_ERROR = ("is not a function", "is not a constructor")

Key = tuple[str, str]


def classify(tc) -> tuple[str, str]:
    kids = [k for k in tc if k.tag in ("failure", "error", "skipped")]
    if not kids:
        return "passed", ""
    k = kids[0]
    msg = (k.get("message") or "").strip()
    first = msg.split("\n", 1)[0]
    if k.tag == "skipped":
        return "skipped", first
    if k.tag == "error":  # collection or setup error: nothing in the test body ran
        return "existence-only", f"error: {first}"
    if EXISTENCE.match(msg):
        return "existence-only", first
    return "strong", first


def classify_js(tc) -> tuple[str, str]:
    kids = [k for k in tc if k.tag in ("failure", "error", "skipped")]
    if not kids:
        return "passed", ""
    k = kids[0]
    msg = (k.get("message") or "").strip()
    first = msg.split("\n", 1)[0]
    typ = (k.get("type") or "").strip()
    if k.tag == "skipped":
        return "skipped", first
    if not typ:
        return "unreadable", first
    if typ == "AssertionError":
        return "strong", first
    if (tc.get("name") or "") == (tc.get("classname") or ""):  # the file could not load
        return "existence-only", f"{typ}: {first}"
    if typ == "ReferenceError" or (typ == "TypeError" and any(s in msg for s in JS_TYPE_ERROR)):
        return "existence-only", f"{typ}: {first}"
    if any(s in msg for s in JS_EXISTENCE):
        return "existence-only", f"{typ}: {first}"
    return "strong", f"{typ}: {first}"


def load(path: str, rule: Callable = classify) -> dict[Key, str] | None:
    """{(classname, name): kind} by the given rules, or None if the file is missing, too large, unreadable or has no
    test cases."""
    if not os.path.isfile(path) or os.path.getsize(path) > MAX_BYTES:
        return None
    try:
        root = ET.parse(path).getroot()
    except Exception:  # noqa: BLE001 - any parse failure means "no readable results"
        return None
    cases = {(tc.get("classname") or "", tc.get("name") or ""): rule(tc)[0] for tc in root.iter("testcase")}
    return cases or None
