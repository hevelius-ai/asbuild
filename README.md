# AsBuild

AsBuild checks an AI agent's work on a pull request against tests a person approved, and records the result in a plain receipt.

## What AsBuild is

A maker-checker record for pull requests written by an AI agent: the agent builds, a program checks, a person approves. Each pull request ends up showing four things:

- the checks were approved before the build (the merged story pull request);
- each agreed test failed before the change and passes after it (the receipt);
- who built the change;
- and who merged it (both in GitHub's own history, which AsBuild does not check).

It is for people who merge an agent's work in GitHub and answer for it, not for builders who do not use pull requests.

How it works, in four steps:

1. You tell Claude Code what you want, and `/asbuild:story` agrees a short checklist with you, in plain words, with exact examples. It writes one test per line and opens a story pull request.
2. Merging that story pull request approves the checks. From then on their tests are locked.
3. The agent builds the change on a branch named `build/S<n>` and opens a pull request.
4. On every push, GitHub Actions runs the locked tests on `main` and on the pull request, and AsBuild posts one check named "AsBuild", with a verdict and a plain receipt. The agent reads it with `/asbuild:verdict`. You decide whether to merge.

## Install

Three steps, once Git, the GitHub CLI and Python are on your computer.

1. Add the plugin to Claude. In the desktop app: Settings, Customize, Plugins, **Add**, **Add marketplace**, **Add from a repository**, enter `hevelius-ai/asbuild`; then **Discover**, AsBuild, **Add**. In a terminal, use the two commands under "1. Add the plugin" below.
2. In your project, type `/asbuild:setup`. Use your project's folder on your computer (a new repository: copy it with `git clone` first, see "2. Set it up"). Claude checks what is missing, prepares AsBuild's two check files and opens a pull request page. Create the pull request and merge it.
3. Say what you want with `/asbuild:story`.

Something missing? "Before you start" lists what to install, one line each. You can follow these steps yourself, or give them to Claude Code word for word.

### Before you start

Your computer needs three programs; setup tells you which ones are missing. On Windows, install them in PowerShell, one line each, then close and reopen Claude so that it finds them:

```powershell
winget install --id Git.Git
winget install --id GitHub.cli
winget install --id Python.Python.3.12
```

On a Mac or Linux, get them from https://git-scm.com, https://cli.github.com and https://www.python.org.

- Git, with your name and email set. Git is needed: Claude Code adds the plugin marketplace by cloning it with Git, and Git needs a name and email for its commits (on many computers, Windows ones among them, it refuses to commit without them). If it has no name or email yet, set them once with `git config`, with your own name and email in place of the examples (leave out `--global` to set them for one repository only; Claude can also set them for you):

  ```bash
  git config --global user.name "Your Name"
  git config --global user.email you@example.com
  ```

- The GitHub CLI (`gh`), signed in. Run `gh auth login` once, in a terminal, and choose GitHub.com, HTTPS, Yes to signing in Git with your GitHub credentials, and sign in with your browser. Claude never handles your password.
- Python 3.12, the version AsBuild's check uses.

Your repository needs:

- A GitHub repository with GitHub Actions switched on, with `main` as its default branch. It may be new and empty: if your folder has no commits either, setup makes the first commit, your folder's `requirements.txt` as it is on disk (saved or not) with pytest added, or a new one that lists pytest, and uploads it as `main`. If your folder already has commits, setup asks you to upload them first. If you set up a new, empty repository by hand instead, push `main` first: GitHub makes the first branch pushed the default branch. AsBuild judges pull requests into `main` from branches of the same repository, not from forks.
- Python code whose tests run with pytest on Python 3.12, and a `requirements.txt` at the repository root that lists pytest (setup adds pytest when it is missing). The check installs your project from it.
- The names AsBuild expects: stories in `dev-docs/stories/` (one folder per story, `S1`, `S2` and so on), their locked tests in `tests/acceptance/`, the tests' fingerprints in `locks.json` at the root, and each build on a branch named `build/S<n>`. The story skill creates the first three for you.

### 1. Add the plugin

In the Claude desktop app, use its menus: open Settings, then Customize, then the Plugins tab. Click **Add**, then **Add marketplace**, then **Add from a repository**, and enter `hevelius-ai/asbuild`. Then open **Discover**, select AsBuild and click **Add**. It downloads to Claude Code the next time you start a session; run `/reload-plugins` in that session, or start another, to load it ([Anthropic's plugin guide](https://claude.com/docs/plugins/overview)). To check, click **+** next to the prompt box, then **Plugins**: AsBuild should be in the list. If the app says a marketplace with the same name already exists, AsBuild's marketplace was added before, for example with the terminal commands below: open **Add**, then **Manage marketplaces**, remove `hevelius-ai`, and add it again.

In Claude Code in a terminal, type these two commands, one at a time:

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

### 2. Set it up

Your project's folder must be on your computer. A new repository has none yet: copy it first, in a terminal (if Git warns that the repository is empty, that is fine):

```bash
git clone https://github.com/<owner>/<repository>.git
```

Open that folder on your computer in Claude Code (in the desktop app: the Code tab, then your folder, not the GitHub repository: a session that runs in the cloud does not have the plugin) and type:

```
/asbuild:setup
```

Claude runs AsBuild's setup. It checks Git, your GitHub sign-in and the repository. If something is missing, it says what and the one thing to do; then run `/asbuild:setup` again. It changes nothing in your folder: your files, your current branch and any unsaved work stay as they are.

When everything is in place, it uploads AsBuild's two workflow files, `.github/workflows/asbuild-test.yml` and `.github/workflows/asbuild-verdict.yml`, on a branch named `asbuild-setup`, and opens GitHub's pull request page in your browser. Click **Create pull request**, then **Merge pull request**, and tell Claude it is merged.

- A first setup's pull request gets no verdict, because the workflows are not on `main` yet: AsBuild judges the pull requests that come after it.
- On a repository that already uses AsBuild, setup brings the two files up to this version. That pull request changes files AsBuild protects, so its verdict is WAITING FOR YOU. That is expected: read it, and merge it.
- If setup says AsBuild is already set up here, there is nothing to merge.

Uploading workflow files needs a GitHub login with the `workflow` scope. If GitHub refuses for that reason, setup gives you the one command to run: `gh auth refresh -h github.com -s workflow`. If an earlier `asbuild-setup` branch is still on GitHub, setup replaces it with one made from today's `main`, but only when every commit on it that `main` lacks is one setup made; otherwise it leaves the branch alone and tells you.

### 3. Agree your first story

In Claude Code, run `/asbuild:story` and say what you want, in your own words. It agrees a short checklist with you, writes one test per line, and opens a story pull request. AsBuild's verdict on a story pull request is always WAITING FOR YOU: merging it approves the checks, and from then on they are locked.

The story pull request also adds one line to `.claude/settings.json`, Claude Code's own deny rule for that story's tests, such as `Edit(/tests/acceptance/S1/**)`. Each story adds its own line, in the form `Edit(/tests/acceptance/S<n>/**)`. From the next session on, Claude Code's file tools, and the file commands it recognises in its shell, can't change those tests. It is on by default; to turn it off for a story, delete that line from the story pull request before you merge it. What it does not cover: a script that opens a file itself is not blocked. CI is the check: whatever changes a locked test, AsBuild's verdict says so. AsBuild does not check `.claude/settings.json` itself, so a pull request could remove the line; the tests stay locked either way.

### 4. Get the verdict after each push

AsBuild posts its verdict as a check named "AsBuild", a little after the tests finish. `gh pr checks --watch` is not enough: it returns when the tests finish, before the verdict is posted. After each push to a pull request (except the one that adds the workflow files, which gets no verdict), Claude Code should run `/asbuild:verdict`, which waits for the AsBuild check and prints the verdict. If it doesn't, ask it to.

### By hand

Setup does the following for you. To do it yourself instead, from your repository's root, in a Bash shell (on Windows, Git Bash, which comes with Git; in Windows PowerShell, type `curl.exe` instead of `curl`, because there `curl` is a different command):

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

Merge this pull request yourself. Like setup's, it gets no verdict on a first setup.

### If something goes wrong

Each of setup's messages names its own fix. The most common ones:

| Setup says | What to do |
| --- | --- |
| This folder is not a Git repository | Open your project's own folder, the one linked to GitHub |
| Git has no name or email for its commits yet | Run the two `git config` commands it shows, with your own name and email |
| The GitHub CLI (gh) is not installed | Install it: `winget install --id GitHub.cli` on Windows, or from https://cli.github.com |
| You are not signed in to GitHub | Run `gh auth login` in a terminal and sign in with your browser |
| Git could not reach the repository on GitHub | Check that you are online; if `gh` is signed in, run `gh auth setup-git` so that Git uses the same sign-in |
| The repository on GitHub is empty, but this folder already has commits | Run `git push -u origin HEAD:main` |
| GitHub's default branch for this repository is … | On GitHub: Settings, then General, set Default branch to `main`, or rename the default branch to `main` when there is none |
| The branch asbuild-setup on GitHub holds commits that setup did not make | On GitHub, merge or close its pull request and delete the branch |
| GitHub refused the two workflow files | Run `gh auth refresh -h github.com -s workflow`; if it still refuses, `gh auth setup-git` as well |
| Git is not installed, or the GitHub CLI is not installed | Install it, then close and reopen Claude |

Then run `/asbuild:setup` again. It is safe to run any number of times.

## The receipts

Each pull request gets one of four verdicts, with a receipt in plain words on top and the technical report underneath. A program writes both from fixed templates; no model is called. The checklist lines and the story's title are quoted from the story. Each verdict below links to a real pull request in [the demo](https://github.com/hevelius-ai/asbuild-demo).

- **PROVEN**: every check you approved failed before the change and passes after it, none was changed, and nothing that worked before broke. Read it, and merge it if you want it. Example: [demo #3](https://github.com/hevelius-ai/asbuild-demo/pull/3).
- **NOT PROVEN**: a check still fails, or something that worked before broke. The receipt marks the line that fails, or says how many things broke; the technical report gives the failing check's ID, or names the tests that broke. Don't merge it yet; the agent fixes the code and pushes again. Example: [demo #4](https://github.com/hevelius-ai/asbuild-demo/pull/4).
- **WAITING FOR YOU**: the decision is yours. There are new checks to approve, or a locked check or protected file was changed, or a check is missing, skipped or already passed before the change, or it failed before only because a part of the app did not exist yet, or the branch is behind a check that was added or changed on `main`, or no story covers the change. The receipt says which. Example, a weakened check: [demo #5](https://github.com/hevelius-ai/asbuild-demo/pull/5).
- **UNRESOLVED**: AsBuild could not read the test results or compute a verdict, so nothing is claimed. This is also the verdict when `main` is not the default branch: the receipt says how to change it. Don't merge it yet; the receipt says what failed. If the cause is your test setup or `requirements.txt`, fix it in its own pull request, because AsBuild protects those files. Example: [demo #6](https://github.com/hevelius-ai/asbuild-demo/pull/6).

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
