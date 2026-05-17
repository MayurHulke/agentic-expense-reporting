"""Policy configuration loader (the spreadsheet 'policy' tab)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass
class Policy:
    currency: str
    human_review_threshold: Decimal
    dual_dept_threshold: Decimal
    extraction_confidence_threshold: float
    allowed_categories: list[str]
    high_risk_categories: list[str]
    per_category_caps: dict[str, Decimal]

    @classmethod
    def load(cls, path: Path) -> Policy:
        d = json.loads(Path(path).read_text())
        return cls(
            currency=d["currency"],
            human_review_threshold=Decimal(str(d["human_review_threshold"])),
            dual_dept_threshold=Decimal(str(d["dual_dept_threshold"])),
            extraction_confidence_threshold=float(d["extraction_confidence_threshold"]),
            allowed_categories=list(d["allowed_categories"]),
            high_risk_categories=list(d["high_risk_categories"]),
            per_category_caps={k: Decimal(str(v)) for k, v in d["per_category_caps"].items()},
        )
