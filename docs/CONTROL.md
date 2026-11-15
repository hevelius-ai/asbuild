# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now
- v0.4.0, TypeScript and JavaScript (D47 design, D48 plan): M0 Ground in progress on `m0/ground` since 2026-11-15T00:53Z. Budget 30 agent hours (report 24, stop 37), 5 owner hours (report 4, stop 7), 10 working days, reviews $250 (report $200, stop $300). Used: 0 agent hours, 0 owner hours of the build (the design's 2.3 and 0.3 are counted apart). Working day 1 of 10.
- Milestones: M0 Ground (4 to 6 h), M1 Engine (6 to 9 h), M2 Test job (6 to 9 h), M3 Story and setup (5 to 8 h), M4 Release (3 to 5 h).
- The board: https://claude.ai/artifact/5b6CiKgT3pouct5UKN1TUu, fed by the linked Haiku keeper.
- v0.3.4 and everything before it: closed; its last "Now" text is in the log.
- Branches in `hevelius-ai/asbuild`: `main`; `m0/ground`.

## Open pull requests and merge order

None yet: M0's pull request opens when its gate is green.

## Running jobs

- Away protocol (owner, 15 Nov 00:5xZ): keep-awake hold on; heartbeat cron in this session.

## Open decisions

- Docker for local Linux checks: the image (named with its exact version and digest) waits for the owner's yes; until then Linux checks run on GitHub runners.

## QUALITY RISK

None open. The early-merge item (#34 merged before its review finished, opened 17:43Z) closed at 21:46Z: the review fixes #35 were approved and merged before `v0.3.4` was published.

## Next steps

1. M0: the task plan `docs/plans/v0.4-M0.md`; the open proofs (P-CI-1, P-ENG-1, lock parity, P-WIN-1, P-VITE8); the conformance harness, level 1, with the Python column and v0.4.0's agreed case table; Python golden files from v0.3.4; Docker for local Linux checks (the image needs the owner's yes).
2. Then M1 Engine, under the three-model review and the scope guard (D48).
3. Known issues: 1 open, K4 (LOW, found 14 Nov).
