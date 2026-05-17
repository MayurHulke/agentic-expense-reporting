"""Wires the three agents into the end-to-end flow.

mobile submission -> Agent 1 (extract + validate + save)
                   -> Agent 2 (total + policy)
                   -> Agent 3 (privacy redaction, decide, human review, pay)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from expense_pipeline.agents import agent1_extract, agent2_policy, agent3_decision
from expense_pipeline.directory import OrgDirectory
from expense_pipeline.extractors import get_extractor
from expense_pipeline.extractors.base import ReceiptExtractor
from expense_pipeline.human_review import HumanReviewer, ScriptedReviewer
from expense_pipeline.models import Decision, DecisionStatus, ExpenseReport
from expense_pipeline.payment import PaymentService
from expense_pipeline.policy import Policy
from expense_pipeline.privacy import RegionalDataStore

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


@dataclass
class PipelineResult:
    report_id: str
    decision: Decision
    transcript: list[str] = field(default_factory=list)


@dataclass
class Pipeline:
    policy: Policy
    org: OrgDirectory
    extractor: ReceiptExtractor
    reviewer: HumanReviewer
    store_region: str = "US"

    @classmethod
    def default(
        cls,
        *,
        reviewer: HumanReviewer | None = None,
        store_region: str = "US",
        prefer_real_extractor: bool = True,
    ) -> Pipeline:
        return cls(
            policy=Policy.load(EXAMPLES / "policy.json"),
            org=OrgDirectory.load(EXAMPLES / "org.json"),
            extractor=get_extractor(prefer_real=prefer_real_extractor),
            reviewer=reviewer or ScriptedReviewer(),
            store_region=store_region,
        )

    def run_report(self, report: ExpenseReport, *, validate: bool = True) -> PipelineResult:
        transcript: list[str] = []
        employee = self.org.employee(report.employee_id)
        transcript.append(
            f"submit: {report.report_id} by {employee.role} "
            f"({employee.department}, region={employee.region})"
        )

        store = RegionalDataStore(region=self.store_region)
        payments = PaymentService()

        extraction = agent1_extract.run(
            report, employee, self.extractor, self.policy, store, validate=validate
        )
        transcript += [f"agent1: {m}" for m in extraction.messages]
        if not extraction.ok:
            return PipelineResult(
                report.report_id,
                Decision(DecisionStatus.NEEDS_MORE_INFO, self.policy.human_review_threshold * 0,
                         "Extraction failed validation; employee asked to resubmit"),
                transcript,
            )

        analysis = agent2_policy.run(extraction.receipts, self.policy)
        transcript.append(f"agent2: {analysis.summary}")
        for v in analysis.violations:
            transcript.append(f"agent2: violation - {v}")

        outcome = agent3_decision.run(
            report, employee, analysis, self.policy, self.org, self.reviewer, payments
        )
        transcript += [f"agent3: {m}" for m in outcome.messages]
        return PipelineResult(report.report_id, outcome.decision, transcript)


def load_report(path: Path) -> ExpenseReport:
    d = json.loads(Path(path).read_text())
    return ExpenseReport(
        report_id=d["report_id"],
        employee_id=d["employee_id"],
        purpose=d["purpose"],
        receipt_sources=list(d["receipts"]),
    )
