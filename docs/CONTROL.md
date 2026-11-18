# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now
- v0.4.0, TypeScript and JavaScript (D47 design, D48 plan, D50 budget, D53 M4a): **published** 2026-11-18T19:34:38Z on 44eaa0b (hevelius-ai/asbuild#43, after M4a #44, 07d7748); tag checked (engine 191949f in all four workflow files; the `v*` ruleset active). Budget 33 agent hours (report 26, stop 40), 5 owner hours (report 4, stop 7), 10 working days, reviews $250 (report $200, stop $300). Used: about 19.2 agent hours, 1.2 owner hours, reviews $196.87, walkthroughs $1.23. Working day 3 of 10.
- Release steps done: 1 the live run (28 of 28 on 4d0563b), 2 the publish, 3 the tag check, 4 the demo (asbuild-demo#14 merged, f2dffa6; #3 PROVEN, #4 NOT PROVEN, #5 WAITING FOR YOU, #6 UNRESOLVED, both jobs cloning `v0.4.0`), 5 the walkthrough (runs 6 and 6b, combined INCOMPLETE: no HIGH or MEDIUM; D3-C1 PROVEN reached; J1-C1 NOT CHECKED, J1-C3 and J1-C6 UNCLEAR; K10 LOW). Left: 6 the owner's own try.
- D51 (2026-11-17): the private live repository `hevelius-ai/asbuild-live`, where the build session sets `main` directly and merges nothing; one Node 24 step in AsBuild's CI.
- The board: https://claude.ai/artifact/5b6CiKgT3pouct5UKN1TUu, fed by the linked Haiku keeper.
- Branches in `hevelius-ai/asbuild`: `main`; `m4/records`. In `hevelius-ai/asbuild-proofs`: `proof/m2-live-bases` (the base apps), `proof/m3-story` (M3's Windows runs). `hevelius-ai/asbuild-walkthrough-6` (private): #1 to #4 merged, #5 open (the walker's WAITING FOR YOU build, left as evidence).
- AsBuild 0.4.0 is installed on this computer from the README (by the walker, run 6).
- Plan usage reset on 2026-11-17 (next reset 2026-11-24T09:00Z).

## Open pull requests and merge order

1. `m4/records`: the release records (this file, the log, hours, K10, two parked lines, the M4 plan's results).

## Running jobs

None.

## Open decisions

None. (Docker: the owner's standing yes, D52, 2026-11-18. W-1 answered A.)

## QUALITY RISK

None open. The last one (2026-11-18T19:53Z: a walker re-check started before its brief was on disk; the write was refused, so it ran nothing) closed at once; prevention: a run starts only after its brief is confirmed on disk, in a later step.

## Next steps

1. The owner's own try (release step 6, about 1 hour), in a repository of the owner's choice; then v0.4.0 is done.
2. Known issues: 1 open, K10 (LOW, found 18 Nov), for the next release review.
3. `hevelius-ai/asbuild-live` and `hevelius-ai/asbuild-walkthrough-6` (private, throwaway) stay until the owner chooses to delete them.
