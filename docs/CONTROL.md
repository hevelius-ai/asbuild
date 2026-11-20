# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now
- v0.4.1, known issue K10 (D54, plan `docs/plans/v0.4.1.md`), on `release/v0.4.1`: the receipt says how to accept a change, and an unjudged line says it is still as agreed. Budget 4 agent hours (report 3, stop 6), 0.4 owner hours (stop 1), reviews $20 (report $15, stop $30), 2 working days. Used: about 0.5 agent hours.
- v0.4.0, TypeScript and JavaScript (D47 design, D48 plan, D50 budget, D53 M4a): **done** 2026-11-20T22:19Z. Published 2026-11-18T19:34:38Z on 44eaa0b (hevelius-ai/asbuild#43, after M4a #44, 07d7748); tag checked (engine 191949f in all four workflow files; the `v*` ruleset active). Budget 33 agent hours (report 26, stop 40), 5 owner hours (report 4, stop 7), 10 working days, reviews $250 (report $200, stop $300). Used: about 19.5 agent hours, 1.65 owner hours, reviews $196.87, walkthroughs $1.23. Working day 4 of 10.
- Release steps all done: 1 the live run (28 of 28 on 4d0563b), 2 the publish, 3 the tag check, 4 the demo (#3 PROVEN, #4 NOT PROVEN, #5 WAITING FOR YOU, #6 UNRESOLVED, both jobs cloning `v0.4.0`), 5 the walkthrough (runs 6 and 6b, combined INCOMPLETE, no HIGH or MEDIUM; K10 LOW), 6 the owner's own try (`hevelius-ai/asbuild-try`, private: setup #1, story S1 #2, build #3 PROVEN, all merged by the owner, 15 minutes; two small things parked).
- D51 (2026-11-17): the private live repository `hevelius-ai/asbuild-live`, where the build session set `main` directly and merged nothing; deleted by the owner 2026-11-20, so a later live run needs a new one.
- The board: https://claude.ai/artifact/5b6CiKgT3pouct5UKN1TUu, fed by the linked Haiku keeper.
- Branches in `hevelius-ai/asbuild`: `main`; `release/v0.4.1`. In `hevelius-ai/asbuild-proofs`: `proof/m2-live-bases` (the base apps), `proof/m3-story` (M3's Windows runs).
- All AsBuild test repositories were deleted by the owner on 2026-11-20: v0.4.0's (`asbuild-live`, `asbuild-walkthrough-6`, `asbuild-try`) and the older ones (`asbuild-walkthrough-3` to `-5`, `asbuild-owner-try`, `asbuild-owner-try2`). The archived `agile-dev-team` repositories stay (the owner's choice).
- AsBuild 0.4.0 is installed on this computer from the README (by the walker, run 6).
- Plan usage reset on 2026-11-17 (next reset 2026-11-24T09:00Z).

## Open pull requests and merge order

1. `release/v0.4.1` (v0.4.1, D54): K10's fix, the version, the records. Its number, checks and review are added when it opens.

## Running jobs

None.

## Open decisions

None. (Docker: the owner's standing yes, D52, 2026-11-18.)

## QUALITY RISK

None open.

## Next steps

1. v0.4.1's review, then the owner merges and publishes it; then release steps 3 to 6 (plan `docs/plans/v0.4.1.md`).
2. Known issues: none open (K10 fixed in v0.4.1, once merged).
3. The skills pruned at this release (playbook 1.12), in the same pull request.
