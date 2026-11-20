"""Render the plain receipt from a verdict, deterministically (ported from G4's render_plain.py; no model).

Top layer, in four parts: the headline, the person's list in their own approved words, "Do you need to do
anything?" and "Good to know". The technical report goes underneath, folded. Six templates (decision C3):
  1 PROVEN
  2 WAITING FOR YOU: a check or protected file changed, or new checks to approve
  3 WAITING FOR YOU: a check missing, skipped, already true before, failing before only because something did
    not exist yet, or no story covers the change
  4 NOT PROVEN: a check still fails
  5 NOT PROVEN: another test failed in the pull request's own run
  6 UNRESOLVED
"""

from __future__ import annotations

import json
import os
import re
import string

MARKER = "<!-- asbuild-receipt -->"
# K8 (the owner's option A): the story's title and plain lines are text from the pull request, shown as written, never
# as Markdown. An ordinary line (only what GitHub never acts on) is left exactly as it is, so receipts stay v0.3.4's
# (done line 2). Any other line is escaped whole: every ASCII punctuation mark gets a backslash, an invisible word
# joiner sits between every two visible ASCII characters (what GitHub turns into a link, mention, reference, emoji
# code or commit id is written in ASCII, so no such word stays whole), and one sits on both sides of every dollar sign,
# at the line's ends too (a formula). Characters outside ASCII get none beside them, so accents, emoji and other
# scripts stay whole (round 1, B3); spaces stay plain, so lines still wrap. Checked with GitHub's own renderer; the
# Level 2 live run checks a posted note.
WORD_JOINER = chr(0x2060)
PLAIN_CHARS = re.compile(r"^(?:[^\W\d_]|\d|\s|[,.;?!'\"%()-]|:(?=\s|$))*$")


def ordinary(text: str) -> bool:
    """Only letters, digits, spaces and the marks , . ; ? ! ' " % ( ) - and a colon before a space; no word mixing
    letters and digits (GH-1, a repository's own link prefixes), no run of 7 hex characters (a commit id), no www."""
    return (
        bool(PLAIN_CHARS.match(text))
        and "www." not in text.lower()
        and not any(re.search(r"\d", w) and re.search(r"[^\W\d_]", w) for w in text.split())
        and not re.search(r"[0-9a-f]{7}", text, re.I)
    )


def as_written(text: str) -> str:
    if ordinary(text):
        return text
    out: list[str] = []
    for i, c in enumerate(text):
        prev = text[i - 1] if i else ""
        if "$" in (c, prev) or (_visible_ascii(prev) and _visible_ascii(c)):
            out.append(WORD_JOINER)
        out.append("\\" + c if c in string.punctuation else c)
    return "".join(out) + (WORD_JOINER if text.endswith("$") else "")


def _visible_ascii(c: str) -> bool:
    return c.isascii() and c.isprintable() and not c.isspace() and c != ""


TEMPLATE_2 = (
    "NEW_CHECKS",
    "NEW_CHECKS_UNDESCRIBED",
    "LOCK_CHANGED",
    "LOCK_DELETED",
    "PROTECTED_CHANGED",
    "STORY_ADDS_TOOLS",
    "STORY_HAS_APP_FILES",
)
# Design §4.4: a JavaScript story that adds its test tools, and the npm error codes the test job reports.
STORY_ADDS_TOOLS = (
    "It also changes the list of software your app installs; approving the checks approves that change too."
)
# K7: a story pull request that also changes the app. Only the number shows: a file's name is the pull request's text.
STORY_HAS_APP_FILES = (
    "It also changes {n} other {files} of your app, which AsBuild hasn't checked; approving the checks adds those "
    "changes too."
)
STORY_HAS_APP_FILES_ACTION = (
    "If you didn't ask for that, tell the AI: \"Keep only the new checks in this change, and put the other changes in "
    'a separate one."'
)
INSTALL = {
    "EBADPLATFORM": "Your app's list of software includes parts that only work on another kind of computer, so GitHub "
    "could not install it.",
    "ERESOLVE": "Your app's list of software includes parts that don't work with each other, so GitHub could not "
    "install it.",
    "EUSAGE": "Your app's list of software doesn't match its list of exact versions, so GitHub could not install it.",
}
TEMPLATE_3 = (
    "OUT_OF_DATE",
    "LOCK_TEST_MISSING",
    "LOCK_TEST_SKIPPED",
    "ACCEPTANCE_PASSES_ON_MAIN",
    "EXISTENCE_ONLY",
    "NO_STORY",
)

