"""Extractor selection.

Precedence: explicit MCP opt-in (EXPENSE_EXTRACTOR=mcp) -> real Claude adapter
if usable -> deterministic mock. The mock keeps the default path zero-setup;
MCP and Claude are opt-in like any production integration.
"""
from __future__ import annotations

import os
from pathlib import Path

from expense_pipeline.extractors.base import ReceiptExtractor
from expense_pipeline.extractors.mock import MockExtractor

__all__ = ["ReceiptExtractor", "MockExtractor", "get_extractor"]


def get_extractor(prefer_real: bool = True) -> ReceiptExtractor:
    """Return the configured extractor (see module docstring for precedence)."""
    if os.environ.get("EXPENSE_EXTRACTOR") == "mcp":
        from expense_pipeline.extractors.mcp_client import MCPExtractor

        return MCPExtractor()

    if prefer_real:
        from expense_pipeline.extractors import claude

        if claude.is_available():
            image_dir = Path(__file__).resolve().parents[3] / "examples" / "fixtures"
            return claude.ClaudeExtractor(image_dir=image_dir)
    return MockExtractor()
