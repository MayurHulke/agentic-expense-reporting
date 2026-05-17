"""MCP server exposing receipt extraction as a standard tool.

Frontier pattern: instead of the extractor being an in-process Python object,
it is a Model Context Protocol server. Any MCP-capable host (Claude Desktop,
Claude Code, an agent runtime) can discover and call `extract_receipt` over a
standard JSON-RPC channel, independent of language or process.

Run it:

    python -m expense_pipeline.mcp_server          # stdio transport (default)

This implementation wraps the deterministic MockExtractor so the server runs
with zero external setup; swapping in the Claude vision extractor is a
one-line change and does not affect the wire contract.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from expense_pipeline.extractors.mock import MockExtractor
from expense_pipeline.serde import extraction_to_dict

mcp = FastMCP("expense-receipt-extractor")
_extractor = MockExtractor()


@mcp.tool()
def extract_receipt(source: str) -> dict:
    """Extract structured fields from a receipt image reference.

    Returns the receipt fields plus a model confidence score and any notes.
    Callers must apply their own validation gate before trusting the data
    (see expense_pipeline.agents.agent1_extract).
    """
    return extraction_to_dict(_extractor.extract(source))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
