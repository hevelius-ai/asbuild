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
