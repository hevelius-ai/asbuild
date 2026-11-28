# Control file: AsBuild Core

Current state only. Times in UTC. Read first in every session. Skills: `engineering-playbook`, `engineering-build-loop`, `.claude/skills/asbuild-project/`.

## Now
- AsBuild v0.4.2 is the final product (D60, done 2026-11-21T14:59Z): nothing more is built unless a real user asks (playbook 1.2). The parking list holds only four new ideas, not evaluated.
- D62 done: the build-or-prompt comparison. The doc (findings, which to use when, limits, the recommended model and effort, a short manual with prompt v2): https://claude.ai/artifact/13QdGB7nrnZF8yd3NZ9Nqz. Round 6 (the two checkers together, and the models on equal terms) is the doc's section "Round 6: together or apart". Fable 5.2 was not run on round 6: the owner's 3B, 2026-11-28 (it was already lowest on the blind set at almost five times Sonnet's cost). The kit folder `prompt-test` (not committed) holds the prompts, scenario designs, scripts and every run's answer.
- D61 done: the public TypeScript demo `hevelius-ai/asbuild-demo-ts`, its README listing #3 PROVEN, #4 NOT PROVEN, #5 WAITING FOR YOU and #6 UNRESOLVED. The README's receipts section links both demos. The product description PDF (two sections) is in the kit folder, outside the repository.
- v0.4.2, v0.4.1, the parked-ideas review (D59) and v0.4.0: done; the log holds their steps.
- The board: https://claude.ai/artifact/5b6CiKgT3pouct5UKN1TUu. Its Haiku keeper is archived (the owner, 2026-11-21); the board was not updated after v0.4.2.
- Branches in `hevelius-ai/asbuild`: `main` only. In `hevelius-ai/asbuild-demo` and `hevelius-ai/asbuild-demo-ts`: `main` and one branch per open demo pull request (the demo pull requests stay open on purpose). In `hevelius-ai/asbuild-proofs` (private, the v0.4.0 test lab): `main`, `proof/m2-live-bases`, `proof/m3-story` and `proof/walkthrough-app` (b5d6308, the app the walkthroughs and the TypeScript demo use). In `hevelius-ai/asbuild-stress-py` and `hevelius-ai/asbuild-stress-ts` (D62's test repositories, public while testing): `main` and one branch per scenario, each with an open pull request (71 in all, round 6 included), kept as the comparison's evidence. In `hevelius-ai/auto-job-search`: `build/S4` (the closed #14, the evidence of Core's done line 1).
- AsBuild 0.4.2 is installed on this computer.
- Plan usage: next weekly reset 2026-12-01T09:00Z.

## Open pull requests and merge order

1. `records/prompt-comparison` (this file, the log, D62, hours, round 6): records only.

## Running jobs

None.

## Open decisions

- 1A or 1B: keep AsBuild as is, or add the re-run of `main`'s copy of the other tests (a deleted, skipped or rewritten test that now fails gets WAITING FOR YOU). Round 6 adds evidence both ways: it would have caught R08, and it would have flagged the correct real build #8 for the owner's decision.

(Docker: the owner's standing yes, D52, 2026-11-18.)

## QUALITY RISK

None open.

## Next steps

1. The owner makes `hevelius-ai/asbuild-stress-py` and `hevelius-ai/asbuild-stress-ts` private again (repository settings are the owner's).
2. Nothing else is planned: building restarts only for a real user's request.
3. Known issues: none open.
4. The playbook holds 1.12's "Clean up at every close" (saved by the owner, checked 2026-11-22).
