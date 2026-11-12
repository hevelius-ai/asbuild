# AsBuild plugin for Claude Code

AsBuild checks an AI agent's pull request against tests a person approved, and records the result in a plain receipt. This plugin is the part that runs in Claude Code. The checking itself runs in GitHub Actions, from two workflow files you add to your repository. How to install it, what each verdict means and what AsBuild does not prove: [AsBuild's README](https://github.com/hevelius-ai/asbuild#readme).

It is for Claude Code working in a GitHub repository that has Python, pytest, git and the GitHub CLI (`gh`). On claude.ai or in Cowork, with no repository to work in, it cannot do its job.

## What it contains

- **`/asbuild:setup`** wires a GitHub repository to AsBuild: it checks Git, the GitHub sign-in and the repository, puts AsBuild's two workflow files on a branch and opens GitHub's page for the pull request, which you create and merge.
- **`/asbuild:story`** agrees a short checklist with you before anything is built, writes one test per line, runs AsBuild's story-time checks and opens a story pull request.
- **`/asbuild:verdict`** waits, after a push, for the AsBuild check on GitHub and tells the agent what the verdict asks.

## What it runs, writes and sends

Nothing in this plugin calls a model or reads a credential. It sends data only to GitHub, through your own `git` and `gh` logins.

- **The setup skill** (`/asbuild:setup`) tells Claude Code to run the setup script and pass on its message, never to enter a password, key or token, and, after you say the pull request is merged, to run `git fetch`, then `git switch main` and `git pull` when your folder has no unsaved work.
- **The setup script** (`scripts/asbuild_setup.py`) runs `git rev-parse`, `git config`, `git ls-remote`, `git fetch`, `git cat-file` and `gh auth status`. It makes its commits with Git's own plumbing (`hash-object`, `read-tree`, `update-index`, `write-tree`, `commit-tree`) on a temporary index in your system's temporary folder, so your files, your current branch and any unsaved work are left as they are. It uploads with `git push --no-follow-tags` only the branch `asbuild-setup` (the two workflow files from this plugin's own `workflows/` folder, and `requirements.txt` with pytest added when it lacks it), replacing an older `asbuild-setup` branch with `--force-with-lease` when one is there. On an empty repository whose folder has no commits either, it first uploads `main`, holding only `requirements.txt`: your folder's own file as it is on disk, saved or not, with pytest added, or a new one that lists pytest. Then it opens GitHub's pull request page in your browser.
- **The story skill** (`/asbuild:story`) tells Claude Code to run `git fetch` and `git switch` to start a `story/S<n>` branch, to write the story file `dev-docs/stories/S<n>/story.md` (your request, word for word, and the agreed checklist) and one test file in `tests/acceptance/S<n>/`, then `git commit`, `git push` and `gh pr create` to open the story pull request on GitHub.
- **The story-time checks** (`scripts/asbuild_story_check.py`) run with your project's own Python. They run `git rev-parse` and `git show` in your repository, and `git worktree add` to make a temporary copy of `origin/main` in your system's temporary folder, outside the repository. They copy the story's tests into it, run your project's `pytest` there, then delete the copy (`git worktree remove` and `prune`). Only when every check passes do they write anything in your repository's files: `locks.json` (the new tests' fingerprints) and the line below. (Git keeps its own record of the temporary copy under `.git/worktrees/` while it exists.)
- **When every check passes, the checks also add one line to `.claude/settings.json`**, a Claude Code deny rule such as `Edit(/tests/acceptance/S1/**)`. From the next session on, Claude Code's file tools cannot change that story's approved tests. The script only ever adds that rule; it never removes or loosens one. If you ask for a check to change before you merge the story pull request, the story skill tells Claude Code to delete that one line first, and the next time the checks pass they add it back. Until then the line stays deleted in your copy of the repository. The story pull request shows the line, and you can delete it before you merge.
- **The verdict skill** (`/asbuild:verdict`) tells Claude Code to run the wait script after each push. After NOT PROVEN it tells Claude Code to fix the code, push to the build branch and wait again, and to stop and tell you after three NOT PROVEN results in a row for the same check; never to change the agreed tests, `locks.json` or the story. If GitHub can't be reached it tells Claude Code to run `gh auth status`.
- **The wait script** (`scripts/asbuild_wait.py`) runs `gh repo view` and `git rev-parse HEAD` once, then `gh api repos/<owner>/<repo>/commits/<commit>/check-runs` about every 20 seconds, for up to 20 minutes. It only reads.

## Licence

MIT licence. Copyright (c) 2026 Hevelius AI Group LLC.
