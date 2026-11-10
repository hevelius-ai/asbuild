"""Unit tests for plugin/scripts/asbuild_story_check.py: the story-time checks run in-process, for coverage."""

from __future__ import annotations

import ast
import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from engine import lock_check
from tests.acceptance.S2.test_S2_story_checks import GOOD_C1, GOOD_C2, REQUEST, STORY, git, make_repo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugin" / "scripts"))
import asbuild_story_check as sc  # noqa: E402

GOOD = GOOD_C1 + GOOD_C2


def run(repo, monkeypatch, capsys, *args):
    monkeypatch.chdir(repo)
    code = sc.main(["S1", "--base", "main", *args])
    return code, capsys.readouterr().out


# ------------------------------------------------------------------ the whole run


def test_pass_and_lock_keeps_other_entries(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, GOOD)
    other = {"tests/acceptance/S0/test_S0_x.py": {"sha256": "ab", "tests": ["test_S0_C1_x"]}}
    (repo / "locks.json").write_text(json.dumps({"files": other}), encoding="utf-8")
    code, out = run(repo, monkeypatch, capsys, "--lock")
    assert code == 0, out
    files = json.loads((repo / "locks.json").read_text(encoding="utf-8"))["files"]
    assert set(files) == {"tests/acceptance/S0/test_S0_x.py", "tests/acceptance/S1/test_S1_count.py"}
    # run again: the same entry is already there, unchanged, so locking again is fine
    assert run(repo, monkeypatch, capsys, "--lock")[0] == 0


def test_lock_never_changes_an_entry_locked_on_the_base(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, GOOD)
    rel = "tests/acceptance/S1/test_S1_count.py"
    (repo / "locks.json").write_text(json.dumps({"files": {rel: {"sha256": "old", "tests": []}}}), encoding="utf-8")
    git(repo, "add", "locks.json")
    git(repo, "commit", "-q", "-m", "an approved lock on main")
    code, out = run(repo, monkeypatch, capsys, "--lock")
    assert code == 1
    assert "is locked on main with other content" in out
    assert json.loads((repo / "locks.json").read_text(encoding="utf-8"))["files"][rel]["sha256"] == "old"


@pytest.mark.parametrize("content", ["not json", "[1]", '{"files": []}'])
def test_unreadable_lock_file_on_the_base_cannot_run(tmp_path, monkeypatch, capsys, content):
    repo = make_repo(tmp_path, GOOD)
    (repo / "locks.json").write_text(content, encoding="utf-8")
    git(repo, "add", "locks.json")
    git(repo, "commit", "-q", "-m", "a broken lock file on main")
    code, out = run(repo, monkeypatch, capsys, "--lock")
    assert code == 2 and "locks.json on main cannot be read" in out


def test_a_story_revised_before_approval_locks_again(tmp_path, monkeypatch, capsys):
    """Round 1, finding 4: an entry this branch wrote is not approved yet, so a revised test replaces it."""
    repo = make_repo(tmp_path, GOOD)
    assert run(repo, monkeypatch, capsys, "--lock")[0] == 0
    test_file = repo / "tests" / "acceptance" / "S1" / "test_S1_count.py"
    test_file.write_text(test_file.read_text().replace('"three.txt"', '"three-words.txt"'))
    code, out = run(repo, monkeypatch, capsys, "--lock")
    assert code == 0, out
    rel = "tests/acceptance/S1/test_S1_count.py"
    raw = (repo / "locks.json").read_bytes()
    assert json.loads(raw)["files"][rel] == lock_check.entry(test_file.read_bytes())
    assert b"\r" not in raw  # written with LF line ends on every system


def test_a_renamed_test_file_leaves_no_lock_entry_behind(tmp_path, monkeypatch, capsys):
    """Round 2, N3: a revision that renames a test file replaces this branch's entries, not only adds to them."""
    repo = make_repo(tmp_path, GOOD)
    other = {"tests/acceptance/S0/test_S0_x.py": {"sha256": "ab", "tests": ["test_S0_C1_x"]}}
    (repo / "locks.json").write_text(json.dumps({"files": other}), encoding="utf-8")
    git(repo, "add", "locks.json")
    git(repo, "commit", "-q", "-m", "story S0 approved on main")
    assert run(repo, monkeypatch, capsys, "--lock")[0] == 0
    folder = repo / "tests" / "acceptance" / "S1"
    (folder / "test_S1_count.py").rename(folder / "test_S1_word_count.py")
    code, out = run(repo, monkeypatch, capsys, "--lock")
    assert code == 0, out
    files = json.loads((repo / "locks.json").read_text(encoding="utf-8"))["files"]
    assert set(files) == {"tests/acceptance/S0/test_S0_x.py", "tests/acceptance/S1/test_S1_word_count.py"}


