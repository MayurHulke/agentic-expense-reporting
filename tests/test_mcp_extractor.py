"""End-to-end test of the MCP transport.

Spawns the real MCP server as a subprocess over stdio, drives it through the
MCPExtractor (which implements the same Protocol as the mock), and runs the
full pipeline. Proves the agentic flow is identical whether extraction is an
in-process call or a Model Context Protocol tool call.
"""
from decimal import Decimal

import pytest

pytest.importorskip("mcp")

from expense_pipeline.extractors.mcp_client import MCPExtractor  # noqa: E402
from expense_pipeline.models import DecisionStatus  # noqa: E402
from expense_pipeline.orchestrator import Pipeline  # noqa: E402


@pytest.fixture(scope="module")
def mcp_pipeline():
    pipeline = Pipeline.default(prefer_real_extractor=False)
    pipeline.extractor = MCPExtractor()
    return pipeline


def test_mcp_extractor_reports_its_transport():
    assert MCPExtractor().name == "mcp"


def test_clear_receipt_over_mcp_matches_in_process(mcp_pipeline, report):
    result = mcp_pipeline.run_report(report("small_trip"))
    assert result.decision.status is DecisionStatus.APPROVED
    assert result.decision.amount == Decimal("38.50")
    assert result.decision.paid is True


def test_unreadable_receipt_over_mcp_still_hits_validation_gate(mcp_pipeline, report):
    result = mcp_pipeline.run_report(report("blurry_receipt"), validate=True)
    assert result.decision.status is DecisionStatus.NEEDS_MORE_INFO
    assert result.decision.paid is False
