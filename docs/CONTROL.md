# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S2 (the skill and story-time checks): draft PR hevelius-ai/asbuild#2 from `build/S2`. Live run done (demo story PR hevelius-ai/asbuild-demo#8, WAITING FOR YOU). Review round 3 approved; a confirm-only re-check of one small fix next. S1 done 2026-11-10.
- Branch `build/S1` in `hevelius-ai/asbuild`: merged and deleted on both sides (2026-11-10, at the owner's request).
- Demo: setup (ef2d91b) and story S1 (e681f36) merged. Open demo PRs, not for merging (S4's demo): #3 PROVEN, #4 NOT PROVEN, #5 WAITING FOR YOU (weakened check), #6 UNRESOLVED, #7 WAITING FOR YOU (no story). #8 is S2's live-run story PR (story S2, count lines), WAITING FOR YOU; merging it is optional.

## Open pull requests and merge order

None to merge now. hevelius-ai/asbuild#2 (S2, carrying the S1 records) is a draft until review approves and CI is green; it is then the one PR to merge. The demo PRs #3 to #8 stay open.

## Running jobs

None between steps; each review round runs in the background and wakes the build session.

## Open decisions

None.

## QUALITY RISK

None.

## Next steps

1. S2: the confirm-only re-check of the round 3 note, CI green, then PR #2 marked ready for the owner's merge.
2. S3: the install page.
