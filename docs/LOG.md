# Log: AsBuild Core

Append-only. UTC.

- 2026-11-10T15:59Z M0: owner steps 1 to 5 confirmed; D21 (reviews), D22 (first commit to main), D23 (progress board) recorded.
- 2026-11-10T17:05Z M0: `hevelius-ai/asbuild` and `hevelius-ai/asbuild-demo` created, public, MIT; first commits b5c7b26 and 92a0320 by heveliusai-dev, checked on GitHub.
- 2026-11-10T17:08Z S1: plan and premortem started on `build/S1`.
- 2026-11-10T17:19Z S1: acceptance tests written (tests/acceptance/S1/test_S1_verdicts.py, sha256 a2d49437511c480515d2f0fda9c56582eef6d310903579ce638c364b8db577c0); seen failing against interface stubs: 10 of 10 cases fail by AssertionError (empty verdict, template 0, stub workflows). Locked from here: a change needs the owner's yes in the PR.
- 2026-11-10T17:43Z S1: review round 1 (claude-fable-5-2): 2 HIGH, 16 MEDIUM; triage (claude-sonnet-5-5) confirmed all 18; fixed in a237777.
- 2026-11-10T17:54Z S1: build/S1 pushed; draft PR hevelius-ai/asbuild#1 opened.
- 2026-11-10T17:57Z S1: asbuild's own CI file did not parse (YAML ": " in the install line); root cause and prevention in docs/reviews/S1.md.
- 2026-11-10T17:59Z S1: review round 2: 15 of 18 closed, 1 HIGH and 2 MEDIUM left; triage confirmed 3; fixed in f967717. CI green at f967717.
- 2026-11-10T18:10Z S1: review round 3 (last): A, B, C closed; 1 HIGH and 1 MEDIUM in the fix commit's new rules. Build stopped for the owner's decision S1-2 (playbook 2.5).
