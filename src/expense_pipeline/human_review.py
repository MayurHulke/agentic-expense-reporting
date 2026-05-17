"""Human-in-the-loop review (Step 3 and Step 5).

The pipeline never calls a human directly; it calls a HumanReviewer. The
default `ScriptedReviewer` makes the demo deterministic and lets tests assert
behavior. An interactive implementation would slot in via the same interface.

The reviewer is given exactly the data the written analysis says a human needs:
the report purpose, employee role/department, total, Agent 2's analysis, and
the per-receipt detail.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from expense_pipeline.models import Approval, Approver


@dataclass
class ReviewContext:
    report_id: str
    employee_name: str
    employee_role: str
    employee_department: str
    purpose: str
    total: Decimal
    policy_summary: str
    violations: list[str]


class HumanReviewer(Protocol):
    def decide(self, approver: Approver, ctx: ReviewContext) -> Approval: ...


class ScriptedReviewer:
    """Approves by default; `rejections` maps approver id -> reason to reject."""

    def __init__(self, rejections: dict[str, str] | None = None) -> None:
        self.rejections = rejections or {}

    def decide(self, approver: Approver, ctx: ReviewContext) -> Approval:
        if approver.id in self.rejections:
            return Approval(approver, approved=False, note=self.rejections[approver.id])
        note = (
            f"Reviewed {ctx.report_id}: {ctx.purpose!r} by {ctx.employee_role}; "
            f"total {ctx.total}. {ctx.policy_summary}"
        )
        return Approval(approver, approved=True, note=note)
