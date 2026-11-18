# AsBuild: checks for a TypeScript or JavaScript app

Use this file in place of the story skill's section 4 when the project is a TypeScript or JavaScript app: a `package.json` at the repository's root and no Python file, `requirements.txt` or `pyproject.toml` (setup decided this already). AsBuild works with React apps built with Vite 5 to 8, and its checks run with Vitest. Everything else in the story skill stays the same.

## 1. The first JavaScript story only: the test tools

If `locks.json` on `origin/main` lists no `.test.` file yet, this is the project's first JavaScript story. Before writing its checks, run this once, from the repository's root:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/asbuild_js.py" tools`

It checks Node.js 24 or newer with npm 11.19 or newer, repairs `package-lock.json` once so it works on every kind of computer (GitHub's are Linux), and adds Vitest (the version that matches the app's Vite), jsdom and Testing Library to the app's development tools.

- Exit 0: commit `package.json` and `package-lock.json` with the story, beside the files the story skill names. The story pull request's note says the list of software changed; merging it approves that too.
- Exit 1: show the message to the person, word for word, in a text block, and stop until it is solved. Never install Node.js, npm or anything else for them, and never edit `package.json` or `package-lock.json` by hand to get past it.
- Exit 2: it could not run; fix what the message names, then run it again.

In a later story it says the tools are there already: skip this step.

## 2. One file per check

- One file per check, named after it: `tests/acceptance/S<n>/S<n>-C<m>.test.tsx` (`.test.ts` when it renders nothing).
- Each file holds exactly one test, written at the start of a line, its title in plain quotes and starting with the check's ID: `test("S<n>-C<m> <what the person sees>", () => { ... });`. Never `describe`, `it.each`, `.only`, `.skip`, `.todo`, `.fails` or a test inside another block; no `${...}` or backslash in the title.
- Start each file with these lines:

```tsx
// @vitest-environment jsdom
import { expect, test } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
```

## 3. Check what the person sees

- Render the page the person uses. A page with links goes inside a router: `render(<MemoryRouter initialEntries={["/settings"]}><Settings /></MemoryRouter>)` (from `react-router-dom`). Where `App` holds its own router, call `window.history.pushState({}, "", "/settings")`, then `render(<App />)`.
- Import only files that exist on `main` now: the check must fail on `main` because the words are not there yet, not because a file is missing. A page the story adds is reached through one that exists, such as `App` at the page's address.
- Do what the person does, and find what they press with `queryBy...`, asserting it is there first, so that a button the story adds fails on `main` by an assertion: `const save = screen.queryByRole("button", { name: "Save" }); expect(save).not.toBeNull(); fireEvent.click(save!);`. Type with `fireEvent.change`.
- Assert each approved example as the exact words, inside `expect(...)`: `expect(document.body.textContent).toContain("Saved")`. Never put an approved example in a variable, a regular expression or a `getByText(...)`: `getByText` stops the test before it asserts, and the check is refused.
- Never add a setup file, a mock of the app's own code, or a change to Vite, Vitest or `tsconfig` settings: AsBuild runs the checks with its own settings and ignores the project's. No network.

Then run the story-time checks exactly as the story skill's section 5 says. They run each check on `main` with AsBuild's settings and need each one to fail there by an assertion.
