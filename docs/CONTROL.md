# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S1 (CI check, verdict and receipts), stage: review approved (after S1-3 = 3A, D25); PR ready, waiting for owner merge 1.
- Branch: `build/S1` in `hevelius-ai/asbuild`, pushed; draft PR hevelius-ai/asbuild#1, CI green at f967717.
- Demo: branch `wiring` in `hevelius-ai/asbuild-demo` committed locally (d79cef4), not pushed; demo story S1 drafted (not in a repository yet).

## Open pull requests and merge order

1. hevelius-ai/asbuild#1 (draft; S1). Merges first: the demo's workflows fetch the engine from its main.
2. Then the demo setup PR (not opened yet).

## Running jobs

None.

## Open decisions

None.

## QUALITY RISK

None.

## Next steps

1. Owner merge 1: hevelius-ai/asbuild#1.
3. Demo setup PR (owner merge 2), then the demo story PR (owner merge 3), then the demo build PRs.
