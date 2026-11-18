// M2-C2: AsBuild's Vitest settings for the agreed checks (engine/js/vitest.acceptance.mjs; design §4.3).
// Run with Node's own runner and coverage, as AsBuild's CI does (D51, 2A):
//   node --test --experimental-test-coverage --test-coverage-include=engine/js/** --test-coverage-lines=100
//        --test-coverage-branches=100 --test-coverage-functions=100 tests/js/
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";

import settingsDefault, {
  INCLUDE,
  TOOL,
  aliases,
  pathsOf,
  readJsonc,
  settings,
  stripJsonc,
} from "../../engine/js/vitest.acceptance.mjs";

function project(files) {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "asbuild-js-")));
  for (const [name, text] of Object.entries(files)) {
    fs.mkdirSync(path.dirname(path.join(root, name)), { recursive: true });
    fs.writeFileSync(path.join(root, name), text);
  }
  return root;
}

function quiet() {
  const lines = [];
  return { log: (line) => lines.push(line), lines };
}

function found(root) {
  return aliases(root, quiet().log).map((a) => [String(a.find), path.relative(root, a.replacement)]);
}

test("M2-C2 JSONC: comments go, strings stay whole, trailing commas go", () => {
  const text = [
    "{",
    '  // a line comment with "quotes"',
    '  "a": "@/*", /* a block comment */',
    '  "b": ["src/**/*.ts", "x//y", "q\\"/*"],',
    '  "c": { "d": 1, },',
    '  "e": [1, 2, ],',
    '  "f": "a, }",',
    "}",
  ].join("\n");
  assert.deepEqual(JSON.parse(stripJsonc(text)), {
    a: "@/*",
    b: ["src/**/*.ts", "x//y", 'q"/*'],
    c: { d: 1 },
    e: [1, 2],
    f: "a, }",
  });
});

test("M2-C2 JSONC: an unclosed block comment ends the text; an unreadable file reads as nothing", () => {
  assert.equal(stripJsonc('{"a": 1} /* never closed'), '{"a": 1} ');
  const root = project({ "bad.json": "{ not json", "good.json": '{"a": 1, // note\n}' });
  assert.equal(readJsonc(path.join(root, "bad.json")), null);
  assert.equal(readJsonc(root), null); // a folder, not a file
  assert.deepEqual(readJsonc(path.join(root, "good.json")), { a: 1 });
});

test("M2-C2 paths: tsconfig.json, then tsconfig.app.json, which wins on the same name", () => {
  const root = project({
    "tsconfig.json": '{ "compilerOptions": { "paths": { "@/*": ["./src/*"], "~lib": ["./lib/index.ts"] } } }',
    "tsconfig.app.json": '{ "compilerOptions": { "baseUrl": "app", "paths": { "@/*": ["./*"] } } }',
  });
  assert.deepEqual(found(root), [
    ["/^@(?=\\/|$)/", "app"],
    ["/^~lib(?=\\/|$)/", path.join("lib", "index.ts")],
  ]);
});

test("M2-C2 paths: relative extends are followed, with or without .json, once each", () => {
  const root = project({
    "tsconfig.json": '{ "extends": "./configs/base", "compilerOptions": { "paths": { "@own/*": ["./own/*"] } } }',
    "configs/base.json": '{ "extends": "./more.json", "compilerOptions": { "paths": { "@base/*": ["../b/*"] } } }',
    "configs/more.json": '{ "extends": "../tsconfig.json", "compilerOptions": { "paths": { "@more/*": ["../m/*"] } } }',
  });
  assert.deepEqual(found(root), [
    ["/^@more(?=\\/|$)/", "m"],
    ["/^@base(?=\\/|$)/", "b"],
    ["/^@own(?=\\/|$)/", "own"],
  ]);
});

test("M2-C2 paths: an extends given as a package name or an array, or a missing file, is not followed", () => {
  const root = project({
    "tsconfig.json": '{ "extends": "@tsconfig/vite-react", "compilerOptions": { "paths": { "@a/*": ["./a/*"] } } }',
    "tsconfig.app.json": '{ "extends": ["./x.json"], "compilerOptions": { "paths": { "@b/*": [], "@c": "c" } } }',
  });
  assert.deepEqual(found(root), [["/^@a(?=\\/|$)/", "a"]]);
  assert.deepEqual(pathsOf(path.join(root, "nothing.json")), {});
  assert.deepEqual(pathsOf(undefined), {});
  const noOptions = project({ "tsconfig.json": "{}" });
  assert.deepEqual(found(noOptions), []);
  const unreadable = project({ "tsconfig.json": '{ "compilerOptions": { "paths": { "@/*": ["./src/*"] } }' });
  assert.deepEqual(found(unreadable), []);
});

