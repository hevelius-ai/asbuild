# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S3 (the install page) in review: hevelius-ai/asbuild#3 from `build/S3`, round 3 APPROVE, CI green; waiting for the owner's merge. Decision D26 (the owner's S3-1): one deny line per story, added by the story-time checks. S1 and S2 done 2026-11-10.
- Branches in `hevelius-ai/asbuild`: `main` and `build/S3`. S2's records ride in S3's PR.
- Demo: setup (ef2d91b) and story S1 (e681f36) merged. Open demo PRs, not for merging (S4's demo): #3 PROVEN, #4 NOT PROVEN, #5 WAITING FOR YOU (weakened check), #6 UNRESOLVED, #7 WAITING FOR YOU (no story). #8 is S2's live-run story PR (story S2, count lines), WAITING FOR YOU; merging it is optional.
- auto-job-search: does not exist yet. After S3's merge: create it private (HANDOVER section 2), follow the install page on it word for word (criterion 1's live half), the owner merges its wiring PR, then its first story with `/asbuild:story`.

## Open pull requests and merge order

1. hevelius-ai/asbuild#3 (`build/S3`): merge now. Nothing else waits on it in this repository.
2. After it: the auto-job-search wiring PR (to be opened by the live run).

The demo PRs #3 to #8 stay open.

## Running jobs

None.

## Open decisions

None.

## QUALITY RISK

None.

## Next steps

1. Owner merges hevelius-ai/asbuild#3.
2. Create `hevelius-ai/auto-job-search` (private), then a headless session follows the install page on it word for word; the owner merges its wiring PR.
3. Its first story with `/asbuild:story`: that pull request's verdict closes S3's criterion 1. Then S3's records and S4.