# Protected files, named for the person by what they are, never by path.
PLAIN_FILE = [
    (re.compile(r"(^|/)dev-docs/requests/"), "your original request"),
    (re.compile(r"(^|/)dev-docs/stories/"), "the agreed description of this job"),
    (re.compile(r"(^|/)tests/acceptance/.*/data/"), "the sample data your checks use"),
    (re.compile(r"(^|/)tests/acceptance/"), "one of your agreed checks"),
    (re.compile(r"^locks\.json$"), "the record of your agreed checks"),
    (re.compile(r"(^|/)(AGENTS|CLAUDE)\.md$", re.I), "the rules the AI must follow"),
    (
        re.compile(
            r"(^|/)(conftest\.py|\.?pytest\.ini|\.?pytest\.toml|tox\.ini|setup\.cfg|setup\.py|\.coveragerc"
            r"|sitecustomize\.py)$|\.pth$"
        ),
        "the settings for how your checks run",
    ),
    (
        re.compile(
            r"(^|/)((vite|vitest)\.config\.[^/]*|vitest\.workspace\.[^/]*|tsconfig[^/]*\.json|jsconfig\.json"
            r"|\.nvmrc|\.node-version)$"
        ),
        "the settings for how your checks run",
    ),
    (re.compile(r"(^|/)pyproject\.toml$"), "the project's settings file"),
    (re.compile(r"(^|/)\.github/"), "the settings for the checks on GitHub"),
    (re.compile(r"^out(/|$)"), "the folder where your checks' results are written"),  # K9
    (
        re.compile(
            r"(^|/)requirements[^/]*$|\.lock$|(^|/)(package-lock\.json|pnpm-lock\.yaml|package\.json"
            r"|npm-shrinkwrap\.json|bun\.lockb|pnpm-workspace\.yaml|\.npmrc|\.yarnrc[^/]*)$"
        ),
        "the list of software your app installs",
    ),
]

STATUS = {
    "works": "✓ works",
    "fails": "✗ doesn't work yet",
    "check_changed": "? not judged: the AI changed one of your agreed checks",
    "check_removed": "? not judged: the AI removed one of your agreed checks",
    # D41 (K1); D54 (K10): the line itself is unchanged
    "file_changed": (
        "? not judged, though this line is still as you agreed it: the AI changed a file only you may change"
    ),
    "not_checked": "? not checked this time",
    "already_passed": "? not shown yet: this was already true before the AI started",
    "exists_only": "? not shown yet: it failed before only because a part of the app didn't exist",
    "new": "new, for you to approve",
}
UNJUDGED = ("not_checked", "check_changed", "check_removed", "file_changed")  # no line was judged


def plain_file(path: str) -> str:
    for rx, name in PLAIN_FILE:
        if rx.search(path):
            return name
    return "a file only you may change"


def _accept(actions: list[str]) -> str:
    """How to accept a change (D54, K10): the green button, its name in brackets only once per receipt."""
    if any("(Merge pull request)" in a for a in actions):
        return "accept it on GitHub with the same green button."
    return "accept it on GitHub with the green button (Merge pull request)."


def template(v: dict) -> int:
    names = [c["code"] for c in v["codes"]]
    if v["verdict"] == "PROVEN":
        return 1
    if v["verdict"] == "WAITING FOR YOU":
        return 2 if any(n in TEMPLATE_2 for n in names) else 3
    if v["verdict"] == "NOT PROVEN":
        return 5 if "PASS_TO_PASS_BROKEN" in names else 4
    return 6


