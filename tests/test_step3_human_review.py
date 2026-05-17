"""Step 3: expenses over $500 require a human before payment."""
from expense_pipeline.human_review import ScriptedReviewer
from expense_pipeline.models import DecisionStatus


def test_small_expense_is_auto_approved_without_human(make_pipeline, report):
    result = make_pipeline().run_report(report("small_trip"))
    assert result.decision.status is DecisionStatus.APPROVED
    assert result.decision.approvals == []  # no human consulted
    assert any("auto-approved" in line for line in result.transcript)


def test_large_expense_is_escalated_to_a_human(make_pipeline, report):
    result = make_pipeline().run_report(report("large_trip"))
    assert result.decision.status is DecisionStatus.APPROVED
    assert len(result.decision.approvals) >= 1  # a human signed off
    assert any("human review required" in line for line in result.transcript)


def test_human_rejection_blocks_payment(make_pipeline, report):
    reviewer = ScriptedReviewer(rejections={"mgr-eng": "Out of policy for this trip"})
    result = make_pipeline(reviewer=reviewer).run_report(report("large_trip"))
    assert result.decision.status is DecisionStatus.REJECTED
    assert result.decision.paid is False
