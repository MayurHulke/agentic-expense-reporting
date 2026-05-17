"""Smoke test: every shipped example runs and yields a sane decision."""
import pytest

from expense_pipeline.models import DecisionStatus
from expense_pipeline.privacy import DataResidencyError

EXPECTED = {
    "small_trip": DecisionStatus.APPROVED,
    "large_trip": DecisionStatus.APPROVED,
    "blurry_receipt": DecisionStatus.NEEDS_MORE_INFO,
    "gift_highrisk": DecisionStatus.APPROVED,
}


@pytest.mark.parametrize("name,status", EXPECTED.items())
def test_examples_produce_expected_status(make_pipeline, report, name, status):
    result = make_pipeline().run_report(report(name))
    assert result.decision.status is status
    assert result.transcript  # always explains itself


def test_eu_example_requires_eu_region(make_pipeline, report):
    with pytest.raises(DataResidencyError):
        make_pipeline(store_region="US").run_report(report("eu_resident"))
