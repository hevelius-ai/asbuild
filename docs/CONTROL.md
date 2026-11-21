# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now
- v0.4.1, known issue K10 (D54, plan `docs/plans/v0.4.1.md`): **done** 2026-11-21T00:09Z. hevelius-ai/asbuild#48 merged by the owner 2026-11-20T23:59:34Z (dc5a15d); published 2026-11-21T00:01:34Z on dc5a15d; tag checked (engine 0bb2867 in all four workflow files; the `v*` ruleset active). Done line 3: asbuild-demo#15 (95cfccb) and auto-job-search#19 (aa0777e) merged by the owner, both repositories on v0.4.1. Walkthrough: first skipped (D55), then run by the owner's reversal (D56): run 7, 2026-11-21T00:34Z, NO BLOCKER FOUND, F2 not seen again, new F3 LOW (K11). Budget 4 agent hours (stop 6), 0.4 owner hours (stop 1), reviews $20 (stop $30), 2 working days. Used: about 1.8 agent hours, about 0.15 owner hours, reviews $20.72, walker $0.50; working day 1 of 2.
- v0.4.2, the final product (D60, plan `docs/plans/v0.4.2.md`): built on `release/v0.4.2`, hevelius-ai/asbuild#53 (draft until #52 merges; it carries #52's records). The five kept ideas; review round 1 BLOCK x3 (4 MEDIUM, fixed), round 2 APPROVE x3; local gate 681 passed, 100%; engine pin dc377ab. Release steps after the merge: the owner publishes `v0.4.2`; the tag check; setup's updates in asbuild-demo and auto-job-search; the plugin here; the walkthrough re-check (a new test repository on the owner's yes). Budget 6 agent hours (stop 8), 0.5 owner hours (stop 1), reviews $45 (stop $60), 2 working days; used about 1.5 agent hours, reviews $12.26.
- The parked-ideas review (D59): **done** 2026-11-21T03:35Z. Fable 5.2 led; of 81 parked items 5 KEEP, 4 MERGE, 72 REMOVE (`docs/plans/parked-review.md`); `docs/PARKING.md` keeps the five, ranked, and four new ideas not evaluated. Spent $29.72 of $90 (stop $110); about 2.2 agent hours of 4 (stop 6). The summary is the document "AsBuild: ideas worth building (parked-ideas review)" (https://claude.ai/artifact/3fgCU8NyeSYiw3KF4xMN5C).
- v0.4.0, TypeScript and JavaScript (D47 to D53): done 2026-11-20T22:19Z (the log holds its release steps).
- The board: https://claude.ai/artifact/5b6CiKgT3pouct5UKN1TUu, fed by the linked Haiku keeper.
- Branches in `hevelius-ai/asbuild`: `main`; `records/parked-review`; `release/v0.4.2`. In `hevelius-ai/asbuild-proofs`: `proof/m2-live-bases` (the base apps), `proof/m3-story` (M3's Windows runs), `proof/walkthrough-app` (the walkthrough app, b5d6308, D57). In `hevelius-ai/auto-job-search`: `build/S4` (the closed #14, the evidence of Core's done line 1).
- AsBuild test repositories: `hevelius-ai/asbuild-t5` (private, D59's proof T5; no pull request, nothing pushed by the session), for the owner to delete when they choose. A later walkthrough makes a new one from `proof/walkthrough-app`. The archived `agile-dev-team` repositories stay (the owner's choice).
- AsBuild 0.4.1 is installed on this computer (`claude plugin update`, 2026-11-21).
- Plan usage reset on 2026-11-17 (next reset 2026-11-24T09:00Z).

## Open pull requests and merge order

1. hevelius-ai/asbuild#52 `records/parked-review`: the parked-ideas review's records (D59). Merge first.
2. hevelius-ai/asbuild#53 `release/v0.4.2`: the release (D60); it already carries #52's commits, so after #52 it shows only v0.4.2's own change. Draft until #52 merges.

## Running jobs

None.

## Open decisions

None. (Docker: the owner's standing yes, D52, 2026-11-18.)

## QUALITY RISK

None. (D55's accepted risk, no walkthrough for v0.4.1, closed by run 7, D56.)

## Next steps

1. The owner merges #52, then #53 (once marked ready), then publishes `v0.4.2`; then the release steps in the plan. `hevelius-ai/asbuild-t5` is for the owner to delete.
4. After v0.4.2 AsBuild is the final product (D60): nothing more is built unless a real user asks. Building restarts only for a real user's request (playbook 1.2).
2. Known issues: none open once v0.4.2 is released (K11 fixed in it).
3. The three shared skills hold the five D57 edits (saved by the owner, checked 2026-11-21).
