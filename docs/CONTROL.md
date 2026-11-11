# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S4 in progress (the demo, the README and the real stories). Its README part merged 2026-11-11: hevelius-ai/asbuild#4 (README, 4660b50) and #5 (the plugin folder's README for the directory, f59e1a0), and hevelius-ai/asbuild-demo#9 (the demo's README, 20ae52c), all by chrisz-glitch at 13:45Z to 13:46Z. S1, S2 and S3 done.
- Branches in `hevelius-ai/asbuild`: `main`; `build/S4-install` (PR #6, the clean-install job, D29), which holds the local `records/after-S4-readme` with these records.
- Demo: the four verdict PRs stay open as the demo: #3 PROVEN, #4 NOT PROVEN, #5 WAITING FOR YOU (weakened check), #6 UNRESOLVED; #7 WAITING FOR YOU (no story; may now conflict with the merged demo README, its posted verdict stays); #8 S2's story PR, WAITING FOR YOU.
- auto-job-search (private): story S1, the personal-data scan, approved (#2, merged 13:39Z, 4022c68). Its build, #3, was PROVEN (S1-C1 to S1-C3 work; 33 other tests, 0 broken) after three review rounds, the owner's decision 4A and a confirm-only re-check, and merged by chrisz-glitch at 13:51Z (bc9ff68). 1 of 3 real stories done. E1-S1's gate (criteria 1 and 4) is setup PR #4 from `setup/gate`: approved after three review rounds, the owner's decision 7A and a confirm-only re-check; gate CI green on Linux and Windows; AsBuild WAITING FOR YOU (protected setup files), as a setup PR should get.
- Night protocol ended 2026-11-11T13:37Z; the system log shows no sleep or wake overnight.

## Open pull requests and merge order

1. hevelius-ai/auto-job-search#4 (E1-S1's gate, a setup PR): approved; the owner's merge.
2. hevelius-ai/asbuild#6 (S4's clean-install job, D29, with the records): review round 3 blocked on a records-only finding; the owner chose 8A (this fix), then a confirm-only re-check, then the owner's merge. Independent of #4.
3. The demo PRs #3 to #8 stay open.

## Running jobs

None.

## Open decisions

None.

## QUALITY RISK

None.

## Next steps

1. auto-job-search#3 merged (story S1 done). Decisions 5 and 6 answered: D28, D29.
2. The owner merges auto-job-search#4 (decision 7 answered: 7A); then the second real story with `/asbuild:story`.
3. S4's clean-install CI job (D29), PR hevelius-ai/asbuild#6: proved on Linux and Windows runners (runs 43033832595 and 43035981859); review rounds 1 and 2 fixed, round 3 blocked on this file (decision 8 answered: 8A); confirm-only re-check, then the owner's merge.
4. The release (D18, D27): the owner tags; the pin PRs; the user walkthrough after re-loading the engineering skills from the synced folder; the owner's try. Then the directory submission (the owner's step).
