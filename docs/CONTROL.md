# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S4 in progress (the demo, the README and the real stories). Its README part merged 2026-11-11: hevelius-ai/asbuild#4 (README, 4660b50) and #5 (the plugin folder's README for the directory, f59e1a0), and hevelius-ai/asbuild-demo#9 (the demo's README, 20ae52c), all by chrisz-glitch at 13:45Z to 13:46Z. S1, S2 and S3 done.
- Branches in `hevelius-ai/asbuild`: `main`; local `records/after-S4-readme` (these records; it goes in with the next asbuild PR).
- Demo: the four verdict PRs stay open as the demo: #3 PROVEN, #4 NOT PROVEN, #5 WAITING FOR YOU (weakened check), #6 UNRESOLVED; #7 WAITING FOR YOU (no story; may now conflict with the merged demo README, its posted verdict stays); #8 S2's story PR, WAITING FOR YOU.
- auto-job-search (private): story S1, the personal-data scan, approved (#2, merged 13:39Z, 4022c68). Its build, #3 from `build/S1`, is PROVEN (S1-C1 to S1-C3 work; 33 other tests, 0 broken) after three review rounds, the owner's decision 4A and a confirm-only re-check. 1 of 3 real stories.
- Night protocol ended 2026-11-11T13:40Z; the system log shows no sleep or wake overnight.

## Open pull requests and merge order

1. hevelius-ai/auto-job-search#3 (build S1, PROVEN): merge now.
2. The demo PRs #3 to #8 stay open.

## Running jobs

None.

## Open decisions

- Decision 6, the clean-install CI job in the synced `engineering-build-loop` 2.4: keep it out of Core as D27 records (6A, recommended) or add it to S4 (6B).

## QUALITY RISK

None.

## Next steps

1. Owner merges auto-job-search#3, and answers 6. Decision 5 answered: D28.
2. E1-S1's gate (criteria 1 and 4) in its own setup PR (D28); then the second real story with `/asbuild:story`.
3. The release (D18, D27): the owner tags; the pin PRs; the user walkthrough after re-loading the engineering skills from the synced folder; the owner's try. Then the directory submission (the owner's step).