def _waiting(v: dict, names: list[str], head: list[str], actions: list[str]) -> None:
    paths = [
        c["params"].get("path", "")
        for c in v["codes"]
        if c["code"] in ("PROTECTED_CHANGED", "LOCK_CHANGED", "LOCK_DELETED")
    ]
    files = " and ".join(sorted({plain_file(p) for p in paths}))
    if "NEW_CHECKS" in names:
        head.append(
            "This needs you: the AI has written new checks for this job, and they count only once you approve them."
        )
        actions.append(
            "Yes. Read each new line above. If every line says what you asked for, approve them on "
            "GitHub with the green button (Merge pull request). From then on the AI can't change them."
        )
        actions.append("If a line is wrong, tell the AI what it should say instead, before you approve.")
    if "NEW_CHECKS_UNDESCRIBED" in names:
        head[:] = [
            "Stop. Don't approve these yet. The AI added new checks without describing them in plain words, so "
            "you can't see what you would approve."
        ]
        actions[:] = ['Yes. Tell the AI: "Describe every new check in plain words in its story, then show it to me."']
    elif "STORY_ADDS_TOOLS" in names:
        head.append(STORY_ADDS_TOOLS)
    for c in [c for c in v["codes"] if c["code"] == "STORY_HAS_APP_FILES"]:
        count = len(c["params"]["paths"])
        head.append(STORY_HAS_APP_FILES.format(n=count, files="file" if count == 1 else "files"))
        actions.append(STORY_HAS_APP_FILES_ACTION)
    if any(n in ("LOCK_CHANGED", "LOCK_DELETED", "PROTECTED_CHANGED") for n in names):
        # Setup's own update (its branch, AsBuild's two workflow files only) is expected (README: read it, merge it).
        own = bool(v.get("setup_update"))
        removed = set(paths) <= {c["params"].get("path", "") for c in v["codes"] if c["code"] == "LOCK_DELETED"}
        if not head:
            if own:
                head.append(
                    "This looks like AsBuild's own update from its setup. It changes "
                    f"{files}, which only you are allowed to change, so AsBuild can't pass it without you."
                )
            else:
                head.append(
                    f"Stop. This needs you. Don't accept it yet. The AI {'removed' if removed else 'changed'} "
                    f"{files}, which only you are allowed to change, so AsBuild can't pass this without you."
                )
        if own:
            actions.append(f"Yes. If you ran AsBuild's setup, read the change, then {_accept(actions)}")
            actions.append(f'If you didn\'t, tell the AI: "Undo your change to {files}."')
        else:
            actions.append(f'Yes. If you didn\'t ask for this, tell the AI: "Undo your change to {files}."')
            if "NEW_CHECKS" not in names:
                actions.append(f"If you did ask for it, read the change, then {_accept(actions)}")
    for n in [n for n in TEMPLATE_3 if n in names]:
        lead = not head
        if n == "OUT_OF_DATE":
            if lead:
                head.append(
                    "Stop. This needs you. Don't accept it yet. The AI's work starts from an older version of your "
                    "app, so AsBuild can't check it against your latest list."
                )
            actions.append(
                'Yes. Tell the AI: "Bring your work up to date with the latest version of the app, then check again."'
            )
        elif n in ("LOCK_TEST_MISSING", "LOCK_TEST_SKIPPED"):
            if lead:
                head.append(
                    "Stop. This needs you. Don't accept it yet. One of your checks didn't run, so AsBuild "
                    "can't tell whether your request works."
                )
            actions.append('Yes. Tell the AI: "Make all my checks run again, without changing them."')
        elif n == "ACCEPTANCE_PASSES_ON_MAIN":
            if lead:
                head.append(
                    "Stop. This needs you. Don't accept it yet. One line on your list was already true "
                    "before the AI started, so it can't show that the AI's work does what you asked."
                )
            actions.append(
                'Yes. Tell the AI: "The line marked ? was already true before you started. Suggest a '
                "new example for it that isn't true yet, and show it to me.\""
            )
        elif n == "EXISTENCE_ONLY":
            if lead:
                head.append(
                    "Stop. This needs you. Don't accept it yet. One line on your list failed before only "
                    "because a part of the app didn't exist, so it can't show that the AI's work does what "
                    "you asked."
                )
            actions.append(
                'Yes. Tell the AI: "The line marked ? failed before for the wrong reason. Suggest a '
                'check that fails because the answer is wrong, and show it to me."'
            )
        else:  # NO_STORY
            if v.get("setup_update") and not lead:  # setup's own update: its lines above say what to do
                continue
            if lead:
                head.append("Stop. This needs you. No agreed check covers this change, so nothing could be checked.")
            actions.append(
                "Yes. Agree a list of checks for this change with the AI first. If it needs none, read "
                f"the change, then {_accept(actions)}"
            )
    if not actions:
        actions.append("Yes. Look at the details below and decide.")


