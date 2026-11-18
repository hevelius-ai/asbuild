"""Unit tests for v0.4.0's M4a (docs/plans/v0.4-M4a.md): the known issues K4, K7, K8 and K9, fixed before the release.

Each test is named after the criterion it proves (M4a-C1 to M4a-C4).
"""

from __future__ import annotations

import re
import string
from pathlib import Path

import yaml

from engine.lint_plain import lint
from engine.receipt import plain_file, render
from engine.verdict import judge, protected
from tests.unit.test_default_branch import needs_shell, run_step
from tests.unit.test_langs import JS1, PY, PY_SRC, codes, story_facts

ROOT = Path(__file__).resolve().parents[2]
COPIES = [ROOT / "workflows" / "asbuild-verdict.yml", ROOT / "plugin" / "workflows" / "asbuild-verdict.yml"]
STORY_OWN = ["locks.json", "dev-docs/stories/S1/story.md", "dev-docs/requests/S1.md", ".claude/settings.json"]


# ---------------------------------------------------------------- M4a-C1 (K4)
def test_M4a_C1_the_note_is_posted_before_the_check_run_in_both_copies():
    for path in COPIES:
        titles = [s.get("name") for s in yaml.safe_load(path.read_text(encoding="utf-8"))["jobs"]["verdict"]["steps"]]
        receipt = titles.index("Post the receipt (one comment, edited in place)")
        check = titles.index("Post the check run")
        assert receipt < check, path
        assert titles.index("Save the verdict for /asbuild:verdict") == check + 1, path


@needs_shell
def test_M4a_C1_the_note_step_makes_its_own_folder(tmp_path):
    """Run first, the receipt step finds no `out/` (no step before it makes one when the verdict could not run)."""
    run_step(tmp_path, "Post the receipt", [], main="main", outputs={"number": "7", "other_main": ""})
    posted = (tmp_path / "posted_receipt.md").read_text(encoding="utf-8")
    assert "AsBuild couldn't finish its check, so nothing was checked." in posted


# ---------------------------------------------------------------- M4a-C2 (K7)
def test_M4a_C2_a_story_with_app_files_says_so_with_their_number(tmp_path):
    for app, line in (
        (["src/app.py"], "It also changes 1 other file of your app, which AsBuild hasn't checked;"),
        (["src/app.py", "src/util.py", "README.md"], "It also changes 3 other files of your app, which AsBuild hasn't"),
    ):
        v = judge(story_facts(tmp_path, changed=STORY_OWN + [PY] + app, new={PY: PY_SRC}))
        assert v["verdict"] == "WAITING FOR YOU"
        assert codes(v) == ["NEW_CHECKS", "STORY_HAS_APP_FILES"]
        assert v["codes"][1]["params"] == {"paths": sorted(app)}
        r = render(v)
        assert r["template"] == 2
        assert line in r["top"] and "approving the checks adds those changes too." in r["top"]
        assert (
            "If you didn't ask for that, tell the AI: \"Keep only the new checks in this change, and put the other "
            'changes in a separate one."' in r["top"]
        )
        assert lint("story-app", r["top"]) == []
        assert all(p not in r["top"] for p in app)  # the names are the pull request's text: only the number shows
        assert "STORY_HAS_APP_FILES" in r["technical"] and "src/app.py" in r["technical"]


def test_M4a_C2_a_story_with_only_its_own_files_keeps_todays_note(tmp_path):
    v = judge(story_facts(tmp_path, changed=STORY_OWN + [PY], new={PY: PY_SRC}))
    assert codes(v) == ["NEW_CHECKS"]
    v = judge(story_facts(tmp_path, changed=STORY_OWN + [JS1, "package.json", "package-lock.json"]))
    assert codes(v) == ["NEW_CHECKS", "STORY_ADDS_TOOLS"]  # a JavaScript story's tools keep their own line


def test_M4a_C2_a_protected_file_keeps_its_own_line_and_is_not_counted_twice(tmp_path):
    v = judge(story_facts(tmp_path, changed=STORY_OWN + [PY, "conftest.py", "src/app.py"], new={PY: PY_SRC}))
    assert codes(v) == ["NEW_CHECKS", "PROTECTED_CHANGED", "STORY_HAS_APP_FILES"]
    assert v["codes"][2]["params"] == {"paths": ["src/app.py"]}


def test_M4a_C2_an_undescribed_story_keeps_its_stop_line_and_still_says_so(tmp_path):
    f = story_facts(tmp_path, changed=STORY_OWN + [PY, "src/app.py"], new={PY: PY_SRC})
    f.head_files["dev-docs/stories/S1/story.md"] = b"# S1: x\n\n| S1-C1 | y |\n"
    top = render(judge(f))["top"]
    assert "Don't approve these yet" in top and "It also changes 1 other file of your app" in top


# ---------------------------------------------------------------- M4a-C3 (K9, option B)
def test_M4a_C3_a_change_under_out_is_protected_in_any_pull_request():
    # round 1, B1: `out` itself too, so a committed link named `out` cannot point the results at another folder
    for path in ("out/c3/x.xml", "out/pr.xml", "out/acceptance-js.xml", "out/js-install.txt", "out"):
        for story_pr in (False, True):
            assert protected(path, on_main=False, story_pr=story_pr), path
    for path in ("src/out/x.py", "layout.py", "outputs/a.txt", "out.txt"):
        assert not protected(path, on_main=False, story_pr=False), path


