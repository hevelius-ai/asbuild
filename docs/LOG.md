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
- 2026-11-10T18:58Z S1: owner answered S1-2 = 2A (D24); round 3's two findings fixed (fa61430); re-check confirmed both, found the symptom in another story's folder (HIGH).
- 2026-11-10T19:06Z S1: changed-check rule re-planned (73ea8aa, 16-case matrix); second re-check: still HIGH in three import-related states. Stopped for the owner's decision S1-3 (playbook 2.2).
- 2026-11-10T19:12Z S1: owner answered S1-3 = 3A (D25); applied in 4b705bf.
- 2026-11-10T19:15Z S1: confirm-only re-check (claude-fable-5-2): APPROVE. Known issues K1, K2 logged. PR hevelius-ai/asbuild#1 marked ready.
- 2026-11-10T19:21Z S1: hevelius-ai/asbuild#1 merged by chrisz-glitch (561817d). Branch delete on GitHub refused by the agent's permission check: left for the owner.
- 2026-11-10T19:22Z S1: demo setup PR hevelius-ai/asbuild-demo#1 opened.
- 2026-11-10T19:33Z S1: demo setup PR hevelius-ai/asbuild-demo#1 merged by chrisz-glitch (ef2d91b).
- 2026-11-10T19:35Z S1: demo story PR hevelius-ai/asbuild-demo#2 opened; first live verdict: AsBuild: WAITING FOR YOU (NEW_CHECKS), one check run, one receipt; wait script exit 4. S1-C7 shown live. K3 logged.
