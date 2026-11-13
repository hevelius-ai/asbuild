---
name: setup
description: "Wire a GitHub repository to AsBuild with one command: check Git, the GitHub sign-in and the repository, put AsBuild's two workflow files on a branch and open GitHub's pull request page for the person to create and merge. Use when someone runs /asbuild:setup, asks to set up or install AsBuild in a repository, or asks for a story or a verdict where `.github/workflows/asbuild-test.yml` is not on `origin/main` yet. Needs Python, git and the gh command."
---

# AsBuild: set up a repository

AsBuild's checks run in GitHub Actions, from two workflow files in the person's repository. This skill puts them there with one script. The person approves them by merging the pull request it prepares; nothing reaches `main` without that merge.

## 1. Run the script

From the project's folder, run:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/asbuild_setup.py"`

If `python` is not found, try `py` (Windows) or `python3` once. If none runs, tell the person to install Python 3.12 from https://www.python.org (on Windows: `winget install --id Python.Python.3.12`), close and reopen Claude so that it finds it, then run `/asbuild:setup` again.

The script changes nothing in the person's folder: no branch is switched and unsaved work stays as it is. It uploads only the branch `asbuild-setup` (and, on an empty repository, its first commit as `main`).

## 2. Do what the exit code says

- **0:** pass on the script's message as it is, with the link. On GitHub's pull request page (open in the browser when the message says so, else from the link) the person clicks **Create pull request**, then **Merge pull request**. If the message says AsBuild is already set up, offer `/asbuild:story`.
- **1:** the person must do one thing first, and the message names it. Pass it on as it is. Never enter a password, key or token, and never run a sign-in for them: `gh auth login` and `gh auth refresh` are the person's to run, in their own terminal. When they say it is done, run the script again.
- **1, about Git's name and email:** ask the person for the name and email to use for their commits, then run the two `git config --global` commands with their answer, never with the examples "Your Name" or `you@example.com`, and run the script again.
- **2:** setup could not run. Tell the person what the message says.

Never write the workflow files by hand or change them, and never merge the pull request: the merge is the person's approval.

## 3. After the merge

When the person says the pull request is merged, run `git fetch origin`. If the folder has no unsaved work, run `git switch main` and `git pull`; otherwise tell the person their work is untouched and `main` is ready when they want it. If Git refuses because untracked files, such as `requirements.txt`, would be overwritten (an empty repository's first commit was made from them), tell the person that GitHub's `main` now holds its own copy, and ask before moving their copy aside (for example to `requirements.txt.local`); never delete it. Then offer `/asbuild:story`: "Say what you want the app to do, and I'll agree a short checklist with you first."
