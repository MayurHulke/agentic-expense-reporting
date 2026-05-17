"""Shared fixtures: always use the deterministic mock extractor in tests."""
from pathlib import Path

import pytest

from expense_pipeline.human_review import ScriptedReviewer
from expense_pipeline.orchestrator import Pipeline, load_report

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def make_pipeline():
    def _factory(reviewer=None, store_region="US"):
        return Pipeline.default(
            reviewer=reviewer or ScriptedReviewer(),
            store_region=store_region,
            prefer_real_extractor=False,
        )

    return _factory


@pytest.fixture
def report():
    def _load(name: str):
        return load_report(EXAMPLES / "reports" / f"{name}.json")

    return _load
