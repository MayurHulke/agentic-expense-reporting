"""Step 5: high-risk expenses need two approvers in two departments."""
from expense_pipeline.human_review import ScriptedReviewer
from expense_pipeline.models import DecisionStatus


def test_high_risk_requires_two_distinct_departments(make_pipeline, report):
    result = make_pipeline().run_report(report("gift_highrisk"))
    assert result.decision.status is DecisionStatus.APPROVED
    depts = {a.approver.department for a in result.decision.approvals}
    assert len(result.decision.approvals) == 2
    assert len(depts) == 2  # segregation of duties
    assert any("dual-department" in line for line in result.transcript)


def test_either_department_can_veto(make_pipeline, report):
    reviewer = ScriptedReviewer(rejections={"mgr-fin": "Finance declines this gift"})
    result = make_pipeline(reviewer=reviewer).run_report(report("gift_highrisk"))
    assert result.decision.status is DecisionStatus.REJECTED
    assert result.decision.paid is False
