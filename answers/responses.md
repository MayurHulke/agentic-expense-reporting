# Project: Analyze and Extend an Agentic Expense Reporting System

## Step 1: System Documentation (Summary)

**Components:** Mobile web UI, mobile camera, Agent 1 (data extraction), Agent 2 (computation and policy comparison), Agent 3 (decision-making), third-party payment service.

**Data stores:** Database of reference images of allowable receipts, cloud-hosted spreadsheet (`data` tab and `policy` tab), HR database (employee role/department).

**Flow:**
1. Employee fills the expense form and uploads receipt photos on the mobile web UI.
2. **Agent 1** extracts transaction data from the receipt images and writes it to the spreadsheet `data` tab.
3. **Agent 2** totals the receipts, compares them against the `policy` tab, and produces a summary with an approve/reject recommendation and explanation.
4. **Agent 3** reviews Agent 2's analysis, factors in the employee's role and the purpose of the expense, then approves or rejects. On reject it returns an error message; on approve it calls the payment tool to reimburse the employee.

---

## Step 2: Find and Fix a Bug

### Location
The bug is in **Agent 1, the data-extraction-and-save step**, specifically the write path from Agent 1 to the spreadsheet `data` tab.

### Problem
Agent 1 uses a vision/LLM model to read receipt images and should record only values it actually read from the image. In practice, when a photo is blurry, cropped, glare-washed, dark, or partially missing, the model does not say "I can't read this." Instead it produces confident, plausible-looking numbers (a hallucinated vendor, date, or total) and writes them straight to the `data` tab. There is **no confidence check, no validation, and no cross-reference against the reference-image database** before the write. Because the `data` tab is the single source of truth that Agent 2 and Agent 3 depend on, every downstream computation and approval inherits the fabricated values, producing over- and under-payments.

### Solution
Insert a verification gate between extraction and the write: have Agent 1 return structured fields with a confidence score, validate them programmatically (line items sum to the stated total, valid date, vendor present, type matches the reference-image database), and only persist to the `data` tab when confidence and validation pass. If either fails, route the extracted values back to the employee on the mobile UI to confirm or correct before saving, so no unverified or hallucinated data ever reaches the spreadsheet.

### Production-grade approach (SOTA)
- **Constrained decoding / tool-use schema:** force the model to return a typed JSON object (function calling or grammar-constrained output) so fields are well-formed and a per-field abstention value ("unreadable") is possible instead of a fabricated guess.
- **Hybrid extraction:** run a deterministic OCR pass (for example a document-AI service) alongside the vision LLM and reconcile the two; disagreement lowers confidence and triggers human confirmation.
- **Calibrated, self-consistent confidence:** sample the extraction a few times (self-consistency) and treat disagreement across samples as low confidence; calibrate the threshold on a labelled set rather than guessing.
- **LLM-as-judge verification:** a second model verifies the extracted JSON against the image before the write, acting as an automated reviewer.
- **Regression eval harness:** a golden set of receipts with ground-truth fields, scored in CI, so accuracy and the hallucination rate cannot silently regress when the model or prompt changes.

---

## Step 3: Add Human Review

### Location
Add a **human approval gate inside Agent 3's decision logic, before it calls the payment tool**. When the computed report total exceeds $500, Agent 3 does not auto-pay; instead it pauses the workflow and routes the report to a designated human approver (the employee's manager / finance reviewer) via the mobile web UI or a notification, and only calls the payment tool after the human decides.

### Decision
The human reviewer can:
- **Approve** the expense as submitted.
- **Reject** it with a written reason (returned to the employee as the error message).
- **Partially approve** (approve compliant items, deny others).
- **Request more information / documentation** and send it back to the employee.
- **Escalate** to a higher approver.

### Data the human needs (and where it comes from)
- Original receipt images, from the camera upload / mobile web submission.
- Extracted line items and computed total, from the spreadsheet `data` tab and Agent 2.
- Agent 2's policy analysis and recommendation with explanation, plus Agent 3's reasoning, from the agents' outputs.
- Relevant policy excerpts, from the spreadsheet `policy` tab.
- Employee name, role, and department, from the HR database.
- Stated business purpose/justification, from the expense form submission.
- Employee's recent expense history, from the spreadsheet `data` tab (for pattern/duplicate checks).

