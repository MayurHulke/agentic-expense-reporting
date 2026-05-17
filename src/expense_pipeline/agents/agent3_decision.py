"""Agent 3: decide, escalate to humans, and pay.

Implements three answers from the written analysis:

* Step 3  - any report over the human-review threshold is escalated to a
            person before payment instead of auto-paying.
* Step 5  - high-risk categories (or very large totals) require two approvers
            in two DIFFERENT departments (segregation of duties).
* Step 4  - before Agent 3 "reasons" over the report, PII is redacted and the
            employee is pseudonymized, so no raw identity is processed/logged.
"""
from __future__ import annotations

from dataclasses import dataclass

from expense_pipeline.agents.agent2_policy import PolicyAnalysis
from expense_pipeline.directory import OrgDirectory
from expense_pipeline.human_review import HumanReviewer, ReviewContext
from expense_pipeline.models import (
    Approver,
    Decision,
    DecisionStatus,
    Employee,
    ExpenseReport,
)
from expense_pipeline.payment import PaymentService
from expense_pipeline.policy import Policy
from expense_pipeline.privacy import pseudonymize, redact_text

FINANCE_DEPT = "Finance"
FALLBACK_SECOND_DEPT = "Engineering"


@dataclass
class DecisionOutcome:
    decision: Decision
    messages: list[str]


def _required_approvers(
    employee: Employee, org: OrgDirectory, *, dual: bool
) -> list[Approver]:
    first = org.approver_for_department(employee.department)
    if not dual:
        return [first]
    # Second approver must be a different department (segregation of duties).
    second_dept = FINANCE_DEPT if employee.department != FINANCE_DEPT else FALLBACK_SECOND_DEPT
    second = org.approver_for_department(second_dept)
    return [first, second]


def run(
    report: ExpenseReport,
    employee: Employee,
    analysis: PolicyAnalysis,
    policy: Policy,
    org: OrgDirectory,
    reviewer: HumanReviewer,
    payments: PaymentService,
) -> DecisionOutcome:
    messages: list[str] = []

    # Step 4: redact + pseudonymize before any reasoning over the report.
    safe_purpose = redact_text(report.purpose)
    messages.append(
        f"privacy: reasoning payload uses {pseudonymize(employee)} and "
        f"redacted purpose {safe_purpose!r}"
    )

    if not analysis.recommend_approve:
        reason = "Policy violation(s): " + "; ".join(analysis.violations)
        messages.append(f"decision: REJECTED -> error message to employee ({reason})")
        return DecisionOutcome(
            Decision(DecisionStatus.REJECTED, analysis.total, reason), messages
        )

    high_risk = bool(analysis.categories & set(policy.high_risk_categories))
    needs_dual = high_risk or analysis.total >= policy.dual_dept_threshold
    needs_human = analysis.total > policy.human_review_threshold or needs_dual

    if not needs_human:
        ref = payments.reimburse(employee, analysis.total, report.report_id)
        messages.append(f"decision: auto-approved under threshold; paid {ref}")
        return DecisionOutcome(
            Decision(DecisionStatus.APPROVED, analysis.total,
                     "Within auto-approval limit", paid=True),
            messages,
        )

    why = []
    if analysis.total > policy.human_review_threshold:
        why.append(f"total {analysis.total} over {policy.human_review_threshold}")
    if high_risk:
        hits = sorted(analysis.categories & set(policy.high_risk_categories))
        why.append(f"high-risk category {hits}")
    if analysis.total >= policy.dual_dept_threshold:
        why.append(f"total over dual-dept threshold {policy.dual_dept_threshold}")
    messages.append("escalation: human review required (" + "; ".join(why) + ")")

    approvers = _required_approvers(employee, org, dual=needs_dual)
    if needs_dual:
        depts = {a.department for a in approvers}
        messages.append(
            f"step5: dual-department approval across {sorted(depts)}"
        )

    ctx = ReviewContext(
        report_id=report.report_id,
        employee_name=employee.name,
        employee_role=employee.role,
        employee_department=employee.department,
        purpose=report.purpose,
        total=analysis.total,
        policy_summary=analysis.summary,
        violations=analysis.violations,
    )

    approvals = []
    for approver in approvers:
        decision = reviewer.decide(approver, ctx)
        approvals.append(decision)
        verdict = "APPROVE" if decision.approved else "REJECT"
        messages.append(
            f"human[{approver.name}/{approver.department}]: {verdict} - {decision.note}"
        )
        if not decision.approved:
            return DecisionOutcome(
                Decision(DecisionStatus.REJECTED, analysis.total,
                         f"Rejected by {approver.name}: {decision.note}",
                         approvals=approvals),
                messages,
            )

    ref = payments.reimburse(employee, analysis.total, report.report_id)
    messages.append(f"decision: APPROVED by {len(approvals)} reviewer(s); paid {ref}")
    return DecisionOutcome(
        Decision(DecisionStatus.APPROVED, analysis.total,
                 "Approved after human review", approvals=approvals, paid=True),
        messages,
    )
