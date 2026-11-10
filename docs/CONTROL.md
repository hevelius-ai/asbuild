# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now

- Story: S1 (CI check, verdict and receipts), stage: built, green locally, in review round 1.
- Branch: `build/S1` in `hevelius-ai/asbuild`, commit e14d2a8 (local, not pushed).
- Demo: branch `wiring` in `hevelius-ai/asbuild-demo`, staged, not committed; demo story S1 drafted (not in a repository yet).

## Open pull requests and merge order

None.

## Running jobs

- Review round 1 of S1: headless `claude -p --model claude-fable-5-2`, started 2026-11-10T17:31Z; wakes the build session when it exits (background task). No log grows while it runs.

## Open decisions

None.

## QUALITY RISK

None.

## Next steps

1. Triage review round 1's blocking findings (Sonnet 5.5), fix, re-check.
2. Push `build/S1`, open the asbuild PR, watch CI; owner merge 1.
3. Demo setup PR (owner merge 2), then the demo story PR (owner merge 3), then the demo build PRs.