def test_a_title_with_request_in_it_still_needs_the_owners_words(tmp_path, monkeypatch, capsys):
    """Round 2, N1: only the template's Request heading opens the Request section."""
    story = STORY.format(request="").replace("# S1: Count words", "# S1: Request a word count")
    repo = make_repo(tmp_path, GOOD, story=story)
    code, out = run(repo, monkeypatch, capsys)
    assert code == 1 and "Request section is empty" in out
    assert sc.parse_story(story)[0] == ""


def test_one_test_carrying_two_check_ids_is_refused(tmp_path, monkeypatch, capsys):
    """Round 1, finding 2: one test per check, so a test may carry only one check ID."""
    both = """
def test_S1_C1_S1_C2_both(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("a b c")
    assert run_app("count", str(f)).stdout.strip() == "words: 3"
    assert "no such file" in run_app("count", str(tmp_path / "missing.txt")).stderr
"""
    repo = make_repo(tmp_path, both)
    code, out = run(repo, monkeypatch, capsys)
    assert code == 1 and "test_S1_C1_S1_C2_both carries more than one check ID" in out


def test_a_test_name_defined_twice_is_refused(tmp_path, monkeypatch, capsys):
    """Round 1, finding 3: a second test of the same name would be locked but never examined."""
    repo = make_repo(tmp_path, GOOD)
    second = repo / "tests" / "acceptance" / "S1" / "test_S1_more.py"
    second.write_text('def test_S1_C1_counts_the_words_in_a_file():\n    assert "words: 9" == ""\n')
    code, out = run(repo, monkeypatch, capsys)
    assert code == 1 and "test_S1_C1_counts_the_words_in_a_file is defined more than once" in out


def test_owner_words_starting_with_a_hash_are_kept(tmp_path, monkeypatch, capsys):
    """Round 1, finding 5: the Request section ends only at the template's next heading."""
    words = "# Word counter\n#1 thing I need: count the words in a file, and say so if the file is missing.\n"
    repo = make_repo(tmp_path, GOOD, story=STORY.format(request=words))
    code, out = run(repo, monkeypatch, capsys)
    assert code == 0, out
    request, _ = sc.parse_story(STORY.format(request=words))
    assert request == words.strip()


def test_messages_name_the_base_branch(tmp_path, monkeypatch, capsys):
    passing = """
def test_S1_C1_counts_the_words_in_a_file(tmp_path):
    assert "words: 3" == "words: 3"
"""
    repo = make_repo(tmp_path, passing + GOOD_C2)
    git(repo, "branch", "trunk")
    monkeypatch.chdir(repo)
    assert sc.main(["S1", "--base", "trunk"]) == 1
    assert "passes already on trunk" in capsys.readouterr().out


def test_the_skill_never_tells_the_agent_to_install_anything():
    """Round 1, finding 6: decision C5, nothing else is installed on the user's machine."""
    text = (Path(__file__).resolve().parents[2] / "plugin" / "skills" / "story" / "SKILL.md").read_text("utf-8")
    assert "install" not in text.lower()


@pytest.mark.parametrize("content", ["not json", '{"no_files": 1}', '{"files": []}', "[1]"])
def test_unreadable_lock_file_cannot_run(tmp_path, monkeypatch, capsys, content):
    repo = make_repo(tmp_path, GOOD)
    (repo / "locks.json").write_text(content, encoding="utf-8")
    code, out = run(repo, monkeypatch, capsys, "--lock")
    assert code == 2 and "locks.json cannot be read" in out