test("M2-C2 aliases: never for the test tools, never outside the project, always logged", () => {
  const root = project({
    "tsconfig.json": JSON.stringify({
      compilerOptions: {
        paths: {
          vitest: ["./stub/vitest.ts"],
          "@vitest/*": ["./stub/*"],
          "vite/*": ["./stub/*"],
          "@testing-library/react": ["./stub/rtl.ts"],
          "@out/*": ["../elsewhere/*"],
          "~/*": ["./*"],
          "@/*": ["./src/*"],
        },
      },
    }),
  });
  const q = quiet();
  const kept = aliases(root, q.log);
  assert.deepEqual(
    kept.map((a) => [String(a.find), a.replacement]),
    [
      ["/^~(?=\\/|$)/", root],
      ["/^@(?=\\/|$)/", path.join(root, "src")],
    ],
  );
  assert.deepEqual(q.lines.slice(0, 5), [
    "asbuild: alias dropped: vitest",
    "asbuild: alias dropped: @vitest/*",
    "asbuild: alias dropped: vite/*",
    "asbuild: alias dropped: @testing-library/react",
    "asbuild: alias dropped: @out/*",
  ]);
  assert.equal(q.lines[5], 'asbuild: aliases kept: ["/^~(?=\\\\/|$)/","/^@(?=\\\\/|$)/"]');
  assert.ok(TOOL.test("@vitest/expect") && TOOL.test("vite") && !TOOL.test("vitest-like") && !TOOL.test("@vite"));
});

test("M2-C2 aliases: a kept alias matches its name and what is under it, nothing else", () => {
  const root = project({ "tsconfig.json": '{ "compilerOptions": { "paths": { "@/*": ["./src/*"], "a.b": ["./ab.ts"] } } }' });
  const [at, ab] = aliases(root, quiet().log);
  assert.ok(at.find.test("@/lib/utils") && at.find.test("@") && !at.find.test("@x/y"));
  assert.ok(ab.find.test("a.b") && !ab.find.test("aXb"));
});

test("M2-C2 settings: fixed values, the automatic JSX runtime for every Vite, never the project's own config", () => {
  const root = project({
    "tsconfig.json": '{ "compilerOptions": { "paths": { "@/*": ["./src/*"] } } }',
    "vite.config.ts": 'export default { resolve: { alias: { vitest: "./cheat.ts" } }, test: { setupFiles: ["./cheat.ts"] } }',
    "vitest.config.ts": 'throw new Error("never read")',
  });
  const s = settings(root, quiet().log);
  assert.deepEqual(Object.keys(s).sort(), ["esbuild", "oxc", "resolve", "test"]);
  assert.deepEqual(s.esbuild, { jsx: "automatic" }); // Vite up to 7
  assert.deepEqual(s.oxc, { jsx: { runtime: "automatic" } }); // Vite 8
  assert.deepEqual(s.test, {
    include: ["tests/acceptance/**/*.test.?(c|m)[jt]s?(x)"],
    setupFiles: [],
    globalSetup: [],
    retry: 0,
    passWithNoTests: false,
  });
  assert.equal(INCLUDE, "tests/acceptance/**/*.test.?(c|m)[jt]s?(x)");
  assert.deepEqual(s.resolve.alias.map((a) => a.replacement), [path.join(root, "src")]);
});

test("M2-C2 settings: the file's default export is the settings for the folder Vitest starts in", () => {
  assert.deepEqual(Object.keys(settingsDefault).sort(), ["esbuild", "oxc", "resolve", "test"]);
  assert.deepEqual(settingsDefault.test, settings(process.cwd(), quiet().log).test);
});

// Premortem 3 (round 1, Opus F2 and Sonnet F1): real file shapes, not only made-up strings. `lovable/` has the layout of
// the four Lovable apps' files (JS-18: `@/*` in both, comments in tsconfig.app.json); `create-vite/` is create-vite's
// own React + TypeScript pair (MIT) with the `@` alias added to tsconfig.app.json as the first story adds it.
const FIXTURES = path.join(path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/, "$1"), "fixtures");

for (const shape of ["lovable", "create-vite"]) {
  test(`M2-C2 premortem 3: the ${shape} tsconfig files give @ for src`, () => {
    const root = path.join(FIXTURES, shape);
    assert.deepEqual(found(root), [["/^@(?=\\/|$)/", "src"]]);
  });
}
