# Demo script / interview talk track

**Opening (15 seconds):** “I chose a narrow invoice workflow because the assignment values real execution and verification over simulated breadth. This prototype reads synthetic invoices from a sandbox and writes to a local SQLite finance app.”

**Show the request (15 seconds):** Submit the default Acme invoice task. Explain that the worker extracts the company and makes a plan instead of asking the user to spell out each action.

**Show the trace (45 seconds):** Walk through search, extraction, validation, write, and read-back verification. Point out that every tool response is recorded and that the worker will not report success if verification fails.

**Show the saved record (20 seconds):** Highlight invoice `ACME-2026-104`, amount INR 22,750.00, and due date 2026-11-02. The October invoice is selected because its invoice date is newer than the September invoice.

**Show reliability (30 seconds):** Run the same task again. The unique invoice number makes the operation idempotent, so a duplicate row is not inserted. Try an unknown company and show that the worker stops instead of claiming completion.

**Explain trade-offs (30 seconds):** The planner is intentionally fixed to one workflow, while company extraction can optionally use an LLM. Tools and permissions remain explicit in code. Next steps would be PDF/email/browser connectors, policy-based approvals, checkpoints, and systematic evaluations.

**Be candid:** Do not describe this as a general computer-use agent. It is an end-to-end prototype for a constrained local environment.
