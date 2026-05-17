"""Step 2: the extraction validation gate and the bug it fixes."""
from decimal import Decimal

from expense_pipeline.models import DecisionStatus


def test_unreadable_receipt_is_rejected_not_saved(make_pipeline, report):
    result = make_pipeline().run_report(report("blurry_receipt"), validate=True)
    assert result.decision.status is DecisionStatus.NEEDS_MORE_INFO
    assert result.decision.paid is False
    assert any("NOT saved" in line for line in result.transcript)


def test_disabling_validation_reproduces_the_overpayment_bug(make_pipeline, report):
    # True receipt total is 60.00; the unreadable image makes the model
    # hallucinate 60 * 1.9 = 114.00. Without the gate, that gets paid.
    result = make_pipeline().run_report(report("blurry_receipt"), validate=False)
    assert result.decision.paid is True
    assert result.decision.amount == Decimal("114.00")
    assert result.decision.amount > Decimal("60.00")  # money lost


def test_clean_receipt_passes_validation(make_pipeline, report):
    result = make_pipeline().run_report(report("small_trip"), validate=True)
    assert result.decision.status is DecisionStatus.APPROVED
