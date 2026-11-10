# Parking list: AsBuild

Not in Core. Nothing here is designed, reviewed or built until "done" is met and a real user asks. Add new items as one line with the date and the reason.

- Session hardening against a cheating agent: custom guard, hashes after every tool call, test-detection scans, held-out twins, the 12-run G3 test (root cause 1 again; CI already does the job)
- The auto-merge gate and builder account as a product; a GitHub ruleset requiring the verdict before merge
- Browser builders, TypeScript, web apps, screenshots, the Lovable flow
- Three modes; the baseline for existing apps; story slicing and build-next-story
- The secret-key wrapper; signed releases
- Publishing to PyPI (needs an account and a token only the owner holds)
- Star-count bars
- The regulated add-on (belongs to the compliance-review track, which is parked)
- Entire CLI transcripts, Spec Kit and Superpowers adapters, Agent Trace, attestations
- Checking a story pull request's `locks.json` entries against its test files (D11 check, 9 Nov 2026: a mismatch only makes later builds wait, never a false PROVEN)
- Locking acceptance data files outside `tests/acceptance/` (D11 check, 9 Nov 2026: that folder is already protected whole)
- Pinning the workflow templates' actions by commit SHA (D11 check, 9 Nov 2026)
- Verdicts for pull requests from forks (D11 check, 9 Nov 2026: the organization requires approval before fork workflows run)
- The local check: `asbuild check` through uvx, and the Stop hook line (D15, 9 Nov 2026: never ran in the form specified; Claude Code's own hooks and deny rules cover the session)
- Hardening against forged test results in the job that runs the pull request's code (9 Nov 2026 check: stated as a limit in the README, D16)
- A Vitest or Jest preset beside pytest (9 Nov 2026 check: TypeScript is the largest share of Claude Code's pull requests; the first item to look at if a stranger asks)
- A control write-up on AI-written changes offered to FINOS's SDLC Controls Framework, with AsBuild as the worked example (9 Nov 2026 check: writing, not building, and only after "done"; not checked whether one is already proposed there)
- A test outside `tests/acceptance` that already fails on main is counted as "something that worked before broke": the full suite runs only on the pull request, as in step 0. Graded PARKED in S1 review round 3 (2026-11-10).
- The story-time example check counts a negated assertion (`assert "words: 3" not in ...`) as checking the example (ported F4 behaviour). Graded PARKED in S2 review round 1 (2026-11-10).
- A timeout on the story-time checks' run of the tests on the base branch. Graded PARKED in S2 review round 1 (2026-11-10).
- The install page does not say whether a plugin installed from the shell needs a reload or a new session before `/asbuild:story`. Graded PARKED in S3 review round 1 (2026-11-10).
- The install page's needs list does not say Python with pytest must be on the reader's own machine for the story-time checks and the wait script. Graded PARKED in S3 review round 1 (2026-11-10).
- A `.claude/settings.json` that is gitignored, or saved with a byte-order mark, when the story-time checks add the deny line. Graded PARKED in S3 review round 1 (2026-11-10).
- The skills' commands say `python`, not `python3`. Graded PARKED in S3 review round 1 (2026-11-10).
- The wait script's timeout exit code 7 is a bare number. Graded PARKED in S3 review round 1 (2026-11-10).
