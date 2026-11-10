# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S1 (CI check, verdict and receipts), stage: stopped after review round 3 of 3 (1 HIGH, 1 MEDIUM left); waiting for the owner's decision S1-2.
- Branch: `build/S1` in `hevelius-ai/asbuild`, pushed; draft PR hevelius-ai/asbuild#1, CI green at f967717.
- Demo: branch `wiring` in `hevelius-ai/asbuild-demo` committed locally (d79cef4), not pushed; demo story S1 drafted (not in a repository yet).

## Open pull requests and merge order

1. hevelius-ai/asbuild#1 (draft; S1). Merges first: the demo's workflows fetch the engine from its main.
2. Then the demo setup PR (not opened yet).

## Running jobs

None.

## Open decisions

- S1-2: S1 review round 3 still blocks (1 HIGH, 1 MEDIUM). Fix both with a confirm-only re-check, or other (see the report of 2026-11-10T18:10Z).

## QUALITY RISK

None.

## Next steps

1. Owner decision S1-2.
2. Mark hevelius-ai/asbuild#1 ready; owner merge 1.
3. Demo setup PR (owner merge 2), then the demo story PR (owner merge 3), then the demo build PRs.
