"""Org directory (the HR database): employees and per-department approvers."""
from __future__ import annotations

import json
from pathlib import Path

from expense_pipeline.models import Approver, Employee


class OrgDirectory:
    def __init__(self, employees: dict[str, Employee], approvers: dict[str, Approver]) -> None:
        self._employees = employees
        self._approvers = approvers

    @classmethod
    def load(cls, path: Path) -> OrgDirectory:
        d = json.loads(Path(path).read_text())
        employees = {
            eid: Employee(eid, e["name"], e["role"], e["department"], e["region"])
            for eid, e in d["employees"].items()
        }
        approvers = {
            dept: Approver(a["id"], a["name"], a["department"])
            for dept, a in d["approvers"].items()
        }
        return cls(employees, approvers)

    def employee(self, employee_id: str) -> Employee:
        return self._employees[employee_id]

    def approver_for_department(self, department: str) -> Approver:
        return self._approvers[department]
