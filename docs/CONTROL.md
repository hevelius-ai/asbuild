# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now
- v0.4.0, TypeScript and JavaScript (D47 design, D48 plan, D50 budget): **paused by the owner until the weekly usage reset (2026-11-17T09:00Z)**; then M2 Test job on `m2/test-job` (draft plan `docs/plans/v0.4-M2.md`, to be reviewed at M2's start). Budget 33 agent hours (report 26, stop 40), 5 owner hours (report 4, stop 7), 10 working days, reviews $250 (report $200, stop $300). Used: about 5.3 agent hours, 0.3 owner hours, reviews $75.02. Working day 2 of 10.
- M1 Engine: hevelius-ai/asbuild#39 merged at 2026-11-15T16:42:25Z (defee5c). M1b safety fixes (D50): hevelius-ai/asbuild#40 merged by chrisz-glitch at 2026-11-15T18:00:04Z (e6eda0d); `m1b/safety` deleted on both sides.
- D49: M1 to M3 merge into `main`; `v0.4.0` is released when everything is ready. Until then a repository newly set up from `main` gets workflows whose engine check stops (fails closed), and a plugin updated from `main` with older workflow files gets "no verdict yet" from `/asbuild:verdict` (D50).
- Milestones left: M2 Test job (6 to 9 h), M3 Story and setup (5 to 8 h), M4 Release (3 to 5 h).
- The board: https://claude.ai/artifact/5b6CiKgT3pouct5UKN1TUu, fed by the linked Haiku keeper.
- Branches in `hevelius-ai/asbuild`: `main`; `m2/test-job` (the plan and these records only).
- Fable 5.2 is at its weekly usage limit until 2026-11-17T09:00Z (its lens then on Opus 5.5 at max). Plan usage is above 80%: checked at every step; all agent tasks pause at 97%.

## Open pull requests and merge order

None.

## Running jobs

None.

## Open decisions

- Docker for local Linux checks: the image (named with its exact version and digest) waits for the owner's yes; until then Linux checks run on GitHub runners.

## QUALITY RISK

None open. The last one (M0's result files left out by `.gitignore`, opened 2026-11-15T01:4xZ) closed when CI went green on 3dd377a (about 15:15Z); its prevention, the fresh-clone check, is in the project skill.

## Next steps

1. After the reset: M2 Test job, from `docs/plans/v0.4-M2.md` (review the draft plan first; lay out the live repository and merges there for the owner).
2. Known issues: 3 open, K4 (LOW, found 14 Nov), K7 and K8 (found 15 Nov, for the release review).
