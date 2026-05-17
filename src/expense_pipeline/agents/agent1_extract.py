"""Agent 1: extract receipt data and persist it.

This is where the Step 2 bug lived. The original Agent 1 wrote whatever the
vision model returned straight to the 'data' tab. On unreadable receipts the
model hallucinated a plausible total, so the company over/under-paid.

The fix is `_validate`: a gate that only persists data which is confident,
complete, in an allowed category, and arithmetically self-consistent. When the
gate is disabled (`validate=False`) you can reproduce the original overpayment
bug for comparison.
"""
from __future__ import annotations

from dataclasses import dataclass

from expense_pipeline.extractors.base import ReceiptExtractor
from expense_pipeline.models import Employee, ExpenseReport, Receipt
from expense_pipeline.policy import Policy
from expense_pipeline.privacy import RegionalDataStore


@dataclass
class ExtractionOutcome:
    ok: bool
    receipts: list[Receipt]
    messages: list[str]


def _validate(result, policy: Policy) -> list[str]:
    """Return a list of reasons the extraction must NOT be saved (empty == ok)."""
    problems: list[str] = []
    if result.receipt is None:
        return [f"{result.source}: nothing could be extracted"]
    if result.confidence < policy.extraction_confidence_threshold:
        problems.append(
            f"{result.source}: confidence {result.confidence:.2f} below "
            f"threshold {policy.extraction_confidence_threshold:.2f}"
        )
    r = result.receipt
    if r.category not in policy.allowed_categories:
        problems.append(f"{result.source}: category '{r.category}' not allowed")
    if r.computed_total != r.stated_total:
        problems.append(
            f"{result.source}: line items sum to {r.computed_total} but "
            f"stated total is {r.stated_total} (does not reconcile)"
        )
    return problems


def run(
    report: ExpenseReport,
    employee: Employee,
    extractor: ReceiptExtractor,
    policy: Policy,
    store: RegionalDataStore,
    *,
    validate: bool = True,
) -> ExtractionOutcome:
    receipts: list[Receipt] = []
    messages: list[str] = []

    for source in report.receipt_sources:
        result = extractor.extract(source)
        messages.extend(f"extract[{extractor.name}] {n}" for n in result.notes)

        problems = _validate(result, policy) if validate else []
        if problems:
            messages.extend(problems)
            messages.append(
                f"{source}: returned to employee for a clearer photo; NOT saved"
            )
            return ExtractionOutcome(ok=False, receipts=[], messages=messages)

        receipt = result.receipt
        store.write(
            employee,
            {
                "source": receipt.source,
                "vendor": receipt.vendor,
                "date": receipt.date,
                "category": receipt.category,
                "total": str(receipt.stated_total),
            },
        )
        receipts.append(receipt)
        messages.append(
            f"{source}: saved ({receipt.vendor}, {receipt.stated_total}) "
            f"conf={result.confidence:.2f}"
        )

    return ExtractionOutcome(ok=True, receipts=receipts, messages=messages)
