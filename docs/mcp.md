# MCP and frontier architecture

This project ships a working **Model Context Protocol (MCP)** integration and is
designed around the agentic patterns considered production-grade in 2026. This
document explains what is implemented, why, and how it maps to frontier methods.

## What is implemented

The receipt-extraction capability, the costly, external, PII-sensitive
boundary, is exposed as a real MCP server and consumed through an MCP client:

| Piece | File | Role |
|---|---|---|
| MCP server | `src/expense_pipeline/mcp_server.py` | `FastMCP` server exposing the `extract_receipt` tool over stdio JSON-RPC |
| MCP client extractor | `src/expense_pipeline/extractors/mcp_client.py` | Implements the existing `ReceiptExtractor` Protocol; calls the tool over MCP |
| Wire contract | `src/expense_pipeline/serde.py` | Single shared (de)serialization so server and client cannot drift |
| Selection | `extractors/__init__.py` | `EXPENSE_EXTRACTOR=mcp` opts in; mock stays the zero-setup default |
| Proof | `tests/test_mcp_extractor.py` | Spawns the server as a subprocess and runs the full pipeline through it |

Run the pipeline over MCP:

```bash
pip install -e ".[mcp]"
EXPENSE_EXTRACTOR=mcp python -m expense_pipeline run examples/reports/gift_highrisk.json
```

The agentic flow is **identical** whether extraction is an in-process call or
an MCP tool call. That is the point: the protocol is the seam, not a rewrite.

## Why MCP here

- **Pluggable by contract, not by import.** The pipeline already depended on a
  `ReceiptExtractor` Protocol. MCP turns that into a language- and
  process-independent contract any host (Claude Desktop, Claude Code, an agent
  runtime) can call.
- **Single-purpose servers.** Each external capability (extraction, org
  directory, policy, payment) is a natural single-purpose MCP server, which is
  the recommended server shape.
- **Auth at the third-party boundary.** Remote MCP standardized on OAuth 2.1
  (June 2025 spec); the payment server is exactly where that belongs.

## Code execution with MCP: the privacy win (Step 4)

The strongest frontier pattern for this system is **code execution with MCP**.
Instead of loading all tool definitions and passing every result through the
model's context, the agent runs code in a sandbox and only logged results reach
the model. Anthropic reports tool-definition overhead dropping ~98.7% (150k to
2k tokens), and, critically for our GDPR analysis (Step 4), *sensitive data
stays in the execution environment and never enters the model context*. That is
a stronger guarantee than redaction alone: raw receipt PII is filtered before
it can reach the LLM.

## MCP vs A2A

In this system the Agent 1 to Agent 2 to Agent 3 hand-offs are
**Agent-to-Agent (A2A)** delegation; each agent's access to tools and data
(extraction, directory, policy, payment) is **MCP**. The 2026 consensus is to
use both: MCP for tools/data, A2A for task delegation between agents.

## Frontier-methods map

| Method (2026 practice) | Where in this project |
|---|---|
| Sustained execution on durable workflows | SOTA notes for Steps 3 and 5; next step is Temporal/LangGraph for the orchestrator |
| Reflection / LLM-as-judge | Step 2 SOTA note: a second model verifies extraction before the write |
| Plan-and-execute / model cascade | Step 6 SOTA note: cheap model first, escalate on low confidence (~90% cost cut) |
| Evals mirroring production, built before failures | Step 2 SOTA note: golden-set regression gate in CI |
| Structured / constrained output | The Step 2 fix: typed fields with confidence and abstention |
| MCP for tools, A2A for delegation | Implemented (extraction over MCP); agents delegate in sequence |

## Production gaps deliberately left open

- The client opens a fresh stdio session per call for clarity. Production
  pools a long-lived session or uses the streamable-HTTP transport behind a
  load balancer; the 2026 MCP roadmap targets stateless operation for exactly
  this horizontal-scaling reason.
- Only extraction is MCP-ified. Directory, policy, and payment are documented
  as the same pattern and are straightforward follow-ups.

## Sources

- [Architecture overview, Model Context Protocol](https://modelcontextprotocol.io/docs/learn/architecture)
- [The 2026 MCP Roadmap](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- [Code execution with MCP, Anthropic Engineering](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [MCP production growing pains, The New Stack](https://thenewstack.io/model-context-protocol-roadmap-2026/)
- [Agentic Design Patterns: The 2026 Guide](https://www.sitepoint.com/the-definitive-guide-to-agentic-design-patterns-in-2026/)
- [7 Agentic AI Trends to Watch in 2026, MachineLearningMastery](https://machinelearningmastery.com/7-agentic-ai-trends-to-watch-in-2026/)
