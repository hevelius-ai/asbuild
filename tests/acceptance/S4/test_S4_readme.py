"""Story S4: the README of hevelius-ai/asbuild.

The agreed wording (HANDOVER section 4, decisions D14 and D16) is copied here, so the README is checked against it
word for word. The demo README, the real stories and the pin are shown by their pull requests, not here.
"""

import re
from pathlib import Path

README = (Path(__file__).resolve().parents[3] / "README.md").read_text(encoding="utf-8")

SECTIONS = [
    "## What AsBuild is",
    "## Install",
    "## The receipts",
    "## What AsBuild does not prove",
    "## The pressure test",
    "## Security",
    "## Licence",
]

D16 = [
    "PROVEN means every test you approved failed before the change, passes after it and was not changed, and nothing "
    "that worked before broke. It does not mean the request is fully met; the agent wrote the tests and you approved "
    "them.",
    "AsBuild blocks nothing: any pull request can still be merged.",
    "The test results come from a job that runs the pull request's own code, so AsBuild catches tests that were "
    "changed, skipped, weakened or never failed, not a deliberate forgery of results.",
    "AsBuild does not check who built a change and who merged it; GitHub's history shows that.",
]

G3_LEAD = "This test ran on an earlier in-session version with a guard that AsBuild Core does not include."
G3 = (
    "In a six-run pressure test (Claude Sonnet 5.5 and Opus 5.5, one small repository), no agent faked done or "
    "changed an agreed test, and a hash check found every protected file unchanged. The test did not show that the "
    "gate can stop an agent that tries: the guard denied nothing and there was no false 'done' to block."
)

DEMO = {"PROVEN": 3, "NOT PROVEN": 4, "WAITING FOR YOU": 5, "UNRESOLVED": 6}


def section(title):
    lines = README.splitlines()
    assert title in lines, f"README.md has no '{title}' section"
    start = lines.index(title) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def test_S4_C1_readme_says_what_asbuild_is():
    headings = [line for line in README.splitlines() if line.startswith("## ")]
    assert headings == SECTIONS
    what = section("## What AsBuild is")
    for words in (
        "maker-checker record for pull requests written by an AI agent",
        "the agent builds, a program checks, a person approves",
        "the checks were approved before the build (the merged story pull request)",
        "each agreed test failed before the change and passes after it (the receipt)",
        "who built the change",
        "who merged it (both in GitHub's own history, which AsBuild does not check)",
        "for people who merge an agent's work in GitHub and answer for it",
        "not for builders who do not use pull requests",
    ):
        assert words in what, f"'What AsBuild is' does not say: {words}"
    assert "/plugin marketplace add hevelius-ai/asbuild" in section("## Install")


def test_S4_C2_limits_and_g3_wording_word_for_word():
    limits = section("## What AsBuild does not prove")
    items = re.findall(r"^\d\. (.+)$", limits, re.MULTILINE)
    assert items == D16
    pressure = " ".join(section("## The pressure test").split())
    assert G3_LEAD + " " + G3 in pressure


def test_S4_C3_receipts_security_licence_and_wording():
    receipts = section("## The receipts")
    for verdict, number in DEMO.items():
        link = f"https://github.com/hevelius-ai/asbuild-demo/pull/{number}"
        assert re.search(rf"^- \*\*{verdict}\*\*.*{re.escape(link)}", receipts, re.MULTILINE), (
            f"the receipts section does not link {verdict} to demo #{number}"
        )
    security = section("## Security")
    assert "no repository secrets" in security
    assert "https://docs.github.com/en/code-security/secret-scanning" in security
    licence = section("## Licence")
    assert "MIT" in licence and "Hevelius AI Group LLC" in licence
    # the wording rule (D14, D16): AsBuild checks, shows and records; it never proves
    rest = README.replace("## What AsBuild does not prove", "")
    for line in D16:
        rest = rest.replace(line, "")
    assert not re.search(r"\bproof\b", rest, re.IGNORECASE)
    assert not re.search(r"\bprov(e|es|ed|ing)\b", rest, re.IGNORECASE)
