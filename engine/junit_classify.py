"""Classify how each test behaved, from a pytest JUnit XML file (ported from step 0's T18).

Trusted-side code: it reads XML and nothing else, and never imports or runs project code.

Per test case:
  passed          the test passed
  strong          the test ran and an assertion failed (real "fails before" evidence)
  existence-only  the test failed only because something does not exist yet: ImportError,
                  ModuleNotFoundError, AttributeError or NameError, or the file could not be collected
  skipped         the test was skipped

Checked on pytest 9 with `-o junit_family=xunit2`: the `type` attribute of <failure> is empty there,
so the rule keys on the message prefix.
"""

from __future__ import annotations

import os
import re

try:  # the XML comes from the untrusted run: use the hardened parser when it is installed
    from defusedxml import ElementTree as ET
except ImportError:  # pragma: no cover - the workflows install defusedxml
    import xml.etree.ElementTree as ET  # noqa: N817

MAX_BYTES = 20 * 1024 * 1024
EXISTENCE = re.compile(r"^(ImportError|ModuleNotFoundError|AttributeError|NameError)\b")

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


def load(path: str) -> dict[Key, str] | None:
    """{(classname, name): kind}, or None if the file is missing, too large, unreadable or has no test cases."""
    if not os.path.isfile(path) or os.path.getsize(path) > MAX_BYTES:
        return None
    try:
        root = ET.parse(path).getroot()
    except Exception:  # noqa: BLE001 - any parse failure means "no readable results"
        return None
    cases = {(tc.get("classname") or "", tc.get("name") or ""): classify(tc)[0] for tc in root.iter("testcase")}
    return cases or None
