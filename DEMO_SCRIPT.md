# Demo Script — Autonomous Invoice Task Worker

**Duration:** Approximately 2–3 minutes

## 1. Introduction (15 seconds)

“I built a focused invoice-processing workflow because I wanted to demonstrate actual execution and verification rather than simulate a general-purpose agent. The worker processes synthetic invoice files in a sandbox and writes the results to a local SQLite finance ledger.”

## 2. Submit the task (15 seconds)

Submit the default Acme invoice request.

“The user specifies the desired outcome in natural language. The worker identifies the company, creates a plan for the supported workflow, and executes the required steps without needing the user to specify each tool call.”

## 3. Explain the execution trace (45 seconds)

Expand the trace and walk through invoice search, extraction, validation, saving, and read-back verification.

“Each tool action produces an observable result that is recorded in the execution trace. After saving the invoice, the worker reads the record back and compares the stored values. It reports success only when the implemented verification checks pass.”

## 4. Show the saved record (20 seconds)

Highlight invoice `ACME-2026-104`, amount INR 22,750.00, and due date `2026-11-02`.

“The worker selects the October invoice because its invoice date is later than the September invoice date. It then saves the extracted fields and verifies the resulting database record.”

## 5. Demonstrate reliability (30 seconds)

Run the same task again, then try a company that does not exist in the sample invoices.

“Repeated execution should not create a duplicate invoice record. When the requested company is unknown, the worker stops safely instead of reporting a false success. I also wrote unit tests for successful processing, missing company information, duplicate prevention, and unknown companies.”

## 6. Discuss design trade-offs and next steps (30 seconds)

“The workflow is intentionally constrained to invoice processing. An OpenAI model can optionally help extract task and company information, but Python controls the available tools and execution steps. With another two weeks, I would focus on dynamic tool selection, additional document and application integrations, stronger recovery and approval mechanisms, and systematic evaluation.”

## Important scope clarification

“This is a working proof of concept for a constrained local environment, not a general-purpose computer-use agent. The invoice files and finance ledger are local, and the prototype does not access real company systems.”