# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S1 (CI check, verdict and receipts), stage: stopped; S1-2 fixes done, but the changed-check rule's re-plan did not close its HIGH; waiting for the owner's decision S1-3.
- Branch: `build/S1` in `hevelius-ai/asbuild`, pushed; draft PR hevelius-ai/asbuild#1, CI green at f967717.
- Demo: branch `wiring` in `hevelius-ai/asbuild-demo` committed locally (d79cef4), not pushed; demo story S1 drafted (not in a repository yet).

## Open pull requests and merge order

1. hevelius-ai/asbuild#1 (draft; S1). Merges first: the demo's workflows fetch the engine from its main.
2. Then the demo setup PR (not opened yet).

## Running jobs

None.

## Open decisions

- S1-3: how a changed acceptance file affects the receipt's check lines (see the report of 2026-11-10T19:07Z). S1-2 was answered 2A (D24).

## QUALITY RISK

None.

## Next steps

1. Owner decision S1-2.
2. Mark hevelius-ai/asbuild#1 ready; owner merge 1.
3. Demo setup PR (owner merge 2), then the demo story PR (owner merge 3), then the demo build PRs.
