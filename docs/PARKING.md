# Parking list: AsBuild

Not in Core. Nothing here is designed, reviewed or built until a real user asks (playbook 1.2). Pruned by the parked-ideas review on 21 Nov 2026 (D59): every other item was removed with its reason in `docs/plans/parked-review.md`, and comes back only with new evidence. Add new items as one line with the date and the reason.

## Worth building (D59), ranked, cheapest as one release of about 5 to 6 agent hours

1. A `def test_` line inside a text string: the story-time check refuses a Python check file where the line reader finds a test name that `ast` does not, instead of a lock no build can satisfy (P33; T6).
2. The waiting check shows as failed: the README and the verdict skill say GitHub shows AsBuild's check as failed while it waits for the person, and that AsBuild blocks nothing unless the check is made required (P70; T1).
3. A no-story receipt with broken tests: no "nothing could be checked" and no accept line; tell the AI to fix the other checks first (R03; T4a; D45 point 2).
4. A build that changes only the list of software: the receipt adds the third path, put that change in its own pull request first (P53 in P45's form; T4b; D41).
5. K11, the technical report's `file_changed` wording (R01; D58; see `docs/KNOWN-ISSUES.md`).

## New, not evaluated (found by the review, 21 Nov 2026)

- Python apps whose packages are only in `pyproject.toml` (uv, Poetry): the test job installs only `requirements.txt`.
- One walkthrough on macOS or Linux: every walker run and owner try so far was on one Windows computer.
- The story and verdict skills copied into the repository's `.claude/skills/`, for cloud sessions and teammates without the plugin.
- Any `.py` file makes setup take a TypeScript or JavaScript app as Python (`asbuild_js.py:128`): 30 of 60 sampled repositories.
