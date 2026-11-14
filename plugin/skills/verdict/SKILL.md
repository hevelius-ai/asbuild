---
name: verdict
description: "Wait for AsBuild's verdict on the pull request you just pushed, show it, and do what it asks. Use after every git push to a pull request in a repository wired to AsBuild (its .github/workflows/ holds asbuild-test.yml), or when someone runs /asbuild:verdict. Needs Python, git and the gh command, logged in."
---

# AsBuild: get the verdict after a push

AsBuild checks each pull request in GitHub and posts one check named "AsBuild" with a verdict and a receipt. `gh pr checks --watch` is not enough: it returns when the test workflow ends, a few seconds before the verdict is posted. Use the wait script instead.

## 1. Wait for the verdict

After `git push`, from the repository root, on the commit you pushed, run:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/asbuild_wait.py"`

It can wait up to 20 minutes, so run it in the background and read its output when it ends. It prints the verdict and the check's summary.

The pull request that adds AsBuild's two workflow files gets no verdict, because the workflows are not on `main` yet: don't wait for it.

## 2. Do what the exit code says

- **0 PROVEN:** every agreed check failed before the change and passes now, and no other test that ran failed, apart from the checks of stories not built yet. Tell the person it is ready for them to read and merge, with the pull request's link. Never merge it yourself.
- **1 NOT PROVEN:** a check still fails, or another test failed. Read the summary, fix the code, push, and run this again. If the tests that fail are ones your change did not touch, never delete, skip or weaken them: run them on `main`, and if they fail on `main` too, stop and tell the person which tests fail. Never change `tests/acceptance/`, `locks.json` or the story to get past it. After three NOT PROVEN results in a row for the same check, stop and tell the person what fails.
- **3 UNRESOLVED:** AsBuild could not run the tests or compute a verdict, so nothing was checked. Read the summary and tell the person what it says. If the cause is `requirements.txt` (for example it does not list pytest) or the workflow files, don't change them in this pull request: AsBuild protects those files, so the verdict would only wait for the person. Say what to fix; it belongs in its own pull request, which the person merges.
- **4 WAITING FOR YOU:** the decision is the person's. Stop and tell them, in plain words, what the summary asks: new checks to approve (a story pull request), a changed check or protected file, a missing or already passing check, or a change no story covers.
- **5 could not ask GitHub:** `gh` or `git` failed. Check `gh auth status` and the network, then run it again.
- **7 no verdict yet:** run it again once. If there is still none, tell the person to look at the pull request's Checks tab.

Report each verdict in one plain sentence, then the next step.
