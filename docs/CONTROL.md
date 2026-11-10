# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S1 (CI check, verdict and receipts), stage: engine merged (hevelius-ai/asbuild#1, merge 561817d by chrisz-glitch); live demo of the criteria next.
- Branch `build/S1` in `hevelius-ai/asbuild`: merged; deleted locally only after the owner deletes it on GitHub (the agent's delete was refused by the permission check).
- Demo: setup merged (ef2d91b). Story PR hevelius-ai/asbuild-demo#2: AsBuild: WAITING FOR YOU (S1-C7 live); waiting for owner merge 3.

## Open pull requests and merge order

1. hevelius-ai/asbuild-demo#2 (story S1; WAITING FOR YOU). Merge now: it approves the checks.
2. Then the demo build PRs (not opened yet).

## Running jobs

None.

## Open decisions

None.

## QUALITY RISK

None.

## Next steps

1. Owner merge 3: hevelius-ai/asbuild-demo#2.
2. Demo build PRs: PROVEN, NOT PROVEN, WAITING (changed check), UNRESOLVED, no story.
3. Demo setup PR (owner merge 2), then the demo story PR (owner merge 3), then the demo build PRs.