### Production-grade approach (SOTA)
- **Durable interrupt/resume:** model the gate as a typed checkpoint in a durable workflow engine (LangGraph interrupts, Temporal, or Step Functions) so a paused report survives restarts and resumes deterministically when the human responds, instead of holding state in memory.
- **Policy-as-code thresholds:** keep the $500 limit and routing rules in a versioned policy module (OPA/Rego or a typed config) rather than hard-coded, so finance can change limits without a redeploy and every change is auditable.
- **Reviewer decision support:** pre-compute an anomaly/risk score (duplicate receipt, out-of-pattern vendor, split-to-avoid-threshold) and surface it with the receipt so the human decides faster and more accurately.
- **SLA and escalation timers:** auto-escalate or remind if a reviewer does not act within an SLA, and capture every decision in an immutable audit log for later review.

---

## Step 4: Ensure Customer Privacy (GDPR)

### Location: five places privacy can be compromised
1. **Mobile camera and receipt images in transit.** Receipts contain PII (names, last-4 card digits, location, itemized purchases) transmitted from the device to the backend.
2. **Cloud spreadsheet hosted in the US.** Extracted transaction and employee data for EU employees stored on US servers violates EU data-residency requirements.
3. **HR database hosted in the US.** Holds employee PII (name, role, department) accessed by Agent 2; same cross-border residency problem.
4. **The Agents (1/2/3) calling third-party LLM APIs.** Receipt images and employee PII are sent to an external model provider that may be US-based, may retain data, or may train on it, an uncontrolled cross-border transfer.
5. **Third-party payment service.** Receives employee identity and bank/payment details; another external processor of PII potentially outside the EU.

### Solution
- **Data residency / regional routing:** host EU employees' data (spreadsheet, HR DB, reference-image DB) in an EU region and route EU submissions so their data never crosses to the US.
- **Data minimization and redaction:** mask card numbers and strip non-essential PII before sending images/text to the LLM; pass an employee ID instead of a name (pseudonymization).
- **Encryption:** TLS in transit and encryption at rest for all stores and image uploads.
- **Vendor controls:** sign Data Processing Agreements with the LLM provider, cloud/spreadsheet vendor, and payment service; require zero-retention / no-training LLM endpoints and EU-based processing.
- **Governance:** lawful basis and consent, access controls and audit logging, and workflows for GDPR data-subject rights (access, correction, erasure) and retention limits.

### Production-grade approach (SOTA)
- **Automated PII detection and redaction:** run a PII recognizer (Presidio-style NER plus regex) over extracted text and images before any external call, instead of masking only card numbers by hand.
- **Tokenization / vaulting:** replace identifiers with format-preserving tokens held in a secure vault, so downstream agents, the spreadsheet, and the payment service operate on tokens and raw PII never spreads.
- **Zero-retention, in-region inference:** use an LLM endpoint contracted for no training and no retention, deployed in an EU region (or a confidential-computing / private deployment), so receipt images never leave the compliance boundary.
- **Policy-enforced residency:** make region a hard control (the implementation in this repo raises a `DataResidencyError` on a cross-region write) rather than a documented intention, plus DLP egress scanning and per-purpose retention with automated deletion.

---

## Step 5: Extend the Workflow

**Capability chosen:** *In special situations, require approval by two people in two different departments.*

### Capability
For high-risk expenses (categories such as gifts, client entertainment, amounts above a defined threshold, or cases where the natural approver is in the requester's own reporting line), the system requires **sequential approval from two managers in two different departments** (for example, the employee's department head and a Finance approver) before the payment tool is ever called. This enforces segregation of duties.

### Location and Data
The trigger logic lives in **Agent 3's decision step**, extending the human-review gate from Step 3. A policy lookup (spreadsheet `policy` tab) defines which categories/thresholds require dual approval; the **HR database** supplies the org structure to identify the correct two approvers in two distinct departments. The workflow orchestrator routes to Approver A, then Approver B; payment proceeds only if **both** approve, and any rejection ends the workflow with an explanation to the employee. The full audit trail (who approved, when, with what context) is written to the spreadsheet.

### Business Value
Strong fraud prevention and SOX/internal-control compliance through segregation of duties, reduced collusion and single-point-of-failure risk on high-value spend, and a defensible audit trail that lowers the cost of financial audits and error remediation.

