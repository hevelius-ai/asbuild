# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S2 (the skill and story-time checks), built on branch `build/S2` (local, not pushed): plan, acceptance tests, plugin, skill, script. Live run and review round 1 running. S1 done 2026-11-10.
- Branch `build/S1` in `hevelius-ai/asbuild`: merged and deleted on both sides (2026-11-10, at the owner's request).
- Demo: setup (ef2d91b) and story S1 (e681f36) merged. Open demo PRs, not for merging (S4's demo): #3 PROVEN, #4 NOT PROVEN, #5 WAITING FOR YOU (weakened check), #6 UNRESOLVED, #7 WAITING FOR YOU (no story).

## Open pull requests and merge order

None to merge now. The demo PRs #3 to #7 stay open for S4. S2's PR (from `build/S2`, which carries the S1 records) opens after review.

## Running jobs

- Live run of `/asbuild:story` on a clone of the demo (headless, claude-sonnet-5-5), started 2026-11-10T20:26Z; output in the session scratchpad; wakes the build session when it ends.
- Review round 1 of S2 (claude-fable-5-2, read-only), started 2026-11-10T20:26Z; wakes the build session when it ends.

## Open decisions

None.

## QUALITY RISK

None.

## Next steps

1. S2: live run evidence, review rounds, then the PR (one owner merge).
2. S3: the install page.
