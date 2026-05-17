"""Domain models for the agentic expense-reporting pipeline.

These are plain dataclasses so the pipeline stays dependency-free and easy to
reason about. Money is handled as Decimal to avoid float rounding errors in
financial logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class DecisionStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    NEEDS_MORE_INFO = "needs_more_info"


@dataclass(frozen=True)
class LineItem:
    description: str
    amount: Decimal


@dataclass
class Receipt:
    source: str
    vendor: str
    date: str
    category: str
    line_items: list[LineItem]
    stated_total: Decimal

    @property
    def computed_total(self) -> Decimal:
        return sum((li.amount for li in self.line_items), Decimal("0"))


@dataclass
class ExtractionResult:
    """What an extractor returns for one receipt image.

    `confidence` is the model's self-reported certainty. The Step 2 bug is that
    the original Agent 1 ignored this and saved whatever came back; the fix is a
    validation gate that refuses to persist low-confidence or inconsistent data.
    """

    source: str
    receipt: Receipt | None
    confidence: float
    notes: list[str] = field(default_factory=list)


@dataclass
class Employee:
    id: str
    name: str
    role: str
    department: str
    region: str  # "US" or "EU" -> drives data-residency routing (Step 4)


@dataclass
class Approver:
    id: str
    name: str
    department: str


@dataclass
class ExpenseReport:
    report_id: str
    employee_id: str
    purpose: str
    receipt_sources: list[str]


@dataclass
class Approval:
    approver: Approver
    approved: bool
    note: str


@dataclass
class Decision:
    status: DecisionStatus
    amount: Decimal
    reason: str
    approvals: list[Approval] = field(default_factory=list)
    paid: bool = False
