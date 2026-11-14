---
name: asbuild-project
description: "Facts for the AsBuild Core build: repositories, accounts, paths, budget, status block, the owner's machine and time zone. Load with engineering-playbook and engineering-build-loop before any AsBuild plan, story, review or gate. Created by Hevelius AI Group LLC"
---

# AsBuild: project facts

The general rules are in `engineering-playbook` and `engineering-build-loop`. This file holds only this project's facts. The scope is in the handover (`HANDOVER.md` section 1) and the decisions in `docs/DECISIONS.md`. Created by Hevelius AI Group LLC.

## Repositories and accounts

- `hevelius-ai/asbuild`: public, the product (plugin, workflow templates, verdict scripts, receipts, marketplace file). MIT, copyright Hevelius AI Group LLC.
- `hevelius-ai/asbuild-demo`: public, the four-verdict demo.
- `hevelius-ai/auto-job-search`: private, the first real user.
- Claude Code works as `heveliusai-dev`, the only GitHub CLI login on the owner's machine. The owner approves and merges as `chrisz-glitch`, in the browser. The agent never merges, approves, tags or pushes to main.
- Commit author: in every repository it clones or creates, Claude Code sets the repository's own git identity to `heveliusai-dev` and its GitHub no-reply address, `<id>+heveliusai-dev@users.noreply.github.com` (the id comes from `gh api user --jq .id`). It never uses the laptop's global git identity, so every commit shows who built it.

## Paths (in `hevelius-ai/asbuild`)

- Control file: `docs/CONTROL.md`. Log: `docs/LOG.md`.
- Decision log: `docs/DECISIONS.md`. Parking list: `docs/PARKING.md`.
- Known issues: `docs/KNOWN-ISSUES.md`. Hours: `docs/hours.csv`.
- Acceptance tests (locked after the owner merges a story): `tests/acceptance/`, with their hashes in `locks.json`.
- Before a story's checks are locked: a check asserts what reached the person or the service (the key used, the words shown), never how a library carries it (a header name) unless the owner approved that form; and it is run once against a throwaway build that uses the dependencies the real build will use, with any decision those depend on settled first (on 11 Nov, S3-C1 asserted `x-api-key`, which Anthropic's current libraries no longer send).

## Budget

18 to 30 agent hours and 5 to 8 owner hours. Stop rules (decision D20): hard stop at 35 agent hours or 10 owner hours; each story stops at the top of its estimate for the owner's choice; S1's kill gate at 20 agent hours; 15 working days (a day counts only if the agent did AsBuild work, not only waited for the owner); outer limit 6 calendar weeks from the first build commit. Report at 28 agent hours, 8 owner hours, working day 12, and at the end of each story.

## Gates

- CI decides (playbook 2.4). `hevelius-ai/asbuild` gets its own CI in S1's first pull request: one workflow running pytest with coverage, lint and types, on every pull request.
- Local early warnings: pytest on the tests touching the changed modules, plus the lint and type tools chosen in story S1 and recorded here when chosen.
- History check (before each commit and push): every new commit's author email is the heveliusai-dev no-reply address; `git log --format=%ae origin/main..HEAD` prints only that address. Nothing more in Core.
- Every workflow file is parsed by the tests (`tests/unit/test_yaml_files.py`): GitHub rejects a file whose plain YAML value holds ": " without running any job.
- Python and pytest only.

## Reviews (decision D21)

- Reviewer: a fresh headless session, `claude -p --model claude-fable-5-2 --effort high --permission-mode plan --tools Read,Grep,Glob --output-format json`, never the `fable` alias. Triage: the same command with `--model claude-sonnet-5-5`.
- Each review record names the model from the JSON result's `modelUsage` → `canonicalModel`. The CLI's `unrecognized_model` warning for the Fable ID is expected; the record is what counts.
- An empty call costs about $0.87, because the session loads the full plugin and tool set.

## Walkthroughs (decisions D31, D42)

- Walker: a fresh headless run on `claude-sonnet-5-5`, high effort, in a new folder outside the repositories, with deny rules on reading the repositories and the installed plugin.
- After every walker run, before reporting it: check the test repository's default branch and settings (`gh api repos/<owner>/<repository>`) and the AsBuild version installed on this computer (`claude plugin list`). Any change beyond the brief and the README's install steps is a QUALITY RISK item.

## Progress board (decision D23)

- https://claude.ai/artifact/2iCLD7UuDC4pVZuvPZ6Vhi. Page: the Hevelius board page since 14 Nov 2026 (the owner's word); source `board/asbuild-board-hevelius.html` in the kit folder (not committed), the earlier page `board/asbuild-board.html`.
- Data: collection `cards` (title, milestone M0/S1/S2/S3/S4/DONE, column todo/doing/waiting/done, order, owner, note, verdict, updated in UTC, and for the Hevelius board page `hours`, the estimate as a number, and `ref`, the short id on the card such as "S7") and the document `meta/status` (story, next, agentHours, ownerHours, workingDay, week, updated; for the Hevelius page also `project`, `planHours` (the total estimate when the plan was agreed, changed only when the owner re-agrees it), `workingDays` 15, `agentBudget` 30, `agentStop` 35, `ownerBudget` 8 and `ownerStop` 10, this project's budget). With every update the keeper also writes `snapshots/day-NN` (NN the working day, two digits; day 0 never stored; the day's last update wins): `day`, `hoursLeft` (the sum of `hours` on every card not in `done` after the batch, computed by a one-line script over the cards as read back), `waiting` (true when a card is in `waiting`) and `updated`. All new fields are optional; old data still loads.
- The board only mirrors the build. The build session is its source of truth and makes every decision; the board keeper never decides anything.
- How it is fed: one-way push (decision D43, the owner's F1, 13 Nov 2026). The keeper is a separate Haiku session, "AsBuild board keeper 2 (Haiku)" since 14 Nov 2026 (the first one is archived), at top level: the owner starts it, or the build session detaches it once right after starting it, because a keeper linked to the builder wakes the builder for a whole turn every time it finishes. Every time something is done, a stage changes or a 🔴 block goes out, the build session sends it the changed fields in one message and carries on: it does not wait, does not read the board back and does not run `date -u` for the board; its reports say "board update sent". The keeper takes `updated` from its own clock (`date -u` in the step just before the write), applies one batch with the day's snapshot, reads back every document the batch touched, compares each field with the message and retries a mismatch once. It messages the build session only when a field still differs after the retry or a value cannot be placed (a column other than todo, doing, waiting or done; an unknown card id), never with "done" or a summary. A script that writes a time to a record still takes it from the clock as it runs (`datetime.now(timezone.utc)`), never from a string in the script.

## The owner

- Time zone: America/New_York; times shown as "3:04 PM".
- Machine: Windows; shell Windows PowerShell 5.1 (no `&&`, no `<` redirection, `'""'` for an empty argument), Git Bash available.
- Away protocol, machine specifics: start the keep-awake hold (it stops only idle sleep); remind the owner once not to press the power button or choose Sleep unless the button is set to do nothing when plugged in; each morning check the system log for standby and report it; re-create the heartbeat if it is missing.

## Status block (ends every report)

- Story and stage
- Verdicts on open pull requests
- Hours: agent used of 30 (stop 35), owner used of 8 (stop 10); current story's hours against its estimate
- Time: working day N of 15; calendar week W of 6
- Open decisions
- QUALITY RISK items
- Known issues: count, ids, oldest age
