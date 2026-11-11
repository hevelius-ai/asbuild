# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S3 done 2026-11-11 (hevelius-ai/asbuild#3 merged by chrisz-glitch at 2026-11-10T22:43Z, 4402c85; the install page followed live on auto-job-search; its first story PR got its verdict). S4 in progress: its README is hevelius-ai/asbuild#4 from `build/S4` (with S3's records and D27), and the demo's README is hevelius-ai/asbuild-demo#9. S1 and S2 done 2026-11-10.
- Branches in `hevelius-ai/asbuild`: `main`; `build/S4` (local, from `records/after-S3`, which holds D27 and these records; both go in with S4's PR).
- Demo: setup (ef2d91b) and story S1 (e681f36) merged. Open demo PRs, not for merging (S4's demo): #3 PROVEN, #4 NOT PROVEN, #5 WAITING FOR YOU (weakened check), #6 UNRESOLVED, #7 WAITING FOR YOU (no story). #8 is S2's live-run story PR (story S2, count lines), WAITING FOR YOU; merging it is optional.
- auto-job-search (private): README stub and MIT licence (a1a68d5), wiring merged by chrisz-glitch (#1, 89f51d1). Story S1, the personal-data scan (E1-S1 criteria 2 and 3, owner's decisions 2A and 3A), is PR #2 from `story/S1`: WAITING FOR YOU (NEW_CHECKS S1-C1, S1-C2, S1-C3), for the owner to approve by merging. E1-S1 criteria 1 and 4 (gate command, CI on Linux and Windows) go in their own setup PR, which changes protected files.
- Night protocol since 2026-11-11T03:21Z: keep-awake hold (session_idle) and a heartbeat every 10 minutes (cron 6278088a, session-only, expires after 7 days).

## Open pull requests and merge order

1. hevelius-ai/auto-job-search#2 (story S1): the owner's approval. Its build waits for it.
2. hevelius-ai/asbuild#4 (S4's README) and hevelius-ai/asbuild-demo#9 (the demo's README): independent; either order.
3. The demo PRs #3 to #8 stay open.

## Running jobs

- Heartbeat cron 6278088a: renews the keep-awake hold, checks jobs, continues no-decision work.

## Open decisions

- E1-S1's gate needs a coverage floor, but its constraints allow only the standard library plus ruff, mypy and pytest, and pytest has no coverage measurement without another package. Owner's call before the gate setup PR.

## QUALITY RISK

None.

## Next steps

1. S4: plan with premortem, then the README (D14 wording, receipts, "What AsBuild does not prove", the G3 wording, licence, secret scanning) and the demo's README link, on `build/S4`.
2. auto-job-search: after the owner approves story S1, its build on `build/S1` and `/asbuild:verdict`.
3. Before S4's done check (D27): re-load the engineering skills from the synced folder; one user walkthrough on the release build; then the owner's own try.
