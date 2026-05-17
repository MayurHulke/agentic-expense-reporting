"""Receipt extractor that talks to the MCP server over stdio.

Implements the same `ReceiptExtractor` Protocol as the mock and Claude
extractors, so the pipeline is unchanged: only the transport differs. This
demonstrates the production seam where a capability lives behind the Model
Context Protocol rather than an in-process call.

Note: this opens a fresh stdio session per call for simplicity. A production
deployment would pool a long-lived session (or use the streamable-HTTP
transport behind a load balancer); see docs/mcp.md.
"""
from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Sequence

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from expense_pipeline.models import ExtractionResult
from expense_pipeline.serde import extraction_from_dict


def _payload(result) -> dict:
    """Extract the tool's dict payload across SDK output shapes."""
    sc = getattr(result, "structuredContent", None)
    if isinstance(sc, dict):
        # FastMCP wraps non-model returns under a single "result" key.
        if set(sc.keys()) == {"result"} and isinstance(sc["result"], dict):
            return sc["result"]
        if "source" in sc:
            return sc
    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            return json.loads(text)
    raise RuntimeError("MCP extract_receipt returned no usable payload")


class MCPExtractor:
    name = "mcp"

    def __init__(
        self,
        command: str = sys.executable,
        args: Sequence[str] = ("-m", "expense_pipeline.mcp_server"),
    ) -> None:
        self._params = StdioServerParameters(command=command, args=list(args))

    def extract(self, source: str) -> ExtractionResult:
        return asyncio.run(self._extract(source))

    async def _extract(self, source: str) -> ExtractionResult:
        async with stdio_client(self._params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("extract_receipt", {"source": source})
                if result.isError:
                    raise RuntimeError(f"MCP extract_receipt failed for {source!r}")
                return extraction_from_dict(_payload(result))
