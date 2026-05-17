# Design: where each rubric answer lives in the code

The repository ships two deliverables that mirror each other:

- the **written analysis** (`answers/responses.md`, plus the course `.docx`)
- a **runnable reference implementation** (`src/expense_pipeline/`) that
  actually performs the fixes and extensions the analysis proposes

This document maps each project step to the code that implements it so a
reviewer can run the claim, not just read it.

## Pipeline shape

```
mobile submission (examples/reports/*.json)
  -> Agent 1  src/expense_pipeline/agents/agent1_extract.py   extract + validate + save
  -> Agent 2  src/expense_pipeline/agents/agent2_policy.py    total + policy analysis
  -> Agent 3  src/expense_pipeline/agents/agent3_decision.py  redact, decide, human review, pay
orchestrated by src/expense_pipeline/orchestrator.py
```

The receipt extractor is pluggable (`extractors/`): a deterministic mock by
default, an optional Claude vision adapter when `ANTHROPIC_API_KEY` is set.

## Step-by-step mapping

| Step | Claim in the analysis | Code that implements it | Proven by |
|---|---|---|---|
| 2. Bug + fix | Agent 1 saved hallucinated data with no validation gate | `agent1_extract._validate` (confidence threshold, category check, arithmetic reconciliation) | `tests/test_step2_validation.py` — rejected with the gate; overpays `$60 -> $114` with `--no-validation` |
| 3. Human review | Reports over $500 escalate to a person before payment | `agent3_decision.run` (`needs_human` branch) | `tests/test_step3_human_review.py` |
| 4. Privacy | Redact PII, pseudonymize, enforce EU data residency | `privacy.py` (`redact_text`, `pseudonymize`, `RegionalDataStore`) | `tests/test_step4_privacy.py` — EU report blocked on a US store |
| 5. Extension | High-risk expenses need two approvers in two departments | `agent3_decision._required_approvers` | `tests/test_step5_dual_dept.py` — two distinct departments, either can veto |
| 6. Cost drivers | Classify each component's cost behavior | `cost.py` | `python -m expense_pipeline cost` |

## Design choices worth noting

- **Zero-setup, deterministic by default.** No API keys or cloud accounts to
  run or grade it. The mock extractor makes the Step 2 hallucination
  reproducible on demand.
- **Money is `Decimal`.** Financial logic never touches binary floats.
- **Agents depend on interfaces, not implementations.** The extractor and the
  human reviewer are Protocols, so the real-Claude adapter and an interactive
  approver slot in without touching the agents.
- **Privacy is enforced, not advisory.** A cross-region write raises
  `DataResidencyError` and stops the pipeline, mirroring a hard GDPR control.
- **MCP is a real transport, not a slide.** The extractor Protocol is also
  served over the Model Context Protocol; the same pipeline runs unchanged with
  `EXPENSE_EXTRACTOR=mcp`. See [`mcp.md`](mcp.md) for the frontier-methods map.

## Try it

```bash
make setup
make demo     # runs every scenario, including the Step 2 bug reproduction
make check    # ruff + pytest
```
