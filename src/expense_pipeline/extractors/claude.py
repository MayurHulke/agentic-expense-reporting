"""Optional real receipt extractor backed by Claude vision.

Used only when ANTHROPIC_API_KEY is set and the `anthropic` SDK is installed;
otherwise the pipeline falls back to the mock extractor. This keeps the project
runnable with zero setup while showing the design is not a toy: the same
ReceiptExtractor interface swaps a deterministic stub for a real model.

Note: receipt images carry PII, so callers redact before invoking this (the
privacy layer covers Step 4). This adapter sends only what it is given.
"""
from __future__ import annotations

import base64
import json
import os
from decimal import Decimal
from pathlib import Path

from expense_pipeline.models import ExtractionResult, LineItem, Receipt

_PROMPT = (
    "Extract the receipt as strict JSON with keys: vendor (str), date "
    "(YYYY-MM-DD), category (one of meals, lodging, transport, supplies, gift, "
    "entertainment), line_items (list of {description, amount}), stated_total "
    "(number), confidence (0-1 float for how readable the receipt was). If a "
    "field is unreadable, lower confidence; do not guess."
)


def is_available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


class ClaudeExtractor:
    name = "claude"

    def __init__(self, image_dir: Path, model: str = "claude-opus-4-7") -> None:
        import anthropic

        self.image_dir = image_dir
        self.model = model
        self.client = anthropic.Anthropic()

    def extract(self, source: str) -> ExtractionResult:
        img_path = self.image_dir / f"{source}.png"
        media = base64.standard_b64encode(img_path.read_bytes()).decode()
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _PROMPT},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": media,
                            },
                        },
                    ],
                }
            ],
        )
        payload = json.loads(resp.content[0].text)
        line_items = [
            LineItem(li["description"], Decimal(str(li["amount"])))
            for li in payload["line_items"]
        ]
        receipt = Receipt(
            source,
            payload["vendor"],
            payload["date"],
            payload["category"],
            line_items,
            Decimal(str(payload["stated_total"])),
        )
        return ExtractionResult(source, receipt, confidence=float(payload["confidence"]))