@pytest.mark.parametrize(
    "content, said",
    [
        ("not json", "cannot be read"),
        ("[1]", "it is not an object"),
        ('{"permissions": []}', "permissions is not an object"),
        ('{"permissions": {"deny": "Edit(x)"}}', "permissions.deny is not a list"),
    ],
)
def test_unreadable_settings_cannot_run_and_change_nothing(tmp_path, monkeypatch, capsys, content, said):
    """D26: the settings file is read before anything is written, so a bad one leaves no lock behind."""
    repo = make_repo(tmp_path, GOOD)
    (repo / ".claude").mkdir()
    (repo / ".claude" / "settings.json").write_text(content, encoding="utf-8")
    code, out = run(repo, monkeypatch, capsys, "--lock")
    assert code == 2 and ".claude/settings.json cannot be read" in out and said in out
    assert not (repo / "locks.json").exists()
    assert (repo / ".claude" / "settings.json").read_text(encoding="utf-8") == content


def test_a_claude_folder_that_is_a_file_cannot_run_and_changes_nothing(tmp_path, monkeypatch, capsys):
    """Round 1, finding 5: a file-system problem is exit 2, found before anything is written."""
    repo = make_repo(tmp_path, GOOD)
    (repo / ".claude").write_text("not a folder", encoding="utf-8")
    code, out = run(repo, monkeypatch, capsys, "--lock")
    assert code == 2 and ".claude/settings.json cannot be written" in out
    assert not (repo / "locks.json").exists()


def test_a_read_only_settings_file_cannot_run_and_changes_nothing(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, GOOD)
    (repo / ".claude").mkdir()
    settings = repo / ".claude" / "settings.json"
    settings.write_text("{}", encoding="utf-8")
    settings.chmod(stat.S_IREAD)
    try:
        code, out = run(repo, monkeypatch, capsys, "--lock")
    finally:
        settings.chmod(stat.S_IREAD | stat.S_IWRITE)
    assert code == 2 and ".claude/settings.json cannot be written" in out
    assert not (repo / "locks.json").exists()


def test_a_read_only_settings_file_that_has_the_line_already_passes(tmp_path, monkeypatch, capsys):
    """Round 2, finding 2: nothing needs writing, so a read-only file is no reason to stop."""
    repo = make_repo(tmp_path, GOOD)
    (repo / ".claude").mkdir()
    settings = repo / ".claude" / "settings.json"
    raw = '{"permissions": {"deny": ["Edit(/tests/acceptance/S1/**)"]}}'
    settings.write_text(raw, encoding="utf-8")
    settings.chmod(stat.S_IREAD)
    try:
        code, out = run(repo, monkeypatch, capsys, "--lock")
    finally:
        settings.chmod(stat.S_IREAD | stat.S_IWRITE)
    assert code == 0, out
    assert settings.read_text(encoding="utf-8") == raw


def test_a_write_that_fails_late_cannot_run(tmp_path, monkeypatch):
    def refuse(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "write_text", refuse)
    with pytest.raises(sc.CannotRun, match="cannot be written: denied"):
        sc.protect(tmp_path, "S1", {"permissions": {"deny": []}})


def test_an_unreadable_settings_file_cannot_run(tmp_path, monkeypatch):
    (tmp_path / ".claude" / "settings.json").mkdir(parents=True)  # a folder where the file should be
    with pytest.raises(sc.CannotRun, match="cannot be"):
        sc.read_settings(tmp_path, "S1")


def test_the_line_already_there_leaves_the_file_untouched(tmp_path):
    """Round 1, LOW: no formatting-only change in the story pull request."""
    (tmp_path / ".claude").mkdir()
    settings = tmp_path / ".claude" / "settings.json"
    raw = '{"permissions":{"deny":["Edit(/tests/acceptance/S1/**)"]}}'
    settings.write_text(raw, encoding="utf-8")
    sc.protect(tmp_path, "S1", sc.read_settings(tmp_path, "S1"))
    assert settings.read_text(encoding="utf-8") == raw


