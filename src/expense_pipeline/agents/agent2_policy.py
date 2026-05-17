"""Agent 2: total the receipts and analyze them against policy."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from expense_pipeline.models import Receipt
from expense_pipeline.policy import Policy


@dataclass
class PolicyAnalysis:
    total: Decimal
    categories: set[str]
    violations: list[str] = field(default_factory=list)
    recommend_approve: bool = True
    summary: str = ""


def run(receipts: list[Receipt], policy: Policy) -> PolicyAnalysis:
    total = sum((r.stated_total for r in receipts), Decimal("0"))
    categories = {r.category for r in receipts}
    violations: list[str] = []

    for r in receipts:
        cap = policy.per_category_caps.get(r.category)
        if cap is not None and r.stated_total > cap:
            violations.append(
                f"{r.source}: {r.category} {r.stated_total} exceeds cap {cap}"
            )

    recommend = not violations
    summary = (
        f"{len(receipts)} receipt(s), total {total} {policy.currency}, "
        f"categories {sorted(categories)}. "
        + ("Within policy." if recommend else f"{len(violations)} violation(s).")
    )
    return PolicyAnalysis(
        total=total,
        categories=categories,
        violations=violations,
        recommend_approve=recommend,
        summary=summary,
    )