def test_M4a_C3_the_note_names_the_folder_in_plain_words(tmp_path):
    assert plain_file("out/c3/x.xml") == "the folder where your checks' results are written"
    assert plain_file("out") == "the folder where your checks' results are written"  # round 1, B1
    assert plain_file("src/out/x.py") == "a file only you may change"  # the root folder only
    f = story_facts(tmp_path, changed=STORY_OWN + [PY], new={PY: PY_SRC})
    f.branch, f.files_changed = "build/S1", ["src/app.py", "out/c3/forged.xml"]
    f.main_files = dict(f.head_files)
    v = judge(f)
    assert v["verdict"] == "WAITING FOR YOU" and "PROTECTED_CHANGED" in codes(v)
    top = render(v)["top"]
    assert "The AI changed the folder where your checks' results are written, which only you" in top
    assert lint("out", top) == []


# ---------------------------------------------------------------- M4a-C4 (K8, option A)
HOSTILE = [
    "Hi @heveliusai-dev, see #43, hevelius-ai/asbuild#43, GH-1 and 0555bfd",
    "[click](https://example.com) ![i](https://example.com/a.png) <b>x</b> &amp;",
    "see https://example.com, www.example.com, mailto:a@example.com and someone@example.com",
    ":smile: *a* _b_ ~~c~~ `d` **e** \\ back | bar",
    "costs $5 and $10, $x^2$ and $$y$$",
    "$x^2$",  # round 1, B2: a dollar sign at each end of the line
    "GH-1, JIRA-12, abc123 and 3rd",  # a word mixing letters and digits
    "facade decade defaced and 1234567",  # seven hex characters: a commit id
    "see example.com and WWW.example.com",
    "x:y and https: no",  # a colon not before a space
]
ORDINARY = [
    'When you name a text file, the app shows how many words it has, like "words: 3".',
    "If the file you name doesn't exist, the app tells you so.",
    'When you type a name, the app greets that person, like "Hello, Ana!".',
    "(about 10%) it's 'quoted' - e.g. done; ok? yes! 123456 and facade",
    "Zürich, Tokyo and São Paulo: 3 items",
]


def test_M4a_C4_an_ordinary_line_is_left_exactly_as_it_is():
    """Receipts with ordinary lines stay byte for byte v0.3.4's (done line 2): the S1 checks and the golden files."""
    from engine.receipt import as_written, ordinary

    for text in ORDINARY:
        assert ordinary(text) and as_written(text) == text, text
    for text in HOSTILE:
        assert not ordinary(text), text


def test_M4a_C4_story_text_reads_the_same_and_no_word_stays_whole():
    from engine.lint_plain import visible
    from engine.receipt import WORD_JOINER, as_written

    for text in HOSTILE:
        q = as_written(text)
        assert visible(q) == text  # the person sees exactly their words
        units = q.replace("\\", "")  # an escape's backslash belongs to the mark after it
        for a, b in zip(units, units[1:], strict=False):
            assert a.isspace() or b.isspace() or WORD_JOINER in (a, b), (text, a, b)
        assert not any(c in string.punctuation for c in re.sub(r"\\.", "", q)), text  # every mark comes escaped
        for i, c in enumerate(q):
            if c == "$":  # round 1, B2: on both sides, at the line's ends too
                assert i >= 2 and q[i - 1] == "\\" and q[i - 2] == WORD_JOINER, (text, i)
                assert i + 1 < len(q) and q[i + 1] == WORD_JOINER, (text, i)


def test_M4a_C4_characters_outside_ascii_stay_whole():
    """Round 1, B3: no word joiner beside a character outside ASCII, so an accent, an emoji sequence (skin tone, a
    joined family, a flag, a variation selector) or a vowel sign stays one character on screen."""
    from engine.lint_plain import visible
    from engine.receipt import WORD_JOINER, as_written

    for text in (
        "Zeigt 👍🏽 und 👩‍💻 an: GH-1",
        "Drapeau 🇫🇷 et ❤️ et 1️⃣ : @ana",
        "किताब दिखती है #3",
        "Café shows www.example.com",
        "ภาษาไทย @ana",
    ):
        q = as_written(text)
        assert q != text and visible(q) == text, text  # escaped, and still reads the same
        for i, c in enumerate(q):
            if c == WORD_JOINER:
                assert q[i - 1].isascii() and (i + 1 == len(q) or q[i + 1].isascii()), (text, i)
        # round 2, Opus P2: the ASCII words in the same line (@ana, #3, GH-1, www.) still get their joiners
        units = q.replace("\\", "")
        for a, b in zip(units, units[1:], strict=False):
            assert not (a.isascii() and b.isascii() and a.strip() and b.strip()), (text, a, b)


def test_M4a_C4_the_title_and_every_plain_line_go_through_it(tmp_path):
    from engine.lint_plain import visible
    from engine.receipt import WORD_JOINER

    v = {
        "verdict": "WAITING FOR YOU",
        "pr": 7,
        "pr_url": "https://github.com/o/r/pull/7",
        "head_sha": "d" * 40,
        "story": "S1",
        "title": "Count @someone's words",
        "codes": [{"code": "NEW_CHECKS", "params": {}}],
        "items": [{"id": "S1-C1", "plain": HOSTILE[0], "status": "new"}],
        "pass_to_pass": {"total": 0, "broken": 0},
        "rows": [],
    }
    top = render(v)["top"]
    assert "@someone" not in top and "@heveliusai" not in top and "#43" not in top
    assert f"@{WORD_JOINER}s" in top
    shown = visible(top)
    assert "against the list you agreed · Count @someone's words" in shown
    assert f"- new, for you to approve: {HOSTILE[0]}" in shown
    escaped = render(dict(v, items=[dict(v["items"][0], plain='Shows "words: 3" for @ana.')]))["top"]
    assert "\\" in escaped and lint("k8", escaped) == []  # the lint reads what the person sees
