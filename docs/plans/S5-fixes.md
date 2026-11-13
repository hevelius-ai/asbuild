# S5 fixes: the owner's try findings T1 to T3 (release `v0.3.1`)

Decision S5-1A (D40). The owner's try of `v0.3.0` (`hevelius-ai/asbuild-owner-try2`, 13 Nov) reached PROVEN in 23 minutes, with three stuck points. Estimate about 2.5 agent hours with review; D38's report line is 24 agent hours (18.3 used before this).

## The findings, their causes and the changes

| ID | What happened | Root cause | Change |
| --- | --- | --- | --- |
| T1 | The owner chose the new GitHub repository in the desktop app's Code tab. That starts a cloud session, which has no AsBuild, so `/asbuild:setup` could not run. | `## Install` step 2 says "Open your project's folder", but a new repository has no folder on the computer, and nothing says how to get one or that a cloud session lacks the plugin. Walker run 3 made its folder with `git init` and did not flag it. | Step 2 says the folder must be on the computer, gives the `git clone` line for a new repository, and says to choose that folder, not the GitHub repository. The opening list's step 2 says it too. |
| T2 | Setup stopped on a missing Git name and email; the owner ran its two commands as shown, so the computer's global identity became "Your Name" and `you@example.com`, and setup then accepted it. | The message shows runnable commands holding placeholders; the skill passes it on as it is; setup checks only that a name and email exist. | The message says to put in your own name and email and that Claude can set them; setup treats the example values as not set and says so; the skill asks the person for their name and email and, with their answer, runs the two commands itself, never with the example values. |
| T3 | The opening list's step 1 says only "Add the plugin to Claude."; the how is further down. | The three-step list was written as a summary, with the steps below it. | Step 1 in the list carries the desktop app's path in one sentence and points to the terminal commands below. |

The locked S5 checks stay unchanged: C2 still finds the two commands with the example values in the message; C12 still finds the three step lines, which only gain words after them.

## Tests first, seen failing

Seen failing on 13 Nov, before the fix, each by its assertion: T1 `'folder on your computer' in "2. In your project, type ..."`; T2 `assert 0 == 1` (setup accepted "Your Name" and pushed); the skill test `'ask the person for the name and email to use' in '---...'`; T3 `'Settings' in '1. Add the plugin to Claude.'`. The round 1 test for the repository's own settings failed on the first fix (no "It is set in this repository's own settings"), and the version test failed with one workflow file set back to `v0.3.0`.

`tests/acceptance/S5/test_S5_fixes.py`, new:

- `test_S5_T1_install_says_the_folder_is_on_your_computer`: the opening list's step 2 and section 2 name a folder on your computer, `git clone https://github.com/`, and that a cloud session does not have the plugin.
- `test_S5_T2_example_identity_counts_as_not_set`: with "Your Name" and `you@example.com` in the global settings (T2 as it happened), setup exits 1 with the example-values message and the `--global` commands, pushes nothing and changes nothing; after each named fix it carries on.
- `test_S5_T2_missing_identity_says_claude_can_set_it`: the missing-identity message says to use your own name and email and that Claude can set them.
- `test_S5_T2_skill_asks_for_the_name_and_email`: the setup skill tells Claude to ask for the name and email, to run the two commands with the person's answer, and never to use the example values.
- `test_S5_T3_step_one_says_how`: the opening list's step 1 names Settings, Customize, Plugins, Add marketplace and `hevelius-ai/asbuild`, then Discover.

- `test_S5_T2_example_identity_in_the_repository_names_the_local_fix` (review round 1, M1): the example in the repository's own settings gets the commands without `--global`, and that fix works.

Version `0.3.1` (D32): `plugin.json` and the four `--branch` lines, held on one number by `tests/unit/test_workflows.py::test_plugin_and_every_workflow_clone_one_version` (review round 1, M2; before it, nothing tested it).

## Premortem: how it could fail

1. The new README words break a locked S3, S4 or S5 string. Test: the full suite runs the locked checks.
2. The example-value check stops a real person whose name is literally "Your Name" (the name alone stops setup, whatever the email). Stated limit: it is the README's example; such a person sets their name in another form, for example with an initial.
3. Claude runs `git config` with a name it guessed. Test: the skill line says to ask and to use the person's answer; the only values it names are the examples, as values never to use.
4. The cloud-session line goes stale if the desktop app later carries local plugins into cloud sessions. Stated limit: the line says what happens today.
5. The examples sit in the repository's own settings (the README allows leaving out `--global`), so a `--global` fix would change nothing (review round 1, M1). Test: setup names the commands without `--global` when the repository's own settings hold an example, and each named fix lets setup carry on, for both places.

## Release after the merge

The owner merges and publishes `v0.3.1`. Setup's own "older workflow files" run updates asbuild-demo and auto-job-search (WAITING FOR YOU, expected; the owner merges).
