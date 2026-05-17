"""Deterministic mock extractor.

Reads a JSON "scanned receipt" fixture and returns an ExtractionResult that
mimics how a real vision model behaves at different image qualities:

* clear      -> accurate fields, high confidence
* blurry     -> accurate fields, low confidence (honest uncertainty)
* unreadable -> HALLUCINATED fields (inflated total, mismatched line items)
                with low confidence

The unreadable case is the heart of the Step 2 bug demo: a naive Agent 1 would
save that fabricated total and overpay; the validation gate refuses to.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from expense_pipeline.models import ExtractionResult, LineItem, Receipt

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "examples" / "fixtures"


class MockExtractor:
    name = "mock"

    def __init__(self, fixture_dir: Path = FIXTURE_DIR) -> None:
        self.fixture_dir = fixture_dir

    def extract(self, source: str) -> ExtractionResult:
        data = json.loads((self.fixture_dir / f"{source}.json").read_text())
        quality = data.get("image_quality", "clear")
        line_items = [
            LineItem(li["description"], Decimal(str(li["amount"]))) for li in data["line_items"]
        ]
        stated_total = Decimal(str(data["stated_total"]))

        if quality == "clear":
            receipt = Receipt(
                source, data["vendor"], data["date"], data["category"],
                line_items, stated_total,
            )
            return ExtractionResult(source, receipt, confidence=0.97)

        if quality == "blurry":
            receipt = Receipt(
                source, data["vendor"], data["date"], data["category"],
                line_items, stated_total,
            )
            return ExtractionResult(
                source, receipt, confidence=0.55,
                notes=["image is blurry; values uncertain"],
            )

        # unreadable: the model invents a plausible but wrong total and a
        # single vague line item that does not reconcile.
        hallucinated_total = (stated_total * Decimal("1.9")).quantize(Decimal("0.01"))
        receipt = Receipt(
            source, data.get("vendor", "Unknown"), data["date"], data["category"],
            [LineItem("itemized purchases", hallucinated_total)],
            hallucinated_total,
        )
        return ExtractionResult(
            source, receipt, confidence=0.38,
            notes=["image unreadable; fields are a low-confidence guess"],
        )
