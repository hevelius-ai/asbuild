# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S4 in progress (the demo, the README and the real stories). Its README part merged 2026-11-11: hevelius-ai/asbuild#4 (README, 4660b50) and #5 (the plugin folder's README for the directory, f59e1a0), and hevelius-ai/asbuild-demo#9 (the demo's README, 20ae52c), all by chrisz-glitch at 13:45Z to 13:46Z. The clean-install CI job (D29) merged 14:30Z: hevelius-ai/asbuild#6 (0db08d3). S1, S2 and S3 done.
- Branches in `hevelius-ai/asbuild`: `main`; local `records/after-install` (these records; they go in with the next asbuild PR).
- Demo: the four verdict PRs stay open as the demo: #3 PROVEN, #4 NOT PROVEN, #5 WAITING FOR YOU (weakened check), #6 UNRESOLVED; #7 WAITING FOR YOU (no story; may now conflict with the merged demo README, its posted verdict stays); #8 S2's story PR, WAITING FOR YOU.
- auto-job-search (private): story S1, the personal-data scan, approved (#2, merged 13:39Z, 4022c68). Its build, #3, was PROVEN (S1-C1 to S1-C3 work; 33 other tests, 0 broken) after three review rounds, the owner's decision 4A and a confirm-only re-check, and merged by chrisz-glitch at 13:51Z (bc9ff68). 1 of 3 real stories done. E1-S1's gate (criteria 1 and 4), setup PR #4, merged by chrisz-glitch at 14:30Z (3e8fb4b) after three review rounds, the owner's decision 7A and a confirm-only re-check; the gate passes on main. E1-S1 is complete. Story S2 (E1-S2, data folder layout and settings) approved: #5, merged 15:49Z (5a2fbe9), after the gate stopped running story checks (decision 9A: #6, 15:40Z, be01a28; wording #7, 15:46Z, 098994a). Build S2, #8 (branch `build/S2`, head 1cc195e): PROVEN (S2-C1 to S2-C4 work; 117 other tests, 0 broken), all checks green; review round 3 blocked on three MEDIUM findings (no HIGH), so the build stops for the owner's decision 10 (one page: `build-S2-round3.md` in the owner's work folder, outside the repositories).
- Away protocol (D30) active since 2026-11-11T15:52Z.

## Open pull requests and merge order

auto-job-search#8 (build S2): waits on decision 10; not ready to merge. The demo PRs #3 to #8 stay open.

## Running jobs

- Away heartbeat: cron c2c1a600 (every 10 minutes) and the keep-awake hold; stopped when the owner is back.

## Open decisions

- 10 (build S2 after round 3): A fix all five and a confirm-only re-check (lean); B merge as it is with the five listed as known issues; C fix only finding 1 (the CV-name regression).

## QUALITY RISK

None.

## Next steps

1. Build S2 (auto-job-search#8): act on decision 10, then the owner's merge.
2. The third real story (E1-S3), and one build PR that misses its checks and gets NOT PROVEN.
3. The release (D18, D27): the owner tags; the pin PRs; the user walkthrough after re-loading the engineering skills from the synced folder; the owner's try. Then the directory submission (the owner's step).
