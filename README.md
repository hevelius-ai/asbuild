# AsBuild

AsBuild checks an AI agent's work on a pull request against tests a person approved, and records the result in a plain receipt.

Work in progress: the install steps below work; the rest of this page comes with the demo.

## Install

You can follow these steps yourself, or give them to Claude Code word for word.

### What your repository needs

- A GitHub repository with GitHub Actions switched on. AsBuild judges pull requests into `main` from branches of the same repository, not from forks.
- Git. Git is needed: Claude Code adds the plugin marketplace by cloning it with Git.
- The GitHub CLI (`gh`), logged in.
- Python code whose tests run with pytest on Python 3.12 (the version AsBuild's check uses), and a `requirements.txt` at the repository root that lists pytest. The check installs your project from it.
- The names AsBuild expects: stories in `dev-docs/stories/` (one folder per story, `S1`, `S2` and so on), their locked tests in `tests/acceptance/`, the tests' fingerprints in `locks.json` at the root, and each build on a branch named `build/S<n>`. The story skill creates the first three for you.

### 1. Install the plugin

In Claude Code, run:

```
/plugin marketplace add hevelius-ai/asbuild
/plugin install asbuild@hevelius-ai
```

The second command opens AsBuild's page in the plugin panel: choose to install it. Then run `/reload-plugins`, or start Claude Code again.

From a script, from CI, or from Claude's own shell, add the marketplace first, then install:

```bash
claude plugin marketplace add hevelius-ai/asbuild
claude plugin install asbuild@hevelius-ai
```

### 2. Add the two workflow files in a pull request

From your repository's root, in a Bash shell (on Windows, Git Bash, which comes with Git):

```bash
git switch -c asbuild-setup
mkdir -p .github/workflows
curl -fsSL -o .github/workflows/asbuild-test.yml https://raw.githubusercontent.com/hevelius-ai/asbuild/main/workflows/asbuild-test.yml
curl -fsSL -o .github/workflows/asbuild-verdict.yml https://raw.githubusercontent.com/hevelius-ai/asbuild/main/workflows/asbuild-verdict.yml
```

Make sure `requirements.txt` lists pytest, then commit both files (and `requirements.txt` if you changed it), push, and open a pull request:

```bash
git add .github/workflows/asbuild-test.yml .github/workflows/asbuild-verdict.yml requirements.txt
git commit -m "Add AsBuild's workflow files"
git push -u origin asbuild-setup
gh pr create --base main --title "Add AsBuild" --body "Adds AsBuild's two workflow files."
```

Merge this pull request yourself. It gets no verdict, because the workflows are not on `main` yet: AsBuild judges the pull requests that come after it.

Pushing workflow files needs a GitHub login with the `workflow` scope. If the push is refused for that reason, run `gh auth refresh -h github.com -s workflow` and push again.

### 3. Agree your first story

In Claude Code, run `/asbuild:story` and say what you want, in your own words. It agrees a short checklist with you, writes one test per line, and opens a story pull request. AsBuild's verdict on a story pull request is always WAITING FOR YOU: merging it approves the checks, and from then on they are locked.

### 4. Get the verdict after each push

AsBuild posts its verdict as a check named "AsBuild", a little after the tests finish. `gh pr checks --watch` is not enough: it returns when the tests finish, before the verdict is posted. After each push to a pull request, Claude Code should run `/asbuild:verdict`, which waits for the AsBuild check and prints the verdict. If it doesn't, ask it to.

## Licence

MIT licence. Copyright (c) 2026 Hevelius AI Group LLC.
