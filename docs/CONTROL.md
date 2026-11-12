# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S4 in progress (the demo, the README and the real stories). Its README part merged 2026-11-11: hevelius-ai/asbuild#4 (README, 4660b50) and #5 (the plugin folder's README for the directory, f59e1a0), and hevelius-ai/asbuild-demo#9 (the demo's README, 20ae52c), all by chrisz-glitch at 13:45Z to 13:46Z. The clean-install CI job (D29) merged 14:30Z: hevelius-ai/asbuild#6 (0db08d3). S1, S2 and S3 done.
- Branches in `hevelius-ai/asbuild`: `main`; `fix/default-branch` (PR #10: the F2 and F1 fix, `v0.2.1`, with the walkthrough records).
- Walkthrough (D27, D31, D33 to D35): verdict BLOCKER FOUND. S1, S2 repeat in `hevelius-ai/asbuild-walkthrough-1b`: INCOMPLETE, 15 PASS, LOW 5. Run 2 (S3, S4) in `hevelius-ai/asbuild-walkthrough-2`: BLOCKER FOUND, F2 HIGH, F1 MEDIUM, LOW 2. Run 1 in `hevelius-ai/asbuild-walkthrough` was stopped by the setup (D35). The three test repositories stay as evidence; reports in the walkthrough folders outside the repositories (never committed).
- Demo: the four verdict PRs stay open as the demo: #3 PROVEN, #4 NOT PROVEN, #5 WAITING FOR YOU (weakened check), #6 UNRESOLVED; #7 WAITING FOR YOU (no story; may now conflict with the merged demo README, its posted verdict stays); #8 S2's story PR, WAITING FOR YOU.
- auto-job-search (private): story S1, the personal-data scan, approved (#2, merged 13:39Z, 4022c68). Its build, #3, was PROVEN (S1-C1 to S1-C3 work; 33 other tests, 0 broken) after three review rounds, the owner's decision 4A and a confirm-only re-check, and merged by chrisz-glitch at 13:51Z (bc9ff68). 1 of 3 real stories done. E1-S1's gate (criteria 1 and 4), setup PR #4, merged by chrisz-glitch at 14:30Z (3e8fb4b) after three review rounds, the owner's decision 7A and a confirm-only re-check; the gate passes on main. E1-S1 is complete. Story S2 (E1-S2, data folder layout and settings) approved: #5, merged 15:49Z (5a2fbe9), after the gate stopped running story checks (decision 9A: #6, 15:40Z, be01a28; wording #7, 15:46Z, 098994a). Build S2, #8 (branch `build/S2`, head 6a89bfe): PROVEN (S2-C1 to S2-C4 work; 125 other tests, 0 broken), all checks green; three review rounds, the owner's decision 10A (fix all five round 3 items) and a confirm-only re-check APPROVE; merged by chrisz-glitch at 18:19Z (96b0e10); `build/S2` deleted on both sides. 2 of 3 real stories done; E1-S2 is complete. Story S3 (E1-S3, model wrapper with the credential order): the owner approved the five-line checklist (4 tries in all; prices kept in the app; a model with no price asks yes/no and records the cost as unknown); five locked checks against a pretend Anthropic on the same computer; story PR #9 merged by chrisz-glitch at 20:19Z (1904113); `story/S3` deleted on both sides. The owner chose 11A (Anthropic's Python library, pinned to 2.3.0; wheel checked against PyPI's hash; local environment `venvs/ajs` beside the repositories). Blocker: anthropic 2.x sends every key as `Authorization: Bearer` (documented change), but the locked S3-C1 expects `x-api-key` for the saved key and the setting, so build S3 cannot pass it with 11A; the owner chose 12A. #10 (S3-C1 accepts either header, 8879294) and #11 (`anthropic==2.3.0`, 74a4c15) merged by chrisz-glitch at 22:24Z, after GitHub's Actions outage (runs queued from 20:19Z; fresh runs started with empty commits at 22:10Z). Build S3, #12 (`build/S3`, head c221220): PROVEN (S3-C1 to S3-C5 work; 232 other tests, 0 broken), all checks green; review round 1 (1 HIGH, 9 MEDIUM, all confirmed and fixed), round 2 APPROVE; merged by chrisz-glitch at 00:40Z on 12 Nov (f7ba459); `build/S3` deleted on both sides. 3 of 3 real stories done; E1-S3 is complete. Story S4 (E1-S4, sample data, licence and credit line; for the NOT PROVEN build): the owner approved the four-line checklist (credit line names Christopher Zaczek; 13A: line 1 keeps three examples); checks proved against a throwaway build and locked; story PR #13 merged by chrisz-glitch at 01:55Z (86e8ac3); `story/S4` deleted on both sides. Build S4, #14 (`build/S4`, b2a9e71, deliberately incomplete, do not merge): NOT PROVEN, the receipt names S4-C4 as not working yet (S4-C1 to S4-C3 work; 237 other tests, 0 broken); it stays open as evidence. Done line 1 is met. The release (D18, D32): hevelius-ai/asbuild#8 merged 2026-11-12 15:24Z (4b5ba03); the owner published the release `v0.2.0` at 15:26Z, its tag on 4b5ba03; the pin PRs hevelius-ai/asbuild-demo#10 (c0ce45b) and hevelius-ai/auto-job-search#15 (abbbd43) merged 15:32Z, both WAITING FOR YOU before the merge as expected. A fresh verdict on auto-job-search#14, run from the pinned main, cloned AsBuild at `v0.2.0` and posted NOT PROVEN again (15:36Z, run 43249553548).
- Away protocol (D30) ended 2026-11-11T20:24Z when the owner answered.

## Open pull requests and merge order

Merge when it is green and reviewed: hevelius-ai/asbuild#10 (`fix/default-branch`). auto-job-search#14 stays open, never merged. The demo PRs #3 to #8 stay open.

## Running jobs

None.

## Open decisions

None. Decision 14 was answered 14A (D32).

## QUALITY RISK

- Walker 2 changed its test repository's default branch twice, beyond the brief's allowance (merging); it restored `main` (checked 16:48Z). Suggested to the owner: name repository settings in walker rule 12.

## Next steps

1. The F2 fix (D36): review, the owner merges #10, the owner publishes `v0.2.1` on its merge commit, one pin PR each in asbuild-demo and auto-job-search, a fresh verdict; then a fresh walker repeats only run 2's failed rows (S3-1, S3-3a) once, in a new, empty test repository. Then the owner's try, and the directory submission.
