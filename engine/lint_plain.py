"""Lint for a receipt's plain top layer (ported from G4's lint_plain.py).

Errors:
  BANNED       a banned word outside brackets: merge, pull request, PR, branch, main, commit, test, CI, hash,
               lock (any form)
  ID           a check or story ID (S1-C1, E1-S1)
  PATH         a file path or file name
  CODE         a reason code (UPPER_SNAKE)
  BRACKET_DUP  the same bracketed term more than once in a receipt
  BRACKET_2    more than one bracketed term in one sentence
A Markdown link's address, `[words](https://...)`, is not text the person reads and is left out.

Usage: python lint_plain.py receipt.md ...   (exit 1 on any error)
"""

from __future__ import annotations

import re
import sys

BANNED = re.compile(r"\b(merg\w*|pull[- ]requests?|PRs?|branch\w*|main|commit\w*|test\w*|CI|hash\w*|lock\w*)\b", re.I)
ID = re.compile(r"\b([A-Z]\d+-[A-Z]\d+(-[A-Z]+\d+)?)\b")
PATH = re.compile(r"[\w.-]+/[\w./-]+|\b[\w-]+\.(py|toml|md|json|ini|cfg|txt|yml|yaml|ts|js|xml)\b|\\")
CODE = re.compile(r"\b[A-Z]{2,}(_[A-Z]+)+\b")
BRACKET = re.compile(r"\(([^()]*)\)")
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n")
LINK = re.compile(r"\]\((https?://[^)\s]+)\)")


def lint(rid: str, top: str) -> list[str]:
    top = LINK.sub("]", top)
    errs = []
    outside = BRACKET.sub(" ", top)
    for rx, name in ((BANNED, "BANNED"), (ID, "ID"), (PATH, "PATH"), (CODE, "CODE")):
        errs += [f"{rid}: {name} {m.group(0)!r}" for m in rx.finditer(outside)]
    seen: dict[str, int] = {}
    for m in BRACKET.finditer(top):
        term = m.group(1).strip().lower()
        seen[term] = seen.get(term, 0) + 1
    errs += [f"{rid}: BRACKET_DUP ({t}) x{n}" for t, n in seen.items() if n > 1]
    errs += [f"{rid}: BRACKET_2 {s.strip()[:80]!r}" for s in SENTENCE.split(top) if len(BRACKET.findall(s)) > 1]
    return errs


def main(argv: list[str] | None = None) -> int:
    paths = sys.argv[1:] if argv is None else argv
    errs = []
    for p in paths:
        text = open(p, encoding="utf-8").read().split("\n<details>", 1)[0]
        errs += lint(p, text)
    print("\n".join(errs + [f"{len(paths)} receipt(s), {len(errs)} lint error(s)"]))
    return 1 if errs else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