def test_a_refused_lock_adds_no_deny_rule(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, GOOD)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "story")
    code, _ = run(repo, monkeypatch, capsys, "--lock")
    assert code == 0
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "locked")
    git(repo, "branch", "-f", "approved")
    (repo / ".claude" / "settings.json").unlink()
    test_file = repo / "tests" / "acceptance" / "S1" / "test_S1_count.py"
    test_file.write_text(test_file.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    code, out = run(repo, monkeypatch, capsys, "--lock", "--base", "approved")
    assert "is locked on approved with other content" in out
    assert not (repo / ".claude" / "settings.json").exists()


def test_the_deny_rule_keeps_non_ascii_settings_and_writes_lf(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, GOOD)
    (repo / ".claude").mkdir()
    (repo / ".claude" / "settings.json").write_text('{"env": {"NOTE": "café"}}', encoding="utf-8")
    code, out = run(repo, monkeypatch, capsys, "--lock")
    assert code == 0 and "S1 tests protected: Edit(/tests/acceptance/S1/**) in .claude/settings.json" in out
    raw = (repo / ".claude" / "settings.json").read_bytes()
    assert b"\r\n" not in raw and "café".encode() in raw
    assert json.loads(raw) == {"env": {"NOTE": "café"}, "permissions": {"deny": ["Edit(/tests/acceptance/S1/**)"]}}


def test_without_lock_writes_no_lock_file_and_keep_saves_the_results(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, GOOD)
    assert run(repo, monkeypatch, capsys, "--keep", str(tmp_path / "kept"))[0] == 0
    assert not (repo / "locks.json").exists()
    assert (tmp_path / "kept" / "story-check.xml").is_file()


def test_output_without_reconfigure(tmp_path, monkeypatch):
    import io

    monkeypatch.setattr(sys, "stdout", io.StringIO())
    assert sc.main(["not-a-story"]) == 2
    assert "not a story ID" in sys.stdout.getvalue()


def test_cannot_run_cases(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert sc.main(["story1"]) == 2 and "not a story ID" in capsys.readouterr().out
    assert sc.main(["S1"]) == 2 and "not a git repository" in capsys.readouterr().out
    repo = make_repo(tmp_path, GOOD)
    monkeypatch.chdir(repo)
    assert sc.main(["S1", "--base", "origin/main"]) == 2 and "fetch it first" in capsys.readouterr().out
    assert sc.main(["S7", "--base", "main"]) == 2 and "no story file" in capsys.readouterr().out
    monkeypatch.setattr(sc.importlib.util, "find_spec", lambda name: None)
    assert sc.main(["S1", "--base", "main"]) == 2 and "pytest is not installed" in capsys.readouterr().out


def test_worktree_or_results_missing_cannot_run(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, GOOD)
    with pytest.raises(sc.CannotRun, match="could not check out"):
        sc.run_on_base(repo, "no-such-branch", "S1", None)
    real = subprocess.run
    monkeypatch.setattr(
        sc.subprocess, "run", lambda cmd, **kw: None if cmd[:3] == [sys.executable, "-m", "pytest"] else real(cmd, **kw)
    )
    with pytest.raises(sc.CannotRun, match="no results"):
        sc.run_on_base(repo, "main", "S1", None)
    assert len(git_out(repo, "worktree", "list").splitlines()) == 1  # the base worktree was removed


def git_out(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True).stdout.strip()


# ------------------------------------------------------------------ the story file


@pytest.mark.parametrize(
    ("story", "said"),
    [
        (STORY.format(request=""), "Request section is empty"),
        ("# S1: x\n\n## Request\n\nwords\n", "no checks"),
        (
            "# S1: x\n\n## Request\n\nw\n\n## Plain checklist\n\n| ID | plain: | Examples |\n| --- | --- | --- |\n"
            + "".join(f"| S1-C{i} | Line {i}. | `v{i}` |\n" for i in range(1, 7)),
            "at most 5",
        ),
        (STORY.format(request=REQUEST) + "\nAlso S1-C9.\n", "S1-C9 is not in the plain checklist"),
        (STORY.format(request=REQUEST).replace("| S1-C2 | If", "| S2-C2 | If"), "S2-C2 belongs to another story"),
        (
            STORY.format(request=REQUEST).replace("| S1-C2 | If the file", "| S1-C2 | | If the file"),
            "S1-C2 has no plain",
        ),
        (STORY.format(request=REQUEST).replace(" `no such file` |", " |"), "S1-C2 needs 1 to 3 approved examples"),
        (STORY.format(request=REQUEST).replace("`no such file`", "`a` `b` `c` `d`"), "S1-C2 needs 1 to 3"),
    ],
)
def test_story_file_problems(tmp_path, monkeypatch, capsys, story, said):
    repo = make_repo(tmp_path, GOOD, story=story)
    code, out = run(repo, monkeypatch, capsys)
    assert code == 1 and said in out, out


def test_parse_story_reads_request_checks_and_escaped_bars():
    text = (
        "# S1: x\n\n## Request\n\nline one\n\nline two\n\n## Plain checklist\n\n| ID | plain: | Ex |\n"
        "| --- | --- | --- |\n| S1-C1 | A \\| B. | `x \\| y` `3` |\n| S1-C2 | No examples column. |\n"
    )
    request, checks = sc.parse_story(text)
    assert request == "line one\n\nline two"
    assert checks == [
        {"id": "S1-C1", "plain": "A | B.", "examples": ["x | y", "3"]},
        {"id": "S1-C2", "plain": "No examples column.", "examples": []},
    ]


# ------------------------------------------------------------------ the tests and the base run


def test_test_naming_problems(tmp_path, monkeypatch, capsys):
    tests = (
        GOOD
        + """
def test_S1_C2_again(tmp_path):
    assert "no such file" == ""


def test_unrelated():
    assert "x" == "y"
"""
    )
    repo = make_repo(tmp_path, tests)
    (repo / "tests" / "acceptance" / "S1" / "test_S1_broken.py").write_text("def test_S1_C1(:\n")
    code, out = run(repo, monkeypatch, capsys)
    assert code == 1
    assert "test_unrelated carries none of this story's check IDs" in out
    assert "S1-C2 needs exactly one test named after it, found 2" in out
    assert "test_S1_broken.py cannot be read as Python" in out


def test_a_check_with_no_test(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, GOOD_C1)
    code, out = run(repo, monkeypatch, capsys)
    assert code == 1 and "S1-C2 needs exactly one test named after it, found 0" in out


def test_no_tests_at_all_skips_the_base_run(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path, "")
    code, out = run(repo, monkeypatch, capsys)
    assert code == 1 and "found 0" in out


def test_class_tests_skips_errors_and_collection_failures(tmp_path, monkeypatch, capsys):
    tests = """
import pytest


class TestCount:
    expected = "words: 3"

    def test_S1_C1_counts(self, tmp_path):
        f = tmp_path / "t.txt"
        f.write_text("a b c")
        assert run_app("count", str(f)).stdout.strip() == self.expected


@pytest.fixture
def broken():
    raise RuntimeError("fixture broke")


def test_S1_C2_missing(broken):
    assert "no such file" in ""
"""
    repo = make_repo(tmp_path, tests)
    code, out = run(repo, monkeypatch, capsys)
    assert code == 1
    assert "S1-C1 ok: test_S1_C1_counts" in out
    assert "S1-C2 test_S1_C2_missing could not run on main" in out
    skipped = tests.replace("def test_S1_C2_missing(broken):", "@pytest.mark.skip('later')\ndef test_S1_C2_missing():")
    repo2 = make_repo(tmp_path / "b", skipped)
    assert "is skipped on main" in run(repo2, monkeypatch, capsys)[1]
    (repo2 / "tests" / "acceptance" / "S1" / "test_S1_count.py").write_text(
        "import no_such_module\n\n" + "import subprocess\nimport sys\n" + GOOD
    )
    out3 = run(repo2, monkeypatch, capsys)[1]
    assert "did not run on main" in out3


def test_results_parametrised_case_that_passes_decides(tmp_path):
    xml = tmp_path / "r.xml"
    xml.write_text(
        "<testsuites><testsuite>"
        '<testcase classname="t" name="test_a[1]"><failure message="assert 1 == 2"/></testcase>'
        '<testcase classname="t" name="test_a[2]"/>'
        '<testcase classname="t" name="test_a[3]"><failure message="assert 1 == 3"/></testcase>'
        '<testcase classname="t" name="test_b[1]"><failure message="TypeError: x"/></testcase>'
        '<testcase classname="t" name="test_b[2]"><failure message="AssertionError: y"/></testcase>'
        '<testcase classname="t" name="test_c"><failure message="Failed: DID NOT RAISE ValueError"/></testcase>'
        '<testcase classname="t" name="test_d[1]"><failure message="assert 1 == 4"/></testcase>'
        '<testcase classname="t" name="test_d[2]"><failure message="assert 1 == 5"/></testcase>'
        "</testsuite></testsuites>"
    )
    r = sc.results(xml)
    assert r["test_a"][0] == "passed"
    assert r["test_b"] == ("other", "TypeError: x")
    assert r["test_c"][0] == "assertion"
    assert r["test_d"] == ("assertion", "assert 1 == 4")


# ------------------------------------------------------------------ the lock entry equals the engine's


@pytest.mark.parametrize(
    "raw",
    [
        b"def test_S1_C1_x():\n    assert 1\n",
        b"def test_S1_C1_x():\r\n    assert 1   \r\n\r\n\r\n",
        b"\xef\xbb\xbfdef test_S1_C1_x():\r    assert 1\t\n",
        b"async def test_S1_C1_y():\n  pass",
        b"\xff\xfe not utf-8 \n",
        b"",
    ],
)
def test_lock_entry_is_the_engines(raw):
    assert sc.entry(raw) == lock_check.entry(raw)


def test_lock_entry_on_the_story_fixture(tmp_path):
    repo = make_repo(tmp_path, GOOD)
    raw = (repo / "tests" / "acceptance" / "S1" / "test_S1_count.py").read_bytes()
    assert sc.entry(raw) == lock_check.entry(raw)


def test_matches_is_the_engines():
    from engine.verdict import matches

    for name in ["test_S1_C1_x", "test_S1_C10_x", "test_s1_c1", "test_S1_C1[a_b]", "test_xS1_C1"]:
        for check in ["S1-C1", "S1-C10"]:
            assert sc.matches(name, check) == matches(name, check)


# ------------------------------------------------------------------ check 2: the examples (F4's cases)

SOURCE = """
import pytest

GREETING = "Hello"
CASES = [("ann", 3), ("bob", 4)]


def test_fstring():
    name = "Ada"
    # the comment mentions "Goodbye, Ada!" but comments are never seen
    assert greet(name) == f"{GREETING}, {name}!"


def test_containers():
    suffix = "-v2"
    expected = {"status": "ready", "codes": [200, -1]}
    a, b = "pair-one", "pair-two"
    total: int = 7
    assert build() == expected
    assert tag() == "release" + suffix
    assert (a, b, total) == x
    assert +5 == y


@pytest.mark.parametrize("user,count", CASES)
def test_param_tuples(user, count):
    assert len(user) + 0 == count or user


@pytest.mark.parametrize("label", ["alpha", pytest.param("beta")])
def test_param_single(label):
    assert label.upper()


@pytest.mark.parametrize(["k"], [("gamma",)])
def test_param_list_names(k):
    assert k


@pytest.mark.parametrize(names_from_somewhere, [1])
def test_param_unknown_names(v):
    assert v == "zeta"


@pytest.mark.parametrize("v", CASES_UNKNOWN)
def test_param_unknown_rows(v):
    assert v


@pytest.mark.parametrize("a,b", [object()])
def test_param_odd_row(a, b):
    assert a


def test_message_is_not_checked():
    assert compute() == 1, "expected the word Banana"


def test_starred_attribute_and_keywords():
    base = ["mu"]
    items = [*base, "nu"]
    holder.attr = "omicron"
    assert items == z
    assert check(value="kappa", msg="lambda")


def test_unittest_calls(self):
    self.assertEqual(x(), "eta", msg="theta")
    self.assertIn(item="iota", container=y)


def test_unresolvable():
    width = compute()
    assert f"{width:>{pad}}" == z
    assert f"{'ab':d}" == z
    assert -"x" == z
    assert "a" + 1 == z
    assert loop == z
    assert x() == b"bytes"


class TestOrders:
    status = "shipped"

    def setUp(self):
        self.code = "Order #01001"

    def test_status(self):
        n = 1001
        assert order() == f"Order #{n:05d}"
        assert self.status == "x"
        assert self.code
        assert price() == 42.5
        assert "ok" in result()
"""


@pytest.mark.parametrize(
    ("name", "present", "absent"),
    [
        ("test_fstring", ["Hello, Ada!"], ["Goodbye, Ada!"]),
        ("test_containers", ["ready", 200, -1, "release-v2", "pair-one", 7, 5], []),
        ("test_param_tuples", ["ann", "bob", 3, 4], []),
        ("test_param_single", ["alpha", "beta"], []),
        ("test_param_list_names", ["gamma"], []),
        ("test_param_unknown_names", ["zeta"], [1]),
        ("test_message_is_not_checked", [1], ["expected the word Banana"]),
        ("test_unittest_calls", ["eta", "iota"], ["theta"]),
        ("test_starred_attribute_and_keywords", ["mu", "nu", "kappa"], ["lambda", "omicron"]),
        ("TestOrders.test_status", ["Order #01001", "shipped", 42.5, "ok", "x"], []),
    ],
)
def test_asserted_values(name, present, absent):
    got = sc.python_asserted(SOURCE, name)
    for v in present:
        assert v in got, (name, v, got)
    for v in absent:
        assert v not in got, (name, v, got)


def test_unresolvable_values_are_not_invented():
    # only the literals written inside the asserts come back; the unknown names add nothing
    assert sc.python_asserted(SOURCE, "test_unresolvable") == [">", "ab", "d", "x", "a", 1]
    assert sc.python_asserted(SOURCE, "test_param_unknown_rows") == []
    assert sc.python_asserted(SOURCE, "test_param_odd_row") == []


def test_find_py_test_misses():
    module = ast.parse(SOURCE)
    assert sc.find_py_test(module, "TestOrders.test_nothing") is None
    assert sc.find_py_test(module, "TestNone.test_status") is None
    assert sc.find_py_test(module, "test_nothing") is None


@pytest.mark.parametrize(
    ("example", "asserted", "ok"),
    [
        ("words: 3", ["words: 3"], True),
        ("no such file", ["error: no such file here"], True),
        ("Ord", ["Order #1"], False),  # under 4 characters: no substring match
        ("Paid in full", ["Paid"], False),  # an asserted string inside the example does not count
        ("42.5", [42.5], True),
        ("3", [3], True),
        ("3", [True], False),
        ("3", [3.0], False),
        ("7", ["words: 7"], False),
        ("words: 3", ["words: 30"], False),  # round 1, finding 1: a different value is not the example
        ("words: 3", ["the count is words: 3."], True),
        ("words: 3", ["xwords: 3"], False),
        ("Hello, Ada!", ["Hello, Ada!!"], True),  # the example's edges are not letters or digits
        ("Total: $10", ["Total: $10.50"], False),  # round 2, N2: a decimal part makes another value
        ("words: 3", ["words: 3.5"], False),
        ("words: 3", ["words: 3,000"], False),
        ("5 items", ["1.5 items"], False),
        ("5 items", ["1,5 items"], False),
        ("5 items", ["you have 5 items."], True),
        ("5 items", ["-5 items"], False),  # round 3 note: a sign makes another value
        ("5 items", ["+5 items"], False),
        ("$10.00", ["costs $10.00 today"], True),  # an example starting with a non-word character
        ("$10.00", ["costs $10.005"], False),
        ("$10.00", ["costs $10.00, paid"], True),
    ],
)
def test_example_matches(example, asserted, ok):
    assert sc.example_matches(example, asserted) is ok


def test_a_loop_variable_is_a_stated_limit(tmp_path, monkeypatch, capsys):
    """F4's one false flag: values reached only through a loop are not resolved, so the example reads as unchecked."""
    looped = (
        GOOD_C1
        + """
def test_S1_C2_a_missing_file_says_so(tmp_path):
    for text in ("no such file",):
        out = run_app("count", str(tmp_path / "missing.txt"))
        assert text in out.stderr.lower()
"""
    )
    repo = make_repo(tmp_path, looped)
    code, out = run(repo, monkeypatch, capsys)
    assert code == 1 and "does not check the approved example `no such file`: assert that exact value" in out


def test_git_helper_sets_identity_only_for_the_command(tmp_path):
    repo = make_repo(tmp_path, GOOD)
    git(repo, "status")
    assert git_out(repo, "log", "--format=%ae") == "t@example.com"
