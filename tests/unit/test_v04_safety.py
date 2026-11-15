"""Unit tests for v0.4.0's safety fixes from the AsChecked re-test (the owner's X1, D50): each named after its criterion
in docs/plans/v0.4-M1b.md.
"""

from __future__ import annotations

from engine.lint_plain import lint
from engine.receipt import plain_file, render
from engine.verdict import judge, protected
from tests.unit.test_langs import PY, PY_EV, PY_SRC, STORY, js_facts, lockfile

PYTEST_NAMES = (".pytest.ini", "pytest.toml", ".pytest.toml")


def test_SF_C1_pytests_other_settings_files_are_protected_everywhere():
    """pytest 9.2 reads these three as well as pytest.ini (proved by running: a `--deselect` in each dropped a test)."""
    for name in PYTEST_NAMES:
        for path in (name, f"app/{name}"):
            assert protected(path, False, False), path
            assert plain_file(path) == "the settings for how your checks run", path
    assert not protected("app/pytest_helpers.toml", False, False)


def test_SF_C1_a_build_that_adds_one_waits_for_the_person(tmp_path):
    main = {"locks.json": lockfile({PY: PY_SRC}), "dev-docs/stories/S1/story.md": STORY, PY: PY_SRC}
    for i, name in enumerate(PYTEST_NAMES):
        d = tmp_path / str(i)
        d.mkdir()
        v = judge(js_facts(d, evidence=PY_EV, changed=["app/count.py", name], main=main))
        assert v["verdict"] == "WAITING FOR YOU", name
        assert {"code": "PROTECTED_CHANGED", "params": {"path": name}} in v["codes"]
        assert v["items"][0]["status"] == "file_changed"
        top = render(v)["top"]
        assert "the settings for how your checks run" in top and lint(name, top) == []


def test_SF_C2_the_verdict_workflow_saves_its_verdict_for_the_skill_after_posting_it():
    from tests.unit.test_workflows import step, steps

    for name in ("asbuild-verdict.yml",):
        titles = [s.get("name") for s in steps(name)]
        assert titles.index("Save the verdict for /asbuild:verdict") == titles.index("Post the check run") + 1
        save = step(name, "Save the verdict for /asbuild:verdict")
        assert save["if"] == "always() && steps.pr.outputs.skip != 'true'"
        assert save["uses"].startswith("actions/upload-artifact@330a01c490aca151604b8cf639adc76d48f6c5d4")
        assert save["with"]["name"] == "asbuild-verdict-${{ github.event.workflow_run.head_sha }}"
        assert save["with"]["path"].split() == ["out/verdict.json", "out/summary.md"]
