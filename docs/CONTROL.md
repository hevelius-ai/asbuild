# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now
- v0.4.0, TypeScript and JavaScript (D47 design, D48 plan, D50 budget): M1b safety fixes on `m1b/safety` since 2026-11-15T16:40Z; M1 merged. Budget 33 agent hours (D50; report 26, stop 40), 5 owner hours (report 4, stop 7), 10 working days, reviews $250 (report $200, stop $300). Used: about 5.3 agent hours, 0.3 owner hours, reviews $75.02. Working day 2 of 10.
- M1 Engine: hevelius-ai/asbuild#39 merged by chrisz-glitch at 2026-11-15T16:42:25Z (defee5c); `m1/engine` deleted on both sides.
- D50: the AsChecked safety fixes (B5 pytest settings files; B4-A the verdict skill reads only AsBuild's saved verdict); plan `docs/plans/v0.4-M1b.md`.
- D49: M1 to M3 merge into `main`; `v0.4.0` is released when everything is ready. Until then a repository newly set up from `main` gets workflows whose engine check stops (fails closed).
- Milestones left: M2 Test job (6 to 9 h), M3 Story and setup (5 to 8 h), M4 Release (3 to 5 h).
- The board: https://claude.ai/artifact/5b6CiKgT3pouct5UKN1TUu, fed by the linked Haiku keeper.
- Branches in `hevelius-ai/asbuild`: `main`; `m1b/safety`.
- Fable 5.2 is at its weekly usage limit until 2026-11-17T09:00Z: its review lens runs on Opus 5.5 at max effort. Plan usage is above 80%: checked at every step; all agent tasks pause at 97%.

## Open pull requests and merge order

None yet: M1's pull request opens when its gate is green and a fresh clone passes.

## Running jobs

None.

## Open decisions

- Docker for local Linux checks: the image (named with its exact version and digest) waits for the owner's yes; until then Linux checks run on GitHub runners.

## QUALITY RISK

None open. The last one (M0's result files left out by `.gitignore`, opened 2026-11-15T01:4xZ) closed when CI went green on 3dd377a (about 15:15Z); its prevention, the fresh-clone check, is in the project skill.

## Next steps

1. M1b: the pull request, the three-lens review, the owner's merge.
2. Then M2 Test job (the live run also checks the saved verdict file of D50).
3. Known issues: 3 open, K4 (LOW, found 14 Nov), K7 and K8 (found 15 Nov, for the release review).
