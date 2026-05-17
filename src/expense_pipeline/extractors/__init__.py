"""Extractor selection: prefer the real Claude adapter, fall back to mock."""
from __future__ import annotations

from pathlib import Path

from expense_pipeline.extractors.base import ReceiptExtractor
from expense_pipeline.extractors.mock import MockExtractor

__all__ = ["ReceiptExtractor", "MockExtractor", "get_extractor"]


def get_extractor(prefer_real: bool = True) -> ReceiptExtractor:
    """Return a real Claude extractor if usable, otherwise the mock one."""
    if prefer_real:
        from expense_pipeline.extractors import claude

        if claude.is_available():
            image_dir = Path(__file__).resolve().parents[3] / "examples" / "fixtures"
            return claude.ClaudeExtractor(image_dir=image_dir)
    return MockExtractor()
