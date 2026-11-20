# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now
- v0.4.0, TypeScript and JavaScript (D47 design, D48 plan, D50 budget, D53 M4a): **done** 2026-11-20T22:19Z. Published 2026-11-18T19:34:38Z on 44eaa0b (hevelius-ai/asbuild#43, after M4a #44, 07d7748); tag checked (engine 191949f in all four workflow files; the `v*` ruleset active). Budget 33 agent hours (report 26, stop 40), 5 owner hours (report 4, stop 7), 10 working days, reviews $250 (report $200, stop $300). Used: about 19.5 agent hours, 1.55 owner hours, reviews $196.87, walkthroughs $1.23. Working day 4 of 10.
- Release steps all done: 1 the live run (28 of 28 on 4d0563b), 2 the publish, 3 the tag check, 4 the demo (#3 PROVEN, #4 NOT PROVEN, #5 WAITING FOR YOU, #6 UNRESOLVED, both jobs cloning `v0.4.0`), 5 the walkthrough (runs 6 and 6b, combined INCOMPLETE, no HIGH or MEDIUM; K10 LOW), 6 the owner's own try (`hevelius-ai/asbuild-try`, private: setup #1, story S1 #2, build #3 PROVEN, all merged by the owner, 15 minutes; two small things parked).
- D51 (2026-11-17): the private live repository `hevelius-ai/asbuild-live`, where the build session sets `main` directly and merges nothing; one Node 24 step in AsBuild's CI.
- The board: https://claude.ai/artifact/5b6CiKgT3pouct5UKN1TUu, fed by the linked Haiku keeper.
- Branches in `hevelius-ai/asbuild`: `main`; `m4/done`. In `hevelius-ai/asbuild-proofs`: `proof/m2-live-bases` (the base apps), `proof/m3-story` (M3's Windows runs).
- Throwaway private repositories: `hevelius-ai/asbuild-live`, `hevelius-ai/asbuild-walkthrough-6` (#5 open, the walker's WAITING FOR YOU build, left as evidence), `hevelius-ai/asbuild-try` (the owner's try).
- AsBuild 0.4.0 is installed on this computer from the README (by the walker, run 6).
- Plan usage reset on 2026-11-17 (next reset 2026-11-24T09:00Z).

## Open pull requests and merge order

1. `m4/done`: the records of release step 6 (this file, the log, hours, two parked lines, the M4 plan's step 6).

## Running jobs

None.

## Open decisions

None. (Docker: the owner's standing yes, D52, 2026-11-18.)

## QUALITY RISK

None open.

## Next steps

1. The owner merges `m4/done`; then nothing is planned. Building restarts only for a real user's request (playbook 1.2).
2. Known issues: 1 open, K10 (LOW, found 18 Nov), for the next release review.
3. `hevelius-ai/asbuild-live`, `hevelius-ai/asbuild-walkthrough-6` and `hevelius-ai/asbuild-try` (private, throwaway) stay until the owner chooses to delete them.
4. At this release: prune the skills (playbook 1.12).
