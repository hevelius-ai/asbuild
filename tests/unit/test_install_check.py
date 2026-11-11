"""The clean-install job's check (tests/install_check.py): every outcome, not only the one CI has seen."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import install_check as ic  # noqa: E402


def plugin_tree(folder: Path, files: dict[str, bytes]) -> Path:
    for name, content in files.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(content)
    return folder


SHIPPED = {".claude-plugin/plugin.json": b'{"name": "asbuild"}\n', "scripts/a.py": b"print(1)\n"}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    shipped = plugin_tree(tmp_path / "repo" / "plugin", SHIPPED)
    monkeypatch.setattr(ic, "ROOT", shipped.parent)
    monkeypatch.delenv("GITHUB_ENV", raising=False)

    def listing(folder):
        doc = [{"id": "asbuild@hevelius-ai", "installPath": str(folder)}]
        path = tmp_path / "installed.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        return str(path)

    return tmp_path, listing


def test_a_matching_copy_passes_and_tells_the_next_step(setup, capsys, monkeypatch):
    tmp, listing = setup
    installed = plugin_tree(tmp / "cache", {k: v.replace(b"\n", b"\r\n") for k, v in SHIPPED.items()})
    env = tmp / "github_env"
    monkeypatch.setenv("GITHUB_ENV", str(env))
    assert ic.main([listing(installed)]) == 0
    assert "the installed copy matches plugin/ (2 files)" in capsys.readouterr().out
    assert env.read_text(encoding="utf-8") == f"ASBUILD_INSTALLED={installed}\n"


@pytest.mark.parametrize(
    "change, said",
    [
        ({"scripts/a.py": b"print(2)\n"}, "differs: scripts/a.py"),
        ({"scripts/extra.py": b"x\n"}, "only in the installed copy: scripts/extra.py"),
        ({"scripts/a.py": None}, "missing from the installed copy: scripts/a.py"),
    ],
)
def test_a_copy_that_differs_fails_and_says_how(setup, capsys, change, said):
    tmp, listing = setup
    files = {**SHIPPED, **{k: v for k, v in change.items() if v is not None}}
    files = {k: v for k, v in files.items() if change.get(k, b"") is not None}
    installed = plugin_tree(tmp / "cache", files)
    assert ic.main([listing(installed)]) == 1
    assert said in capsys.readouterr().out


def test_a_plugin_not_in_the_list_cannot_be_checked(setup, capsys):
    tmp, _ = setup
    path = tmp / "installed.json"
    path.write_text(json.dumps([{"id": "other@somewhere", "installPath": str(tmp)}]), encoding="utf-8")
    assert ic.main([str(path)]) == 2
    assert "asbuild@hevelius-ai is not in Claude Code's plugin list" in capsys.readouterr().out


def test_the_installed_marketplace_must_be_the_commit_checked_out(setup, capsys, monkeypatch):
    tmp, listing = setup
    installed = plugin_tree(tmp / "cache", SHIPPED)
    clone = tmp / "marketplaces" / "hevelius-ai"
    (clone / ".claude-plugin").mkdir(parents=True)
    (clone / ".claude-plugin" / "marketplace.json").write_text('{"name": "hevelius-ai"}', encoding="utf-8")
    other = tmp / "marketplaces" / "another"  # another marketplace's clone is not mistaken for AsBuild's
    (other / ".claude-plugin").mkdir(parents=True)
    (other / ".claude-plugin" / "marketplace.json").write_text('{"name": "another"}', encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=clone, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "x"],
        cwd=clone,
        check=True,
    )
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=clone, capture_output=True, text=True).stdout.strip()
    monkeypatch.setattr(ic, "MARKETPLACES", tmp / "marketplaces")
    assert ic.main([listing(installed), "--commit", head]) == 0
    assert ic.main([listing(installed), "--commit", "0" * 40]) == 1
    assert f"the marketplace was cloned at {head}, not at {'0' * 40}" in capsys.readouterr().out
    monkeypatch.setattr(ic, "MARKETPLACES", tmp / "nowhere")
    assert ic.main([listing(installed), "--commit", head]) == 2


def test_an_empty_commit_is_a_mismatch_not_a_skipped_check(setup, capsys, monkeypatch):
    """Clean-install review round 2: `--commit ""` (a failed `git rev-parse`) must not switch the check off."""
    tmp, listing = setup
    installed = plugin_tree(tmp / "cache", SHIPPED)
    monkeypatch.setattr(ic, "marketplace_commit", lambda: "a" * 40)
    assert ic.main([listing(installed), "--commit", ""]) == 1
    out = capsys.readouterr().out
    assert "not at the commit checked out" in out and "a newer commit is on the branch" in out
