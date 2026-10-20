# CentrAlign AI — Autonomous Invoice Task Worker

A small, runnable proof of concept for the **AI Engineering Intern** assignment. It takes a natural-language invoice task, identifies the company, searches local invoice files, extracts and validates fields, writes to a simulated finance application, reads the record back, and reports evidence. It is intentionally limited to a sandbox rather than pretending to support every website or company workflow.

## Demo result

For the default request, the worker should select `ACME-2026-104` (the newer of two Acme invoices), extract **INR 22,750.00** due **2026-11-02**, write one row into the local SQLite ledger, and verify the stored values by reading the row back.

## Requirements

- Python 3.10+
- `pip`
- Optional: an OpenAI API key if you want LLM-based company/intent parsing. The demo works without one.

## Setup and run

```bash
cd centralign_ai_worker
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit. Enter a request and click **Run task**. Expand the execution trace to inspect each plan, action, observation, recovery, and verification event. The UI can export the trace as JSON.

### Optional LLM parsing

Set `OPENAI_API_KEY` in your shell before starting Streamlit. Optionally set `OPENAI_MODEL` (defaults to `gpt-4o-mini`). The LLM is used only to extract the task type and company name; the tool permissions and workflow remain explicit in Python. If the LLM call fails, the worker falls back to a deterministic parser. Do not put real company data or credentials into this demo.

### Run tests

```bash
python -m unittest discover -s tests -v
```

### Run without the UI

```bash
python - <<'PY'
from worker import AutonomousInvoiceWorker
result = AutonomousInvoiceWorker().run(
    "Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done."
)
print(result["status"], result["message"])
for event in result["events"]:
    print(event["kind"], event["message"])
PY
```

## Architecture

```text
Natural-language task
        |
        v
Intent/company extraction ---- optional LLM; deterministic fallback
        |
        v
Explicit task plan
        |
        v
Tool loop: search -> extract/validate -> save -> read-back verify
        |          |             |              |
        +----------+-------------+--------------+
                   execution events / audit log
                              |
                              v
                 status + evidence + trace
```

### Main modules

- `app.py`: Streamlit interface, trace viewer, saved-record table, JSON export, and demo reset.
- `worker.py`: intent parsing, plan, bounded execution loop, tool orchestration, recovery behavior, and outcome reporting.
- `InvoiceTools`: permitted tools for file search, field extraction, saving to the simulated finance app, and verification.
- `FinanceStore`: SQLite-backed internal finance application and audit log.
- `invoices/`: synthetic sample invoices. They are safe test fixtures, not real company data.
- `tests/`: tests for successful completion, missing input, unknown company, and duplicate prevention.

## Important design decisions

1. **Narrow scope over fake generality.** Only local `.txt` invoice files and a local SQLite ledger are supported. This lets the demo genuinely execute and verify a task end-to-end.
2. **Tools are explicit and constrained.** The worker can only call its registered invoice tools. File access is restricted to the configured invoice directory. It does not control a general-purpose computer or access third-party sites.
3. **Observe after every action.** Each tool result is appended to an event trace, which makes decisions inspectable and debuggable.
4. **Validate before writing.** Required fields and date/amount formats are checked. Missing or malformed data does not get silently guessed.
5. **Verify independently.** The worker queries SQLite after the write and compares invoice number, company, amount, currency, due date, and source file. It only reports `completed` if every check passes.
6. **Idempotency.** `invoice_number` is unique. Re-running the same task returns the existing record rather than inserting a duplicate.
7. **Bounded retries and execution.** Search is retried once when no result is found, and a maximum step budget prevents an unbounded loop. The current search retry is intentionally modest; it does not change the company identity.
8. **LLM is optional, not trusted with permissions.** If configured, the LLM extracts the task type/company. Python validates and executes a fixed set of tools. Without a key, deterministic parsing keeps the demo reproducible.

## How the autonomy loop maps to the assignment

| Assignment concept | Prototype behavior |
|---|---|
| Understand goal | Extracts task type/company; asks for input if company is missing |
| Plan | Produces an explicit sequence of tool steps |
| Select tools | Uses invoice search, extraction, save, and verification tools |
| Execute | Reads local files and writes a real SQLite record |
| Observe | Stores each tool result as an event |
| Adapt/recover | Retries a failed search once; stops safely on invalid extraction |
| Memory/context | Carries discovered file and extracted invoice in execution context |
| Human input | Requests clarification or review when required information is missing/invalid |
| Verify | Reads back the stored row and compares important fields |
| Evidence | Returns saved record, verification checks, and JSON execution trace |

## Assumptions

- The request is for invoice processing and names a company.
- The newest invoice means the greatest valid `Invoice Date` among matching local files.
- Sample invoices are UTF-8 text files with `Invoice Number`, `Company`, `Invoice Date`, `Due Date`, and `Total Due` fields.
- The internal system is represented by a local database; this is not an integration with a real finance platform.
- Human approval is represented by stopping and requesting review when the worker cannot safely extract the required fields. The prototype does not execute external payments or irreversible actions.

## Known limitations

- Only `.txt` invoice files are parsed; PDF, scanned documents, OCR, email, and browser interaction are not implemented.
- The baseline task planner is fixed to one invoice workflow. The optional LLM does not invent new tool sequences.
- The deterministic company parser handles common request wording, not arbitrary language. The optional LLM improves extraction but requires a configured API key and network access.
- Retry behavior is intentionally simple; there is no exponential backoff, distributed queue, or resumable long-running task store.
- The UI and SQLite store are intended for a local demo, not concurrent production use or multi-tenant data.
- Verification confirms that values were stored correctly; it does not prove that the source invoice is authentic or that the amount is commercially correct.
- There is no role-based access control, secrets manager, full prompt-injection defense, or production audit retention policy.

## What I would build next

1. Add a PDF/email connector and robust extraction with source-span evidence.
2. Add a typed tool registry and schema-validated plans, with per-tool permission scopes.
3. Add approval gates for sensitive writes and a policy engine for allowed actions.
4. Add structured retries, timeouts, idempotency keys, checkpointing, and task resumption.
5. Build an evaluation suite with success rate, field accuracy, tool-call efficiency, recovery rate, and false-completion rate.
6. Add a browser connector for a controlled sandbox application, then test dynamic UI states and recovery.
7. Add persistent company memory with explicit provenance, freshness, and tenant isolation.
8. Add observability, structured logs, and a replayable trace for debugging.

## Demo walkthrough (2–3 minutes)

1. Start the app and show the sample invoice files.
2. Submit the default Acme request.
3. Show that the worker selects the October invoice rather than September's invoice.
4. Expand the trace and explain the search, extraction, save, and read-back verification events.
5. Show the saved row and the verification checks.
6. Run the task again to demonstrate duplicate prevention.
7. Try a company that is not in the folder to show that the agent does not claim success without evidence.

## Submission checklist

- [x] Source code
- [x] Setup and run instructions
- [x] Architecture and design decisions
- [x] Assumptions and limitations
- [x] Models/APIs/frameworks disclosure
- [x] Tests
- [x] Demo walkthrough script
- [ ] Push this folder to a GitHub repository and add its URL to the application
- [ ] Record a short demo video or prepare a live demo

## Technologies and disclosure

- Python standard library: file operations, regular expressions, datetime validation, SQLite, JSON, unittest.
- Streamlit: local demo interface.
- OpenAI Python SDK: optional intent/company extraction only when `OPENAI_API_KEY` is set.
- No external browser/computer-use framework, external company connector, or real credentials are used.
