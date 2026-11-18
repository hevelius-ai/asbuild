"""M3-C2 and M3-C3: plugin/scripts/asbuild_js.py, the JavaScript facts setup and the story check share (the Vitest
table, the one stop list, the version readers) and the first story's command (docs/plans/v0.4-M3.md)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugin" / "scripts"))
import asbuild_js as js  # noqa: E402


def pkg(deps: dict | None = None, dev: dict | None = None, **extra) -> bytes:
    doc = dict(extra)
    if deps is not None:
        doc["dependencies"] = deps
    if dev is not None:
        doc["devDependencies"] = dev
    return json.dumps(doc).encode()


def lock(**versions: str) -> bytes:
    return json.dumps({"packages": {f"node_modules/{k}": {"version": v} for k, v in versions.items()}}).encode()


APP = {"react": "^18.3.1", "react-dom": "^18.3.1"}
VITE5 = {"vite": "^5.4.1"}


# ------------------------------------------------------------------ the Vitest table (design §4.4)


def test_M3_C2_the_table_pins_the_proven_vitest_for_each_vite():
    assert js.VITEST_FOR == {5: "3.2.4", 6: "3.2.4", 7: "4.1.12", 8: "5.1.0"}


@pytest.mark.parametrize(
    ("vite", "vitest", "problem"),
    [
        ((5, 4, 21), (3, 2, 4), None),
        ((6, 4, 6), (3, 2, 9), None),
        ((7, 3, 8), (4, 1, 12), None),
        ((8, 3, 8), (5, 1, 0), None),
        ((8, 3, 8), None, None),  # no Vitest yet: the first story adds it
        ((4, 5, 0), None, "Vite 4.5.0"),
        ((9, 0, 0), None, "Vite 9.0.0"),
        (None, None, "not built with Vite"),
        ((5, 4, 21), (4, 1, 12), "Vitest 4.1.12"),
        ((8, 3, 8), (5, 0, 2), "Vitest 5.0.2"),
        ((7, 0, 0), (4,), "Vitest 4"),  # a range with no minor cannot be matched to the table
    ],
)
def test_M3_C3_vite_and_vitest_are_checked_against_the_table(vite, vitest, problem):
    found = js.table_problem(vite, vitest)
    assert found is None if problem is None else problem in found


@pytest.mark.parametrize(
    ("spec", "version"),
    [
        ("^5.4.1", (5, 4, 1)),
        ("~6.4", (6, 4)),
        (">=7.0.0 <8", (7, 0, 0)),
        ("8.x", (8,)),
        ("v5.4.21", (5, 4, 21)),
        ("= 3.2.4", (3, 2, 4)),
        ("latest", None),
        ("*", None),
        ("workspace:*", None),
        ("npm:rolldown-vite@7.1.0", None),
        (5, None),
    ],
)
def test_M3_C3_a_range_gives_its_first_version_or_nothing(spec, version):
    assert js.version_of(spec) == version


def test_M3_C3_the_lockfile_wins_over_the_range():
    p = json.loads(pkg(APP, VITE5))
    assert js.installed("vite", p, json.loads(lock(vite="5.4.21"))) == (5, 4, 21)
    assert js.installed("vite", p, None) == (5, 4, 1)
    assert js.installed("vite", p, {"packages": {"node_modules/vite": {}}}) == (5, 4, 1)
    assert js.installed("vite", p, {"packages": []}) == (5, 4, 1)
    assert js.installed("vitest", p, None) is None


# ------------------------------------------------------------------ setup: the kind of repository and the stop list


@pytest.mark.parametrize(
    ("paths", "kind"),
    [
        ({"app.py", "package.json"}, "python"),
        ({"requirements.txt", "package.json"}, "python"),
        ({"pyproject.toml", "package.json"}, "python"),
        ({"tools/build.py", "web/package.json"}, "python"),
        ({"package.json", "src/App.tsx"}, "javascript"),
        ({"package.json", "node_modules/x/setup.py"}, "javascript"),  # installed packages never count
        ({"web/package.json", "web/src/App.tsx"}, "subfolder"),
        ({"README.md"}, "python"),
        ({"node_modules/x/package.json", "README.md"}, "python"),
        (set(), "python"),
    ],
)
def test_M3_C3_the_kind_of_repository_is_read_from_its_tracked_files(paths, kind):
    assert js.kind(paths) == kind


def test_M3_C3_the_subfolder_is_named():
    assert js.subfolder({"b/package.json", "a/package.json", "node_modules/q/package.json"}) == "a"


@pytest.mark.parametrize(
    ("package", "lockfile", "paths", "phrase"),
    [
        (b"{ not json", None, set(), "cannot be read"),
        (b"[1, 2]", None, set(), "cannot be read"),
        (pkg(APP, VITE5, workspaces=["packages/*"]), None, set(), "workspaces"),
        (pkg(APP, VITE5), None, {"pnpm-workspace.yaml"}, "workspaces"),
        (pkg({**APP, "next": "15.0.0"}), None, set(), "Next.js"),
        (pkg({"lodash": "4"}, {"prettier": "3"}), None, set(), "not a React app"),
        (pkg({**APP, "react-native": "0.76.0"}, VITE5), None, set(), "React Native"),
        (pkg(APP), None, set(), "not built with Vite"),
        (pkg(APP, {"vite": "^4.5.0"}), None, set(), "Vite 4.5.0"),
        (pkg(APP, {"vite": "latest"}), None, set(), "not built with Vite"),
        (pkg(APP, {**VITE5, "vitest": "^2.1.8"}), None, set(), "Vitest 2.1.8"),
        (pkg(APP, {**VITE5, "jest": "^29.7.0"}), None, set(), "Jest"),
        (pkg(APP, {**VITE5, "@playwright/test": "^1.48.0"}), None, set(), "Playwright"),
        (pkg(APP, {**VITE5, "playwright": "^1.48.0"}), None, set(), "Playwright"),
    ],
)
def test_M3_C3_each_shape_on_the_stop_list_stops_in_plain_words(package, lockfile, paths, phrase):
    found = js.stop_reason(package, lockfile, paths)
    assert found is not None and phrase in found
    assert found.startswith("AsBuild cannot check this project yet: ")


@pytest.mark.parametrize(
    ("package", "lockfile"),
    [
        (pkg(APP, VITE5), None),
        (pkg(APP, {"vite": "^8.0.0", "vitest": "5.1.0"}), None),
        (pkg(APP, {"vite": "^4.0.0"}), lock(vite="7.3.8")),  # the lockfile says what installs
        (pkg(APP, {**VITE5, "jest": "^29.7.0", "vitest": "3.2.4"}), None),  # Jest beside Vitest is allowed
        (pkg({**APP, **VITE5}), b"{ not json"),  # an unreadable lockfile: the ranges decide
        (b'{"dependencies": {"react": "18", "vite": "5"}, "devDependencies": "x"}', None),
    ],
)
def test_M3_C3_a_react_and_vite_app_on_the_table_passes(package, lockfile):
    assert js.stop_reason(package, lockfile, {"package.json"}) is None


def test_M3_C3_the_stop_list_is_one_list_in_its_order():
    assert [name for name, _ in js.STOP_LIST] == [
        "unreadable",
        "workspaces",
        "next",
        "react",
        "vite",
        "vitest",
        "jest",
        "playwright",
    ]


# ------------------------------------------------------------------ this computer's Node and npm


def fake(answers: dict[str, str | None]):
    """A stand-in for shutil.which and the version commands: {"node": "v24.22.1", "npm": "11.19.1"}."""

    def which(name):
        return f"/bin/{name}" if answers.get(name) is not None else None

    def run(cmd, cwd=None):
        return subprocess.CompletedProcess(cmd, 0, answers[Path(cmd[0]).name] + "\n", "")

    return which, run


@pytest.mark.parametrize(
    ("node", "npm", "phrase"),
    [
        ("v24.22.1", "11.19.1", None),
        ("v26.13.1", "11.21.0", None),
        ("v25.0.0", "12.0.0", None),
        (None, "11.19.1", "Node.js is not installed"),
        ("v24.22.1", None, "npm is not installed"),
        ("v22.11.0", "10.9.0", "Node.js 22.11.0"),
        ("v24.22.1", "11.18.0", "npm 11.18.0"),
        ("v24.22.1", "10.9.9", "npm 10.9.9"),
        ("garbage", "11.19.1", "Node.js garbage"),
    ],
)
def test_M3_C3_node_24_and_npm_11_19_are_required(monkeypatch, node, npm, phrase):
    which, run = fake({"node": node, "npm": npm})
    monkeypatch.setattr(js.shutil, "which", which)
    monkeypatch.setattr(js, "sh", run)
    found = js.tool_problem()
    if phrase is None:
        assert found is None
    else:
        assert phrase in found
        assert "https://nodejs.org" in found and "winget install --id OpenJS.NodeJS.LTS" in found


def test_M3_C3_a_version_command_that_fails_reads_as_too_old(monkeypatch):
    monkeypatch.setattr(js.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(js, "sh", lambda cmd, cwd=None: subprocess.CompletedProcess(cmd, 1, "", "boom"))
    assert "Node.js unknown" in js.tool_problem()


# ------------------------------------------------------------------ the first story's repair (M3-C2)


@pytest.mark.parametrize(
    ("name", "dropped"),
    [
        ("@rollup/rollup-linux-x64-gnu", True),
        ("@esbuild/darwin-arm64", False),  # no "-" before darwin: the proven rule leaves it (npm handles it)
        ("@swc/core-win32-x64-msvc", True),
        ("lightningcss-darwin-arm64", True),
        ("@tailwindcss/oxide-android-arm64", True),
        ("rollup-freebsd-ia32", True),
        ("@img/sharp-linux-arm", True),
        ("darwin-arm64-thing", False),
        ("react", False),
        ("my-darwin-tools", False),
    ],
)
def test_M3_C2_the_proven_platform_rule(name, dropped):
    assert bool(js.PLATFORM.search(name)) is dropped


def test_M3_C2_platform_names_are_dropped_from_dependencies_and_dev_only():
    doc = {
        "dependencies": {"react": "18", "@rollup/rollup-darwin-arm64": "4.24.0"},
        "devDependencies": {"@swc/core-win32-x64-msvc": "1.7.0", "vite": "5"},
        "optionalDependencies": {"@rollup/rollup-linux-x64-gnu": "4.24.0"},
    }
    assert js.drop_platform(doc) == ["@rollup/rollup-darwin-arm64", "@swc/core-win32-x64-msvc"]
    assert doc == {
        "dependencies": {"react": "18"},
        "devDependencies": {"vite": "5"},
        "optionalDependencies": {"@rollup/rollup-linux-x64-gnu": "4.24.0"},
    }
    assert js.drop_platform({"dependencies": "x"}) == []


@pytest.fixture
def app(tmp_path, monkeypatch):
    """A JavaScript project folder with a stand-in npm, node, git: every command is recorded, none runs."""
    (tmp_path / "package.json").write_text(
        json.dumps(
            {"name": "app", "dependencies": {**APP, "@rollup/rollup-darwin-arm64": "4.24.0"}, "devDependencies": VITE5},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "node_modules" / "react").mkdir(parents=True)
    (tmp_path / "node_modules" / "react" / "index.js").write_text("x", encoding="utf-8")
    calls: list[list[str]] = []
    state = {"main_lock": None, "fail": None, "vite": "5.4.21"}

    def run(cmd, cwd=None):
        calls.append([Path(cmd[0]).name, *cmd[1:]])
        tool = Path(cmd[0]).name
        if tool == "git" and cmd[1] == "rev-parse":
            return subprocess.CompletedProcess(cmd, 0, str(tmp_path) + "\n", "")
        if tool == "git" and cmd[1] == "show":
            ok = state["main_lock"] is not None
            return subprocess.CompletedProcess(cmd, 0 if ok else 128, state["main_lock"] or "", "" if ok else "no")
        if tool == "node":
            return subprocess.CompletedProcess(cmd, 0, "v24.22.1\n", "")
        if tool == "npm" and cmd[1] == "--version":
            return subprocess.CompletedProcess(cmd, 0, "11.19.1\n", "")
        if tool == "npm" and state["fail"] and state["fail"] in cmd:
            return subprocess.CompletedProcess(cmd, 1, "", "npm error code ERESOLVE\nnpm error last line\n")
        if tool == "npm" and "--package-lock-only" in cmd:
            if state["vite"] is not None:
                (tmp_path / "package-lock.json").write_text(lock(vite=state["vite"]).decode(), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(js.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(js, "sh", run)
    monkeypatch.chdir(tmp_path)
    return tmp_path, calls, state


NPM = ["--no-audit", "--no-fund", "--legacy-peer-deps"]


def test_M3_C2_tools_repairs_once_then_installs_the_tables_vitest(app, capsys):
    folder, calls, _ = app
    assert js.main(["tools"]) == 0
    out = capsys.readouterr().out
    npm = [c for c in calls if c[0] == "npm" and c[1] != "--version"]
    assert npm == [
        ["npm", "install", "--package-lock-only", *NPM],
        [
            "npm",
            "install",
            "--save-dev",
            "--save-exact",
            *NPM,
            "vitest@3.2.4",
            "jsdom",
            "@testing-library/react",
            "@testing-library/dom",
        ],
    ]
    assert not (folder / "node_modules").exists()
    doc = json.loads((folder / "package.json").read_text(encoding="utf-8"))
    assert "@rollup/rollup-darwin-arm64" not in doc["dependencies"] and doc["devDependencies"] == VITE5
    assert "@rollup/rollup-darwin-arm64" in out and "Vitest 3.2.4" in out
    assert out.strip().endswith(js.TOOLS_DONE)


def test_M3_C2_tools_with_nothing_to_drop_leaves_package_json_as_it_is(app, capsys):
    folder, _, _ = app
    text = json.dumps({"dependencies": APP, "devDependencies": {"vite": "^8.0.0"}}, indent=4) + "\n"
    (folder / "package.json").write_text(text, encoding="utf-8")
    _, calls, state = app
    state["vite"] = "8.3.8"
    js.remove_tree(folder / "node_modules")  # a fresh clone: nothing to remove
    assert js.main(["tools"]) == 0
    assert (folder / "package.json").read_text(encoding="utf-8") == text
    out = capsys.readouterr().out
    assert "Vitest 5.1.0" in out and "node_modules" not in out
    assert "vitest@5.1.0" in calls[-1]


def test_M3_C2_tools_refuses_after_the_first_javascript_story(app, capsys):
    _, calls, state = app
    state["main_lock"] = json.dumps({"files": {"tests/acceptance/S1/S1-C1.test.tsx": {"sha256": "x", "tests": []}}})
    assert js.main(["tools"]) == 1
    assert js.ALREADY_TOOLS in capsys.readouterr().out
    assert not [c for c in calls if c[0] == "npm" and c[1] == "install"]


def test_M3_C2_tools_runs_when_main_locks_only_python_checks(app):
    _, _, state = app
    state["main_lock"] = json.dumps({"files": {"tests/acceptance/S1/test_S1_x.py": {"sha256": "x", "tests": []}}})
    assert js.main(["tools"]) == 0
    state["main_lock"] = "{ not json"
    assert js.main(["tools"]) == 0


@pytest.mark.parametrize("step", ["--package-lock-only", "--save-exact"])
def test_M3_C2_an_npm_failure_stops_with_npms_own_lines(app, capsys, step):
    _, calls, state = app
    state["fail"] = step
    assert js.main(["tools"]) == 1
    out = capsys.readouterr().out
    assert "npm error last line" in out
    assert calls[-1][0] == "npm" and step in calls[-1]


@pytest.mark.parametrize(("vite", "phrase"), [("4.5.3", "Vite 4.5.3"), (None, "not built with Vite")])
def test_M3_C2_a_vite_off_the_table_stops_before_the_tools(app, capsys, vite, phrase):
    _, calls, state = app
    state["vite"] = vite
    assert js.main(["tools"]) == 1
    assert phrase in capsys.readouterr().out
    assert not [c for c in calls if "--save-exact" in c]


def test_M3_C2_tools_needs_node_and_npm_first(app, capsys, monkeypatch):
    _, calls, _ = app
    monkeypatch.setattr(js.shutil, "which", lambda name: None if name == "node" else f"/bin/{name}")
    assert js.main(["tools"]) == 1
    assert "Node.js is not installed" in capsys.readouterr().out
    assert not [c for c in calls if c[0] == "npm"]


def test_M3_C2_tools_outside_a_javascript_project_cannot_run(app, capsys):
    folder, _, _ = app
    (folder / "package.json").unlink()
    assert js.main(["tools"]) == 2
    assert "no package.json" in capsys.readouterr().out
    (folder / "package.json").write_text("{ broken", encoding="utf-8")
    assert js.main(["tools"]) == 2
    assert "package.json cannot be read" in capsys.readouterr().out


def test_M3_C2_tools_outside_git_cannot_run(app, capsys, monkeypatch):
    def run(cmd, cwd=None):
        return subprocess.CompletedProcess(cmd, 128, "", "not a git repository")

    monkeypatch.setattr(js, "sh", run)
    monkeypatch.setattr(js, "tool_problem", lambda: None)
    assert js.main(["tools"]) == 2
    assert "not a git repository" in capsys.readouterr().out


def test_M3_C2_a_read_only_file_in_node_modules_is_still_removed(app):
    folder, _, _ = app
    locked = folder / "node_modules" / "react" / "index.js"
    locked.chmod(0o444)
    assert js.main(["tools"]) == 0
    assert not (folder / "node_modules").exists()


def test_M3_C2_sh_runs_a_real_command():
    p = js.sh([sys.executable, "-c", "print('hi')"])
    assert p.returncode == 0 and p.stdout.strip() == "hi"


def test_M3_C2_anything_but_tools_prints_the_usage(capsys):
    assert js.main([]) == 2
    assert js.main(["repair"]) == 2
    assert capsys.readouterr().out.count("usage: asbuild_js.py tools") == 2


def test_M3_C2_output_to_a_stream_without_reconfigure(monkeypatch):
    import io

    stream = io.StringIO()  # a stream without reconfigure
    monkeypatch.setattr(sys, "stdout", stream)
    assert js.main(["x"]) == 2
    assert "usage" in stream.getvalue()
