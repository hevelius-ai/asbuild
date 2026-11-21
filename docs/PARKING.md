# Parking list: AsBuild

Not in Core. Nothing here is designed, reviewed or built until a real user asks (playbook 1.2). Pruned by the parked-ideas review on 21 Nov 2026 (D59): every other item was removed with its reason in `docs/plans/parked-review.md`, and comes back only with new evidence. Add new items as one line with the date and the reason.

## Built

The five ideas D59 kept (P33, P70, R03, P53 in P45's form, R01 = K11) are built in `v0.4.2` (D60). AsBuild is the final product: nothing more is built unless a real user asks.

## New, not evaluated (found by the review, 21 Nov 2026)

- Python apps whose packages are only in `pyproject.toml` (uv, Poetry): the test job installs only `requirements.txt`.
- One walkthrough on macOS or Linux: every walker run and owner try so far was on one Windows computer.
- The story and verdict skills copied into the repository's `.claude/skills/`, for cloud sessions and teammates without the plugin.
- Any `.py` file makes setup take a TypeScript or JavaScript app as Python (`asbuild_js.py:128`): 30 of 60 sampled repositories.
