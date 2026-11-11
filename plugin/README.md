# AsBuild plugin for Claude Code

AsBuild checks an AI agent's pull request against tests a person approved, and records the result in a plain receipt. This plugin is the part that runs in Claude Code. The checking itself runs in GitHub Actions, from two workflow files you add to your repository. How to install it, what each verdict means and what AsBuild does not prove: [AsBuild's README](https://github.com/hevelius-ai/asbuild#readme).

It is for Claude Code working in a GitHub repository that has Python, pytest, git and the GitHub CLI (`gh`). On claude.ai or in Cowork, with no repository to work in, it cannot do its job.

## What it contains

- **`/asbuild:story`** agrees a short checklist with you before anything is built, writes one test per line, runs AsBuild's story-time checks and opens a story pull request.
- **`/asbuild:verdict`** waits, after a push, for the AsBuild check on GitHub and tells the agent what the verdict asks.

## What it runs, writes and sends

Nothing in this plugin calls a model, reads a credential or sends data anywhere except GitHub, through your own `gh` login.

- **The story-time checks** (`scripts/asbuild_story_check.py`) run in your repository, with your project's own Python. They run `git rev-parse`, `git show` and `git worktree add`, `remove` and `prune` on your repository, and your project's `pytest` in that temporary copy of `main`. They write `locks.json` (the new tests' fingerprints).
- **They also add one line to `.claude/settings.json`**, a Claude Code deny rule such as `Edit(/tests/acceptance/S1/**)`. From the next session on, Claude Code's file tools cannot change that story's approved tests. It only adds a rule; it never removes or loosens one. The story pull request shows the line, and you can delete it before you merge.
- **The skill** tells Claude Code to run `git fetch`, `git switch`, `git commit` and `git push` on a `story/S<n>` branch, and `gh pr create` to open the story pull request.
- **The wait script** (`scripts/asbuild_wait.py`) runs `gh repo view`, `git rev-parse HEAD`, and `gh api repos/<owner>/<repo>/commits/<commit>/check-runs` about every 20 seconds, for up to 20 minutes. It only reads.

## Licence

MIT licence. Copyright (c) 2026 Hevelius AI Group LLC.