def render(v: dict) -> dict:
    n = template(v)
    names = [c["code"] for c in v["codes"]]
    head: list[str] = []
    actions: list[str] = []
    if n == 1:
        head.append("Done. Every line on your list works.")
        p2p = v.get("pass_to_pass") or {}
        if p2p.get("total"):
            head.append(
                "None of your app's other checks failed, apart from the checks of stories not built yet."
                if p2p.get("unbuilt")
                else "None of your app's other checks failed."
            )
        actions.append(f"Yes, one last step to add it to your app. Open [this change on GitHub]({v['pr_url']}).")
        actions.append(
            "If you want this change, press the green button there (Merge pull request). Every line on your "
            "list works; that is all AsBuild checked."
        )
    elif n in (2, 3):
        _waiting(v, names, head, actions)
    elif n in (4, 5):
        head.append("Not done yet, so don't accept it. Nothing has been added to your app yet.")
        if n == 5:
            head.append("Some of your app's other checks fail now.")
        actions.append("No, not yet. Wait: you'll get a new note when the AI has tried again.")
    elif "CRASH" in names:  # the tests may have run; AsBuild itself could not finish
        head.append("Stop. Don't accept it. AsBuild couldn't finish its check, so nothing was checked.")
        actions.append('Yes. Tell the AI: "Run the AsBuild check again." If it happens again, ask for help.')
    else:
        head.append("Stop. Don't accept it. The checks couldn't run, so nothing was checked.")
        head += [INSTALL[c["params"]["error"]] for c in v["codes"] if c["code"] == "INSTALL_FAILED"][:1]
        actions.append(
            "Yes. Tell the AI: \"The checks didn't run. Fix the setup so they run, without changing "
            'them." If it happens again, ask for help.'
        )

    checklist = [f"{STATUS[i['status']]}: {as_written(i['plain'])}" for i in v["items"]]
    broken = (v.get("pass_to_pass") or {}).get("broken", 0) if n == 5 else 0
    if broken:
        besides = (
            ", besides the checks of stories not built yet" if (v.get("pass_to_pass") or {}).get("unbuilt") else ""
        )
        checklist.append(f"✗ Other checks in your app that fail now: {broken}{besides}.")
    title = f" · {as_written(v['title'])}" if v.get("title") else ""
    listed = (
        "The new lines for you to approve:"
        if "NEW_CHECKS" in names
        else ("The list you agreed with the AI before it started:")
    )
    top = [f"Note from AsBuild, which checks the AI's work against the list you agreed{title}", "", " ".join(head)]
    if checklist:
        top += ["", listed] + [f"- {c}" for c in checklist]
    top += ["", "Do you need to do anything?"] + [f"- {a}" for a in actions]
    if "NEW_CHECKS" in names:  # nothing is checked until the owner approves the lines
        top += [
            "",
            "Good to know: AsBuild hasn't checked anything yet. Once you approve these lines, it checks the AI's "
            "work against them, on GitHub, separately from the AI.",
        ]
    elif n == 6 or all(i["status"] in UNJUDGED for i in v["items"]):  # nothing judged
        top += ["", "Good to know: AsBuild runs on GitHub, separately from the AI."]
    else:
        top += [
            "",
            "Good to know: AsBuild checked only the lines on your list, nothing else, such as how fast it "
            "is or how it looks. The check ran on GitHub, separately from the AI.",
        ]
    return {"template": n, "top": "\n".join(top), "technical": v.get("technical") or technical(v)}


def technical(v: dict) -> str:
    """The technical report: verdict, reason codes with their paths and IDs, and each check's status."""
    lines = [f"AsBuild: {v['verdict']} for PR #{v['pr']} at {v['head_sha'][:10]} (story {v.get('story') or 'none'})"]
    if v.get("run_url"):
        lines.append(f"Verdict run: {v['run_url']}")
    lines.append("")
    lines += [
        f"- {c['code']}" + (f" {json.dumps(c['params'], sort_keys=True)}" if c["params"] else "") for c in v["codes"]
    ] or ["- no findings"]
    lines += [f"- {i['id']}: {i['status']}" for i in v["items"]]
    p2p = v.get("pass_to_pass") or {}
    lines.append(f"- other tests: {p2p.get('total', 0)} run, {p2p.get('broken', 0)} broken")
    return "\n".join(lines)


def write_receipt(r: dict, path: str) -> None:
    body = (
        f"{MARKER}\n{r['top']}\n\n<details><summary>Technical report</summary>\n\n```\n{r['technical']}\n```\n"
        "</details>\n"
    )
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
