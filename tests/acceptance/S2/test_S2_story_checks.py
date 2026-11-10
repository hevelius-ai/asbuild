"""Story S2: the skill and its story-time checks.

Each test builds a small git repository in a temporary folder: a tiny app on main, then a story with its
acceptance tests in the working tree. It runs the plugin's story-time check script as a separate process,
with this Python (the project's own Python and pytest, decision C5), the way the skill runs it.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from engine import junit_classify, lock_check

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "plugin" / "scripts" / "asbuild_story_check.py"
SKILL = ROOT / "plugin" / "skills" / "story" / "SKILL.md"

APP_MAIN = '''import sys

from app import __version__


def main(argv):
    if argv[:1] == ["version"]:
        print(__version__)
        return 0
    print("usage: python -m app version", file=sys.stderr)
    return 2


sys.exit(main(sys.argv[1:]))
'''

REQUEST = (
    "I want the app to count the words in a text file. When I give it a file name, it should tell me how "
    "many words the file has.  If the file doesn't exist, it should say so — not crash.\n"
)

STORY = """# S1: Count words

## Request (the owner's words, unchanged)

{request}
## Criteria

| ID | Criterion | Cites |
| --- | --- | --- |
| S1-C1 | `python -m app count <file>` prints `words: <n>` as its last line and exits 0 | Request, sentence 2 |
| S1-C2 | For a missing file, `python -m app count <file>` exits 2 and its error output contains "no such file" | Request, sentence 3 |

## Plain checklist (approved by the owner; the receipt quotes it word for word)

| ID | plain: | Examples (approved) |
| --- | --- | --- |
| S1-C1 | When you name a text file, the app shows how many words it has, like "words: 3". | `words: 3` |
| S1-C2 | If the file you name doesn't exist, the app tells you so instead of crashing. | `no such file` |
"""

HEADER = '''import subprocess
import sys


def run_app(*args):
    return subprocess.run([sys.executable, "-m", "app", *args], capture_output=True, text=True)

'''

GOOD_C1 = '''
def test_S1_C1_counts_the_words_in_a_file(tmp_path):
    f = tmp_path / "three.txt"
    f.write_text("one two\\nthree\\n")
    out = run_app("count", str(f))
    assert out.returncode == 0
    assert out.stdout.strip().splitlines()[-1] == "words: 3"
'''

GOOD_C2 = '''
def test_S1_C2_a_missing_file_says_so(tmp_path):
    out = run_app("count", str(tmp_path / "missing.txt"))
    assert out.returncode == 2
    assert "no such file" in out.stderr.lower()
'''


def git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def make_repo(tmp_path, tests_source, story=None):
    """A git repository: the app committed on main; the story and its tests left in the working tree."""
    repo = tmp_path / "repo"
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "__init__.py").write_text('__version__ = "0.1.0"\n')
    (repo / "app" / "__main__.py").write_text(APP_MAIN)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "app")
    story_dir = repo / "dev-docs" / "stories" / "S1"
    story_dir.mkdir(parents=True)
    (story_dir / "story.md").write_bytes((story or STORY.format(request=REQUEST)).encode("utf-8"))
    tests_dir = repo / "tests" / "acceptance" / "S1"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_S1_count.py").write_text(HEADER + tests_source)
    return repo


def run_checks(repo, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "S1", "--base", "main", *extra],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_S2_C1_two_check_story_passes_and_locks(tmp_path):
    repo = make_repo(tmp_path, GOOD_C1 + GOOD_C2)
    story_before = (repo / "dev-docs" / "stories" / "S1" / "story.md").read_bytes()
    keep = tmp_path / "evidence"
    out = run_checks(repo, "--lock", "--keep", str(keep))
    assert out.returncode == 0, out.stdout + out.stderr
    assert "S1-C1 ok" in out.stdout and "S1-C2 ok" in out.stdout
    assert out.stdout.strip().splitlines()[-1] == "story-time checks passed: 2 checks, 2 tests"
    # the owner's words are untouched, byte for byte
    story_after = (repo / "dev-docs" / "stories" / "S1" / "story.md").read_bytes()
    assert story_after == story_before and REQUEST.encode("utf-8") in story_after
    # the lock entries are the engine's own, so later build PRs see an unchanged lock
    test_file = repo / "tests" / "acceptance" / "S1" / "test_S1_count.py"
    locks = json.loads((repo / "locks.json").read_text(encoding="utf-8"))
    assert locks == {"files": {"tests/acceptance/S1/test_S1_count.py": lock_check.entry(test_file.read_bytes())}}
    assert locks["files"]["tests/acceptance/S1/test_S1_count.py"]["tests"] == [
        "test_S1_C1_counts_the_words_in_a_file",
        "test_S1_C2_a_missing_file_says_so",
    ]
    # CI's fails-before check would call both failures real ("strong"), not existence-only
    kinds = {}
    for xml in keep.glob("*.xml"):
        kinds.update(junit_classify.load(str(xml)) or {})
    assert sorted(kinds.values()) == ["strong", "strong"]


def test_S2_C2_test_passing_on_main_fails_with_reason(tmp_path):
    passing = '''
def test_S1_C1_counts_the_words_in_a_file(tmp_path):
    out = run_app("version")
    assert out.returncode == 0
    assert "words: 3" not in out.stdout
'''
    repo = make_repo(tmp_path, passing + GOOD_C2)
    out = run_checks(repo, "--lock")
    assert out.returncode == 1, out.stdout + out.stderr
    assert re.search(r"S1-C1 .*passes already on main", out.stdout)
    assert "S1-C2 ok" in out.stdout
    assert not (repo / "locks.json").exists()


def test_S2_C2_non_assertion_failure_fails_with_reason(tmp_path):
    other_reasons = '''
def test_S1_C1_counts_the_words_in_a_file(tmp_path):
    from app.count import count_words
    assert count_words("one two three") == "words: 3"


def test_S1_C2_a_missing_file_says_so(tmp_path):
    out = run_app("count", str(tmp_path / "missing.txt"))
    assert len(out.returncode) == 2
    assert "no such file" in out.stderr.lower()
'''
    repo = make_repo(tmp_path, other_reasons)
    out = run_checks(repo)
    assert out.returncode == 1, out.stdout + out.stderr
    assert re.search(r"S1-C1 .*fails on main for a reason other than an assertion.*ModuleNotFoundError", out.stdout)
    assert re.search(r"S1-C2 .*fails on main for a reason other than an assertion.*TypeError", out.stdout)


def test_S2_C2_unapproved_values_fail_with_reason(tmp_path):
    other_values = '''
def test_S1_C1_counts_the_words_in_a_file(tmp_path):
    f = tmp_path / "two.txt"
    f.write_text("one two\\n")
    out = run_app("count", str(f))
    assert out.stdout.strip().splitlines()[-1] == "words: 2"
'''
    repo = make_repo(tmp_path, other_values + GOOD_C2)
    out = run_checks(repo)
    assert out.returncode == 1, out.stdout + out.stderr
    assert re.search(r"S1-C1 .*does not check the approved example `words: 3`", out.stdout)
    assert "S1-C2 ok" in out.stdout


def test_S2_C3_skill_under_100_lines():
    text = SKILL.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert len(lines) < 100
    assert lines[0] == "---" and "---" in lines[1:]
    front = lines[1 : lines.index("---", 1)]
    assert any(line.startswith("name: ") for line in front)
    assert any(line.startswith("description: ") for line in front)
    assert "${CLAUDE_PLUGIN_ROOT}/scripts/asbuild_story_check.py" in text
