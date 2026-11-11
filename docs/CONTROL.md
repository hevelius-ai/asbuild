# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S4 in progress (the demo, the README and the real stories). Its README part merged 2026-11-11: hevelius-ai/asbuild#4 (README, 4660b50) and #5 (the plugin folder's README for the directory, f59e1a0), and hevelius-ai/asbuild-demo#9 (the demo's README, 20ae52c), all by chrisz-glitch at 13:45Z to 13:46Z. The clean-install CI job (D29) merged 14:30Z: hevelius-ai/asbuild#6 (0db08d3). S1, S2 and S3 done.
- Branches in `hevelius-ai/asbuild`: `main`; local `records/after-install` (these records; they go in with the next asbuild PR).
- Demo: the four verdict PRs stay open as the demo: #3 PROVEN, #4 NOT PROVEN, #5 WAITING FOR YOU (weakened check), #6 UNRESOLVED; #7 WAITING FOR YOU (no story; may now conflict with the merged demo README, its posted verdict stays); #8 S2's story PR, WAITING FOR YOU.
- auto-job-search (private): story S1, the personal-data scan, approved (#2, merged 13:39Z, 4022c68). Its build, #3, was PROVEN (S1-C1 to S1-C3 work; 33 other tests, 0 broken) after three review rounds, the owner's decision 4A and a confirm-only re-check, and merged by chrisz-glitch at 13:51Z (bc9ff68). 1 of 3 real stories done. E1-S1's gate (criteria 1 and 4), setup PR #4, merged by chrisz-glitch at 14:30Z (3e8fb4b) after three review rounds, the owner's decision 7A and a confirm-only re-check; the gate passes on main. E1-S1 is complete.
- Night protocol ended 2026-11-11T13:37Z; the system log shows no sleep or wake overnight.

## Open pull requests and merge order

None to merge. The demo PRs #3 to #8 stay open.

## Running jobs

None.

## Open decisions

None.

## QUALITY RISK

None.

## Next steps

1. The second real story in auto-job-search, E1-S2 (data folder layout and settings), with `/asbuild:story`: the owner answers its questions; then its build and verdict.
2. The third real story (E1-S3), and one build PR that misses its checks and gets NOT PROVEN.
3. The release (D18, D27): the owner tags; the pin PRs; the user walkthrough after re-loading the engineering skills from the synced folder; the owner's try. Then the directory submission (the owner's step).
