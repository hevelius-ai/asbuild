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

The new test assertions were seen failing on the round 1 README. LOW, both taken: the temporary copy is introduced before it is named, and only the `gh api` call repeats. PARKED: the story skill says 2 to 5 lines where the script accepts 1 to 5; the script's `--keep` option, which the skill never uses.
