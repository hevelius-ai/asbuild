// AsBuild's Vitest settings for the agreed checks (design §4.3; rebuilt with tests from the proven form in
// hevelius-ai/asbuild-proofs, proofs/vite8-app/asbuild-c3.mjs: JS-17, JS-18, JS-20, P-VITE8).
//
// The test job starts Vitest with this file (`--config "$ASBUILD/engine/js/vitest.acceptance.mjs" --root .`), so the
// project's own Vite and Vitest settings, setup files and plugins play no part in the agreed checks. It imports only
// Node's built-ins, so it loads from outside the project on any Vite. Aliases come from the project's tsconfig
// `paths` (tsconfig.json, then tsconfig.app.json, following relative `extends`), never from its Vite config; an alias
// for the test tools themselves, or one pointing outside the project, is dropped. Stated limit: an `extends` given
// as an array or a package name is not followed.
import fs from "node:fs";
import path from "node:path";

export const TOOL = /^(vitest|@vitest|vite|@testing-library)(\/|$)/;
export const INCLUDE = "tests/acceptance/**/*.test.?(c|m)[jt]s?(x)";

// Removes // and /* */ comments and trailing commas, never inside a string ("@/*" and "src/**/*.ts" stay whole;
// the proof's reader kept a comma followed by a comment, which a real tsconfig can hold).
export function stripJsonc(text) {
  let out = "";
  let i = 0;
  let inString = false;
  while (i < text.length) {
    const ch = text[i];
    const next = text[i + 1];
    if (inString) {
      if (ch === "\\") {
        out += text.slice(i, i + 2);
        i += 2;
        continue;
      }
      if (ch === '"') inString = false;
      out += ch;
      i += 1;
      continue;
    }
    if (ch === '"') {
      inString = true;
    } else if (ch === "/" && next === "/") {
      while (i < text.length && text[i] !== "\n") i += 1;
      continue;
    } else if (ch === "/" && next === "*") {
      const end = text.indexOf("*/", i + 2);
      i = end < 0 ? text.length : end + 2;
      continue;
    } else if (ch === "}" || ch === "]") {
      // A comma before it (comments already gone, so `1, // note\n}` too) is a trailing comma. Text kept so far
      // that ends in a comma, outside a string, cannot end inside one.
      out = out.replace(/,(\s*)$/, "$1");
    }
    out += ch;
    i += 1;
  }
  return out;
}

// The parsed file, or null when it cannot be read or is not JSON with comments.
export function readJsonc(file) {
  try {
    return JSON.parse(stripJsonc(fs.readFileSync(file, "utf8")));
  } catch {
    return null;
  }
}

// { name: absolute target } from one tsconfig file and the files it extends (theirs first, its own over them).
export function pathsOf(file, seen = new Set()) {
  if (!file || seen.has(file) || !fs.existsSync(file)) return {};
  seen.add(file);
  const cfg = readJsonc(file) || {};
  let out = {};
  if (typeof cfg.extends === "string" && cfg.extends.startsWith(".")) {
    const parent = path.resolve(path.dirname(file), cfg.extends);
    out = pathsOf(fs.existsSync(parent) ? parent : parent + ".json", seen);
  }
  const options = cfg.compilerOptions || {};
  const base = path.resolve(path.dirname(file), options.baseUrl || ".");
  for (const [name, targets] of Object.entries(options.paths || {})) {
    if (Array.isArray(targets) && targets.length) out[name] = path.resolve(base, String(targets[0]));
  }
  return out;
}

export function aliases(root, log) {
  const found = { ...pathsOf(path.join(root, "tsconfig.json")), ...pathsOf(path.join(root, "tsconfig.app.json")) };
  const kept = [];
  for (const [name, target] of Object.entries(found)) {
    const find = name.replace(/\/\*$/, "");
    const to = target.replace(/[\\/]\*$/, "");
    if (TOOL.test(find) || !(to === root || to.startsWith(root + path.sep))) {
      log("asbuild: alias dropped: " + name);
      continue;
    }
    const escaped = find.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    kept.push({ find: new RegExp("^" + escaped + "(?=/|$)"), replacement: to });
  }
  log("asbuild: aliases kept: " + JSON.stringify(kept.map((a) => String(a.find))));
  return kept;
}

export function settings(root, log = console.log) {
  return {
    resolve: { alias: aliases(root, log) },
    // JSX without the app's own plugin, the automatic runtime: Vite up to 7 reads `esbuild`, Vite 8 reads `oxc`.
    esbuild: { jsx: "automatic" },
    oxc: { jsx: { runtime: "automatic" } },
    test: { include: [INCLUDE], setupFiles: [], globalSetup: [], retry: 0, passWithNoTests: false },
  };
}

export default settings(process.cwd());