### Production-grade approach (SOTA)
- **Durable multi-party workflow:** orchestrate the two approvals as a durable workflow with independent, parallel-or-sequential approval tasks, timeouts, and reassignment, so neither approver blocks indefinitely and the state is recoverable.
- **Formal segregation-of-duties control:** express the "two distinct departments, neither in the requester's reporting line" rule in policy-as-code and resolve approvers from the HR graph at runtime, so org changes never silently break the control.
- **Tamper-evident audit log:** append each approval to an append-only, hash-chained log (or signed records) so the audit trail is defensible for SOX, with notification/sign-off via the reviewers' normal channels.

---

## Step 6: Estimate Operational Cost Drivers

| Cost behavior | Activities / components |
|---|---|
| **Flat and low regardless of volume** | Cloud spreadsheet storage; `policy` tab configuration/maintenance; mobile web front-end hosting; reuse of the existing HR database. |
| **Flat and high regardless of volume** | Base platform/infra and monitoring; security and GDPR compliance program; LLM provider minimum/committed-use contracts; fixed-headcount human-review/finance team salaries. |
| **Highly variable, potentially expensive** | **Agent 1 multimodal vision LLM calls** (per receipt image, the largest driver, scales directly with receipt volume); Agent 2 and Agent 3 LLM inference (per report); **third-party payment-service transaction fees** (per reimbursement); image storage/egress at scale; human-review time for the >$500 and dual-approval paths (scales with the number of large/high-risk expenses). |

Template mapping (one mark per component): Database, Spreadsheet, Mobile Web and Camera = flat and low; Private infrastructure = flat and high; Agent 1, Agent 2, Agent 3, Payment service = highly variable.

### Production-grade approach (SOTA)
- **Model cascade / routing:** use a small cheap model for easy receipts and escalate to a large multimodal model only on low confidence, cutting the dominant Agent 1 cost without losing accuracy.
- **Prompt and result caching:** cache policy context and deduplicate identical receipt submissions so repeated tokens are not paid for twice.
- **Batch and async inference:** process non-urgent reports via batch APIs at a lower rate.
- **Cost observability:** attribute token spend per agent and per report (traced) so the most expensive paths are visible and optimizable, with budget alerts before overruns.

---

## Stand-Out (Optional): Pastry Food-Truck National Expansion

Three challenges solved with one agentic system:

1. **Market Ranking Agent** pulls demographic, foot-traffic, competition, permit-friendliness, and event-density data per metro, scores them against weighted success factors, and outputs a ranked top-20 with a justification per market. *Tools:* web/data APIs, scoring model, spreadsheet export.
2. **Per-Market Research Agents (fan-out):** for each top market, sub-agents (a) map best neighborhoods/events, (b) compile a licensing/health-permit to-do list from local government sources, and (c) draft personalized intro emails to local food writers and cooking-school students using a brand "achievements" knowledge base. *Tools:* web search, mapping API, RAG over press kit, email-draft tool with human approval before send.
3. **Cost-Watch Agent** tracks labor, gas, kitchen-rental, and ingredient prices across all markets on a schedule and raises an alert when a rolling average rises faster than a set threshold. *Tools:* price-feed APIs, time-series store, anomaly detection, notification tool.

**Orchestration:** an orchestrator agent triggers ranking, spawns per-market research sub-agents in parallel, and schedules the cost-watch agent on a recurring cron, with a human-in-the-loop checkpoint before any outbound emails or financial commitments.

---

## Implementation and Frontier Architecture

Every answer above is backed by a runnable reference implementation in this repository, not just described. The three-agent pipeline performs the Step 2 validation gate, the Step 3 human-review gate, the Step 4 PII redaction and data-residency enforcement, and the Step 5 dual-department approval, each covered by tests that run in CI.

The system is also built on 2026 frontier agentic patterns. The receipt-extraction capability is exposed as a working Model Context Protocol (MCP) server and consumed through an MCP client behind the same interface, so the agentic flow is identical whether extraction is an in-process call or a standard protocol tool call. The agents delegate in sequence (Agent-to-Agent), while their access to tools and data is MCP, which is the current consensus split. The strongest privacy benefit comes from the code-execution-with-MCP pattern, where sensitive receipt data stays in the execution environment and never enters the model context, a stronger guarantee than redaction alone. The full mapping of each answer to modern techniques (durable workflows, reflection / LLM-as-judge, model cascades, evals built before failures, OAuth at the payment boundary) is in `docs/mcp.md` and `docs/design.md`.
