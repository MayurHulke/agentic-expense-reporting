"""Step 6: operational cost-driver classification, as runnable data."""
from __future__ import annotations

FLAT_LOW = "flat & low"
FLAT_HIGH = "flat & high"
VARIABLE = "highly variable"

COST_DRIVERS: dict[str, tuple[str, str]] = {
    "Database": (FLAT_LOW, "mostly fixed lookups / low storage"),
    "Spreadsheet": (FLAT_LOW, "cheap cloud storage"),
    "Mobile Web and Camera": (FLAT_LOW, "static front end + on-device camera"),
    "Agent 1": (VARIABLE, "multimodal vision LLM per receipt; dominant driver"),
    "Agent 2": (VARIABLE, "LLM inference per report"),
    "Agent 3": (VARIABLE, "LLM inference + review routing per report"),
    "Private infrastructure": (FLAT_HIGH, "base platform / monitoring"),
    "Payment service": (VARIABLE, "per-transaction fees scale with volume"),
}


def render_table() -> str:
    width = max(len(k) for k in COST_DRIVERS)
    lines = [f"{'Component'.ljust(width)}  {'Category'.ljust(16)}  Why"]
    lines.append("-" * (width + 2 + 16 + 2 + 40))
    for comp, (cat, why) in COST_DRIVERS.items():
        lines.append(f"{comp.ljust(width)}  {cat.ljust(16)}  {why}")
    return "\n".join(lines)
