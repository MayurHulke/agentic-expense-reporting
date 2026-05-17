"""Mock payment tool. Records reimbursements instead of moving real money."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from expense_pipeline.privacy import pseudonymize


@dataclass
class PaymentService:
    payments: list[dict] = field(default_factory=list)

    def reimburse(self, employee, amount: Decimal, report_id: str) -> str:
        # Only a pseudonymous id reaches the third-party payment boundary.
        ref = f"pay-{len(self.payments) + 1:04d}"
        self.payments.append(
            {"ref": ref, "payee": pseudonymize(employee),
             "amount": str(amount), "report_id": report_id}
        )
        return ref
