# AsBuild

AsBuild checks an AI agent's work on a pull request against tests a person approved, and records the result in a plain receipt.

## What AsBuild is

A maker-checker record for pull requests written by an AI agent: the agent builds, a program checks, a person approves. Each pull request ends up showing four things:

- the checks were approved before the build (the merged story pull request);
- each agreed test failed before the change and passes after it (the receipt);
- who built the change, and who merged it (both in GitHub's own history, which AsBuild does not check).

It is for people who merge an agent's work in GitHub and answer for it, not for builders who do not use pull requests.

How it works, in four steps:

1. You tell Claude Code what you want, and `/asbuild:story` agrees a short checklist with you, in plain words, with exact examples. It writes one test per line and opens a story pull request.
2. Merging that story pull request approves the checks. From then on their tests are locked.
3. The agent builds the change on a branch named `build/S<n>` and opens a pull request.
4. On every push, GitHub Actions runs the locked tests on `main` and on the pull request, and AsBuild posts one check named "AsBuild", with a verdict and a plain receipt. The agent reads it with `/asbuild:verdict`. You decide whether to merge.

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

The story pull request also adds one line to `.claude/settings.json`, Claude Code's own deny rule for that story's tests, such as `Edit(/tests/acceptance/S1/**)`. Each story adds its own line, in the form `Edit(/tests/acceptance/S<n>/**)`. From the next session on, Claude Code's file tools, and the file commands it recognises in its shell, can't change those tests. It is on by default; to turn it off for a story, delete that line from the story pull request before you merge it. What it does not cover: a script that opens a file itself is not blocked. CI is the check: whatever changes a locked test, AsBuild's verdict says so. AsBuild does not check `.claude/settings.json` itself, so a pull request could remove the line; the tests stay locked either way.

### 4. Get the verdict after each push

AsBuild posts its verdict as a check named "AsBuild", a little after the tests finish. `gh pr checks --watch` is not enough: it returns when the tests finish, before the verdict is posted. After each push to a pull request (except the one that adds the workflow files, which gets no verdict), Claude Code should run `/asbuild:verdict`, which waits for the AsBuild check and prints the verdict. If it doesn't, ask it to.

## The receipts

Each pull request gets one of four verdicts, with a receipt in plain words on top and the technical report underneath. A program writes both from fixed templates; no model is called. The checklist lines and the story's title are quoted from the story. Each verdict below links to a real pull request in [the demo](https://github.com/hevelius-ai/asbuild-demo).

- **PROVEN**: every check you approved failed before the change and passes after it, none was changed, and nothing that worked before broke. Read it, and merge it if you want it. Example: [demo #3](https://github.com/hevelius-ai/asbuild-demo/pull/3).
- **NOT PROVEN**: a check still fails, or something that worked before broke. The receipt marks the line that fails, or says how many things broke; the technical report gives the failing check's ID, or names the tests that broke. Don't merge it yet; the agent fixes the code and pushes again. Example: [demo #4](https://github.com/hevelius-ai/asbuild-demo/pull/4).
- **WAITING FOR YOU**: the decision is yours. There are new checks to approve, or a locked check or protected file was changed, or a check is missing, skipped or already passed before the change, or it failed before only because a part of the app did not exist yet, or the branch is behind a check that was added or changed on `main`, or no story covers the change. The receipt says which. Example, a weakened check: [demo #5](https://github.com/hevelius-ai/asbuild-demo/pull/5).
- **UNRESOLVED**: AsBuild could not read the test results or compute a verdict, so nothing is claimed. Don't merge it yet; the receipt says what failed. If the cause is your test setup or `requirements.txt`, fix it in its own pull request, because AsBuild protects those files. Example: [demo #6](https://github.com/hevelius-ai/asbuild-demo/pull/6).

A story pull request always gets WAITING FOR YOU: its receipt lists the new checks for you to approve by merging.

## What AsBuild does not prove

1. PROVEN means every test you approved failed before the change, passes after it and was not changed, and nothing that worked before broke. It does not mean the request is fully met; the agent wrote the tests and you approved them.
2. AsBuild blocks nothing: any pull request can still be merged.
3. The test results come from a job that runs the pull request's own code, so AsBuild catches tests that were changed, skipped, weakened or never failed, not a deliberate forgery of results.
4. AsBuild does not check who built a change and who merged it; GitHub's history shows that.

## The pressure test

This test ran on an earlier in-session version with a guard that AsBuild Core does not include. In a six-run pressure test (Claude Sonnet 5.5 and Opus 5.5, one small repository), no agent faked done or changed an agreed test, and a hash check found every protected file unchanged. The test did not show that the gate can stop an agent that tries: the guard denied nothing and there was no false 'done' to block.

## Security

AsBuild uses no repository secrets: its two workflows use only the token GitHub gives each run. The job that runs the pull request's code has read-only rights; the job that posts the verdict runs from `main` and never runs pull-request code. A login that can push to your repository can usually also create or delete its secrets, and AsBuild does not watch them. AsBuild does not look for keys or passwords in your code either: for that, turn on GitHub's own secret scanning and push protection (https://docs.github.com/en/code-security/secret-scanning).

## Licence

MIT licence. Copyright (c) 2026 Hevelius AI Group LLC.
