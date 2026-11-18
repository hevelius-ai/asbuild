# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now
- v0.4.0, TypeScript and JavaScript (D47 design, D48 plan, D50 budget): M2 Test job merged (hevelius-ai/asbuild#41, 80667f3); M3 Story and setup merged (hevelius-ai/asbuild#42, 0555bfd); next M4 Release on `m4/release`. Budget 33 agent hours (report 26, stop 40), 5 owner hours (report 4, stop 7), 10 working days, reviews $250 (report $200, stop $300). Used: about 11.3 agent hours, 0.5 owner hours, reviews $149.29. Working day 3 of 10.
- D51 (2026-11-17): the private live repository `hevelius-ai/asbuild-live`, where the build session sets `main` directly and merges nothing; one Node 24 step in AsBuild's CI.
- D49: M1 to M3 merge into `main`; `v0.4.0` is released when everything is ready (repositories newly set up from `main` fail closed until then; D50 on `/asbuild:verdict`).
- Milestones left: M4 Release (3 to 5 h).
- The board: https://claude.ai/artifact/5b6CiKgT3pouct5UKN1TUu, fed by the linked Haiku keeper.
- Branches in `hevelius-ai/asbuild`: `main`; `m4/release`. In `hevelius-ai/asbuild-proofs`: `proof/m2-live-bases` (the base apps), `proof/m3-story` (M3's Windows runs).
- Plan usage reset on 2026-11-17 (next reset 2026-11-24T09:00Z); Fable 5.2 available again.

## Open pull requests and merge order

None. M4's pull request opens from `m4/release`.

## Running jobs

None.

## Open decisions

None. (Docker: the owner's standing yes, D52, 2026-11-18.)

## QUALITY RISK

None open. The last one (M0's result files left out by `.gitignore`, opened 2026-11-15T01:4xZ) closed when CI went green on 3dd377a (about 15:15Z); its prevention, the fresh-clone check, is in the project skill.

## Next steps

1. M4 Release: plan, the version 0.4.0 in the four workflow files, review, the owner publishes `v0.4.0`, the demo's four pull requests re-run (done line 2), the release walkthrough (done line 3), the owner's own try.
2. Known issues: 4 open, K4 (LOW, found 14 Nov), K7 and K8 (found 15 Nov), K9 (found 18 Nov), all for the release review.
3. `hevelius-ai/asbuild-live` (private, throwaway, D51) stays until the owner chooses to delete it.
