---
name: story
description: "Agree a story with a person before an AI builds it: save their words unchanged, agree 2 to 5 plain checks with exact examples, write one test per check, run AsBuild's story-time checks and open the story pull request. Use when someone asks for a new feature or change in a repository wired to AsBuild (its .github/workflows/ holds asbuild-test.yml), or runs /asbuild:story. Needs Claude Code in a GitHub repository with Python, pytest, git and the gh command."
---

# AsBuild: agree a story before anything is built

AsBuild checks an AI's pull request against checks the person approved before the build. This skill writes those checks. The person approves them by merging the story pull request; after that the tests are locked, and only the person may change them.

## 1. Start the story and save the person's words, unchanged

1. Run `git fetch origin`, then `git switch -c story/S<n> origin/main`. `S<n>` is one above the highest story folder in `dev-docs/stories/` (S1 if there is none).
2. Create `dev-docs/stories/S<n>/story.md` at once. Put the person's request into it exactly as they wrote it: every character, line break and typo. Never correct, shorten or summarise it.

## 2. Agree the checklist with the person

- Ask only about what their words leave open: one short, plain question at a time, at most three or four, then propose the checklist. Don't ask about things they don't need to decide (colours, technology, hosting).
- Plain words only. At most one technical term per sentence, in brackets after the plain words. Never use these outside brackets: test, merge, branch, commit, deploy, API, database, field, validation, input, backend, frontend, endpoint, criterion.
- Name things by what the person sees or does, in their own words. If they don't understand, say it again with an everyday comparison, never with a new term.
- The checklist has 2 to 5 sentences. Each describes one thing the person will see the app do, with one to three exact examples: the exact words, numbers or dates they would see. If they ask for a sixth, combine it with a line it belongs to, or ask which one can wait.
- Show it like this, then wait:

```
Here is what your app will do. You'll be able to check each line yourself:

1. <plain sentence>. For example: <exact example>.

Is each of these right? You can say "yes", or tell me which number to change and how.
```

- If they change a line, show the whole checklist again. When every line is approved, say "Thank you, that's agreed." and stop asking.

## 3. Write the story file

Complete the file in this layout, keeping the request exactly as saved. Each criterion restates exactly one approved line; add nothing the person did not approve.

```markdown
# S<n>: <short title in the person's words>

## Request (the owner's words, unchanged)

<the request, exactly as written>

## Criteria

| ID | Criterion | Cites |
| --- | --- | --- |
| S<n>-C1 | <exact observable behaviour and values> | Request, sentence <k> |

## Plain checklist (approved by the owner; the receipt quotes it word for word)

| ID | plain: | Examples (approved) |
| --- | --- | --- |
| S<n>-C1 | <the approved sentence, word for word> | `<exact value>` `<exact value>` |

## Not in this story

<what the person did not decide, and the default the build will use>
```

Each example goes in backticks, exactly as the person will see it. Write `\|` for a bar inside a cell.

## 4. Write one test per check

- One file, `tests/acceptance/S<n>/test_S<n>_<short_name>.py`, with one test per check, named `test_S<n>_C<m>_<what_it_checks>`.
- Test what the person will see: run the app the way they use it, and assert each approved example as the exact literal value, such as `assert out.stdout.strip() == "words: 3"`. Don't assert it in a loop or build it from parts.
- Use only the standard library and pytest. No conftest.py (AsBuild runs these tests without it), no skips, no network.
- Build nothing: no app code in this pull request. Each test must fail now, by an assertion, because the feature isn't there yet.

## 5. Run the story-time checks

Run this from the repository root, with the Python that runs the project's tests (for example the one in its `.venv`):

`python "${CLAUDE_PLUGIN_ROOT}/scripts/asbuild_story_check.py" S<n> --lock`

- Exit 0: every check passed, and the tests' fingerprints were added to `locks.json`.
- Exit 1: each line says what is wrong. Fix the test, never the person's words or examples. If an example cannot be checked as agreed, ask the person. After three failed attempts, stop and tell the person what failed.
- Exit 2: the checks could not run. Fix what the message names (fetch `origin`, or use the Python that has the project's pytest), then run again.

## 6. Open the story pull request

1. Commit only `story.md`, the test file and `locks.json`. Push the branch.
2. Run `gh pr create --base main --title "Story S<n>: <title>"`. In the body, list the checklist and add: "Merging this pull request approves these checks. AsBuild then checks every build of this story against them."
3. Tell the person in plain words: read the list on the pull request, and merge it if it is right. Nothing is built yet. AsBuild's note on this pull request always says it is waiting for them.

The build comes later, in its own pull request from a branch named `build/S<n>`, and never changes `tests/acceptance/`.
