"""Privacy controls (Step 4).

Two concrete protections the written analysis calls for:

1. PII minimization/pseudonymization before data leaves the trust boundary
   (e.g. before a receipt or summary is sent to an external LLM).
2. Data-residency routing: EU employees' data must be stored/processed in the
   EU region. We model the store's region and refuse a cross-region write.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from expense_pipeline.models import Employee

# 13-19 digit card-like number, optionally space/dash separated.
_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


def redact_text(text: str) -> str:
    """Mask card-like numbers, keeping only the last 4 digits."""

    def _mask(m: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", m.group())
        return f"****-****-****-{digits[-4:]}" if len(digits) >= 4 else "****"

    return _CARD_RE.sub(_mask, text)


def pseudonymize(employee: Employee) -> str:
    """Send a stable opaque ID to external services, never the name."""
    return f"employee:{employee.id}"


class DataResidencyError(RuntimeError):
    """Raised when EU data would be written to a non-EU store."""


@dataclass
class RegionalDataStore:
    """Simulates the cloud spreadsheet 'data' tab with a residency region."""

    region: str  # "US" or "EU"

    def __post_init__(self) -> None:
        self._rows: list[dict] = []

    def write(self, employee: Employee, row: dict) -> None:
        if employee.region == "EU" and self.region != "EU":
            raise DataResidencyError(
                f"GDPR: {pseudonymize(employee)} is EU; refusing write to "
                f"{self.region} store. Route to an EU region."
            )
        self._rows.append({"owner": pseudonymize(employee), **row})

    @property
    def rows(self) -> list[dict]:
        return list(self._rows)
