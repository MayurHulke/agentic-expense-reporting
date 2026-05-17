"""Receipt extractor interface.

The pipeline depends only on this Protocol, so the extraction model is
pluggable: a deterministic mock by default (zero setup, runs anywhere) and an
optional real Claude vision adapter when an API key is available.
"""
from __future__ import annotations

from typing import Protocol

from expense_pipeline.models import ExtractionResult


class ReceiptExtractor(Protocol):
    name: str

    def extract(self, source: str) -> ExtractionResult:
        """Read one receipt image reference and return structured fields."""
        ...
