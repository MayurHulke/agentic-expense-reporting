"""Serialization between the domain models and the MCP wire format.

Kept in one place so the MCP server and client agree on the contract.
"""
from __future__ import annotations

from decimal import Decimal

from expense_pipeline.models import ExtractionResult, LineItem, Receipt


def extraction_to_dict(result: ExtractionResult) -> dict:
    receipt = None
    if result.receipt is not None:
        r = result.receipt
        receipt = {
            "source": r.source,
            "vendor": r.vendor,
            "date": r.date,
            "category": r.category,
            "line_items": [
                {"description": li.description, "amount": str(li.amount)}
                for li in r.line_items
            ],
            "stated_total": str(r.stated_total),
        }
    return {
        "source": result.source,
        "confidence": result.confidence,
        "notes": list(result.notes),
        "receipt": receipt,
    }


def extraction_from_dict(data: dict) -> ExtractionResult:
    receipt = None
    rd = data.get("receipt")
    if rd is not None:
        receipt = Receipt(
            source=rd["source"],
            vendor=rd["vendor"],
            date=rd["date"],
            category=rd["category"],
            line_items=[
                LineItem(li["description"], Decimal(str(li["amount"])))
                for li in rd["line_items"]
            ],
            stated_total=Decimal(str(rd["stated_total"])),
        )
    return ExtractionResult(
        source=data["source"],
        receipt=receipt,
        confidence=float(data["confidence"]),
        notes=list(data.get("notes", [])),
    )
