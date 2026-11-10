"""Every workflow file in the repository parses as YAML and has the keys GitHub needs.

A plain YAML value containing ": " (for example `--only-binary=:all: -r`) is read as a mapping, and GitHub
rejects the whole file without running any job. This test is the local check that was missing.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
FILES = sorted([*ROOT.glob(".github/workflows/*.yml"), *ROOT.glob("workflows/*.yml")])


def test_there_are_workflow_files():
    assert {p.name for p in FILES} >= {"ci.yml", "asbuild-test.yml", "asbuild-verdict.yml"}


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_workflow_parses_with_trigger_and_jobs(path):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    assert doc.get("on", doc.get(True)), "no trigger"
    for job in doc["jobs"].values():
        for step in job["steps"]:
            assert isinstance(step.get("run", ""), str), step
