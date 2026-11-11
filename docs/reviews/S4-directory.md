# S4 directory step: review record

The plugin folder's README for Anthropic's directory (D17), hevelius-ai/asbuild#5 from `build/S4-directory`. Reviews follow D21: a fresh read-only session on `claude-fable-5-2` at high effort; triage on `claude-sonnet-5-5`.

## Evidence before review

- Anthropic's pre-submission checklist (claude.com/docs/plugins/pre-submission-checklist, read 11 Nov 2026): a plugin folder without a README of at least 40 words outside code blocks is blocked; the security scan looks for behaviour a plugin does not disclose, such as changing Claude's permission settings. The rest of the checklist holds for `plugin/`: name, licence, small text files only, no hooks, MCP servers, launchers or `bin/`, valid skill front matter.
- `claude plugin validate ./plugin --strict` passes.
- `tests/unit/test_plugin_readme.py` seen failing without the README.

## Round 1: claude-fable-5-2

REQUEST CHANGES: 1 HIGH, 4 MEDIUM, 2 LOW, 2 PARKED. Cost $1.20. Triage on `claude-sonnet-5-5` ($0.28): 5 CONFIRMED.

| # | Grade | Finding | Fix |
| --- | --- | --- | --- |
| 1 | HIGH | "It never removes or loosens one" was untrue of the plugin: the story skill tells Claude Code to delete the deny line when a check changes before the merge | The script only adds the rule; the README now discloses that the story skill deletes that one line first and the next run adds it back |
| 2 | MEDIUM | "The skill" named neither skill and left out what the verdict skill tells Claude Code to do | Both skills named, with their instructions |
| 3 | MEDIUM | "through your own `gh` login" was untrue for `git fetch` and `git push` | "through your own `git` and `gh` logins" |
| 4 | MEDIUM | The story file and the temporary copy outside the repository were not disclosed | Both named |
| 5 | MEDIUM | The link promised the verdicts and limits, which the main README gets only in hevelius-ai/asbuild#4 | Merge order: #4 first, then this PR |

The new assertions on the deny line, the story file, the temporary folder and the logins were seen failing on the round 1 README; the loop over the skill names was not (both names were already there), which round 2 found. LOW, both taken: the README now introduces the temporary copy before naming it, and says only the `gh api` call repeats. PARKED: the story skill says 2 to 5 lines where the script accepts 1 to 5; the script's `--keep` option, which the skill never uses.

## Round 2: claude-fable-5-2, the round 1 fixes (616e25e)

REQUEST CHANGES: all five round 1 findings closed (finding 5 by merge order: #4 first); 2 new MEDIUM, 1 LOW, 3 PARKED. Cost $1.18. Triage on `claude-sonnet-5-5` ($0.23): 2 CONFIRMED.

| # | Grade | Finding | Fix |
| --- | --- | --- | --- |
| 1 | MEDIUM | "the next run of the checks adds it back" was untrue when that run fails: the script writes `locks.json` and the deny line only when every check passes. The story skill said the same | The README and the story skill say both are written only on a pass; the README adds that the line stays deleted until then |
| 2 | MEDIUM | The skill-name loop could not fail: both names were already in the README | The test now pins the verdict skill's bullet ("push to the build branch", already in the README at 616e25e) and the pass-only wording (those two assertions seen failing before the fix) |

LOW taken (the record's wording). PARKED: `git worktree prune` clears every missing worktree's record, not only AsBuild's (S2's code); `protect()` rewrites the whole settings file with two-space indents (S3's code); round 1's two parked items.

## Round 3: claude-fable-5-2, the round 2 fixes (b0e11e9); approval on the whole branch

APPROVE: both round 2 findings closed; no new HIGH or MEDIUM. 3 LOW, all taken (the README mentions git's own record of the temporary copy; two record sentences made exact). Cost $1.23. CI green at b0e11e9.

Cost for this step's reviews: $3.61 for the three rounds ($1.20, $1.18, $1.23) and $0.51 for triage ($0.28, $0.23), $4.12 in all.
