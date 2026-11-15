# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now
- v0.4.0, TypeScript and JavaScript (D47 design, D48 plan): M1 Engine in progress on `m1/engine` since 2026-11-15T15:21Z. Budget 33 agent hours (D50; report 26, stop 40), 5 owner hours (report 4, stop 7), 10 working days, reviews $250 (report $200, stop $300). Used: about 2.7 agent hours, 0.15 owner hours, reviews $33.43. Working day 2 of 10.
- M0 Ground: hevelius-ai/asbuild#38 merged by chrisz-glitch at 2026-11-15T15:20:39Z (324ce35); the 48-row conformance table is locked (changing a row is an owner decision).
- Milestones: M1 Engine (6 to 9 h), M2 Test job (6 to 9 h), M3 Story and setup (5 to 8 h), M4 Release (3 to 5 h).
- The board: https://claude.ai/artifact/5b6CiKgT3pouct5UKN1TUu, fed by the linked Haiku keeper.
- Branches in `hevelius-ai/asbuild`: `main`; `m1/engine`.
- D50: the AsChecked safety fixes (B5, B4-A) on `m1b/safety`, built on #39; plan `docs/plans/v0.4-M1b.md`.
- D49: M1 to M3 merge into `main`; `v0.4.0` is released when everything is ready. Until then a repository newly set up from `main` gets workflows whose engine check stops (fails closed).

## Open pull requests and merge order

None yet: M1's pull request opens when its gate is green and a fresh clone passes.

## Running jobs

None.

## Open decisions

- Docker for local Linux checks: the image (named with its exact version and digest) waits for the owner's yes; until then Linux checks run on GitHub runners.

## QUALITY RISK

None open. The last one (M0's result files left out by `.gitignore`, opened 2026-11-15T01:4xZ) closed when CI went green on 3dd377a (about 15:15Z); its prevention, the fresh-clone check, is in the project skill.

## Next steps

1. M1 Engine: `docs/plans/v0.4-M1.md`. Tests first: `CURRENT = "M1"` in the conformance suite, then the engine changes, row by row.
2. Then M2 Test job.
3. Known issues: 1 open, K4 (LOW, found 14 Nov).
