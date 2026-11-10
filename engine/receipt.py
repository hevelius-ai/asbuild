"""Render the plain receipt from a verdict, deterministically (ported from G4's render_plain.py; no model).

Top layer, in four parts: the headline, the person's list in their own approved words, "Do you need to do
anything?" and "Good to know". The technical report goes underneath, folded. Six templates (decision C3):
  1 PROVEN
  2 WAITING FOR YOU: a check or protected file changed, or new checks to approve
  3 WAITING FOR YOU: a check missing, skipped, already true before, failing before only because something did
    not exist yet, or no story covers the change
  4 NOT PROVEN: a check still fails
  5 NOT PROVEN: something that worked before broke
  6 UNRESOLVED
"""

from __future__ import annotations

import json
import os
import re

MARKER = "<!-- asbuild-receipt -->"
TEMPLATE_2 = ("NEW_CHECKS", "NEW_CHECKS_UNDESCRIBED", "LOCK_CHANGED", "LOCK_DELETED", "PROTECTED_CHANGED")
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
            r"(^|/)(conftest\.py|pytest\.ini|tox\.ini|setup\.cfg|setup\.py|\.coveragerc|sitecustomize\.py)$|\.pth$"
        ),
        "the settings for how your checks run",
    ),
    (re.compile(r"(^|/)pyproject\.toml$"), "the project's settings file"),
    (re.compile(r"(^|/)\.github/"), "the settings for the checks on GitHub"),
    (
        re.compile(r"(^|/)requirements[^/]*$|\.lock$|(^|/)(package-lock\.json|pnpm-lock\.yaml)$"),
        "the list of software your app installs",
    ),
]

STATUS = {
    "works": "✓ works",
    "fails": "✗ doesn't work yet",
    "check_changed": "? not judged: the AI changed one of your agreed checks",
    "not_checked": "? not checked this time",
    "already_passed": "? not shown yet: this was already true before the AI started",
    "exists_only": "? not shown yet: it failed before only because a part of the app didn't exist",
    "new": "• new, for you to approve",
}


def plain_file(path: str) -> str:
    for rx, name in PLAIN_FILE:
        if rx.search(path):
            return name
    return "a file only you may change"


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
    if any(n in ("LOCK_CHANGED", "LOCK_DELETED", "PROTECTED_CHANGED") for n in names):
        if not head:
            head.append(
                f"Stop. This needs you. Don't accept it yet. The AI changed {files}, which only you are "
                "allowed to change, so AsBuild can't pass this without you."
            )
        actions.append(f'Yes. Most likely you didn\'t ask for this. Then tell the AI: "Undo your change to {files}."')
        if "NEW_CHECKS" not in names:
            actions.append("Only if you did ask for it, accept the change yourself after reading it.")
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
            if lead:
                head.append("Stop. This needs you. No agreed check covers this change, so nothing could be checked.")
            actions.append(
                "Yes. Agree a list of checks for this change with the AI first. If it needs none, read "
                "the change and accept it yourself."
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
        if (v.get("pass_to_pass") or {}).get("total"):
            head.append("Everything that worked before still works.")
        actions.append(f"Yes, one last step to add it to your app. Open [this change on GitHub]({v['pr_url']}).")
        actions.append(
            "Press the green button there (Merge pull request). It's safe to press, because every "
            "line on your list works."
        )
    elif n in (2, 3):
        _waiting(v, names, head, actions)
    elif n in (4, 5):
        head.append("Not done yet, so don't accept it. Nothing has been added to your app yet.")
        if n == 5:
            head.append("Something that worked before has stopped working.")
        actions.append("No, not yet. Wait: you'll get a new note when the AI has tried again.")
    elif "CRASH" in names:  # the tests may have run; AsBuild itself could not finish
        head.append("Stop. Don't accept it. AsBuild couldn't finish its check, so nothing was checked.")
        actions.append('Yes. Tell the AI: "Run the AsBuild check again." If it happens again, ask for help.')
    else:
        head.append("Stop. Don't accept it. The checks couldn't run, so nothing was checked.")
        actions.append(
            "Yes. Tell the AI: \"The checks didn't run. Fix the setup so they run, without changing "
            'them." If it happens again, ask for help.'
        )

    checklist = [f"{STATUS[i['status']]}: {i['plain']}" for i in v["items"]]
    broken = (v.get("pass_to_pass") or {}).get("broken", 0) if n == 5 else 0
    if broken:
        checklist.append(f"✗ {broken} thing(s) that worked before are broken now.")
    title = f" · {v['title']}" if v.get("title") else ""
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
    elif n == 6 or all(i["status"] in ("not_checked", "check_changed") for i in v["items"]):  # nothing judged
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
