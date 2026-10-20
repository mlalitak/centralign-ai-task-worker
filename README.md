# CentrAlign AI — Autonomous Invoice Task Worker

A focused proof of concept for the **CentrAlign AI Engineering Intern** assignment. The worker accepts a natural-language invoice task, identifies the company, searches local sample invoices, extracts and validates fields, writes a record to a simulated finance application, reads the record back, and reports the outcome with an execution trace.

> **Scope and safety:** This is a local sandbox demo. It uses synthetic `.txt` invoices and a local SQLite database. It does not access real company systems, browse the web, or operate arbitrary desktop applications.

**GitHub repository:** https://github.com/mlalitak/centralign-ai-task-worker

## Demo result

For the default request, the worker should select `ACME-2026-104` (the newer of the two Acme invoices), extract **INR 22,750.00** due **2026-11-02**, write one row into the local SQLite ledger, and verify the stored values by reading the row back.

Example task:

> Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal system, and tell me once it is done.

## Features

- Natural-language task input through a Streamlit interface.
- Company/task extraction using an optional OpenAI model, with a deterministic parser fallback.
- Invoice discovery and field extraction from local text fixtures.
- Field validation before writing to the finance ledger.
- SQLite persistence and read-back verification.
- Structured execution trace showing goals, plans, actions, observations, and completion.
- Safe handling of missing/unknown company information and invalid invoice data.
- Duplicate prevention using invoice-number uniqueness and idempotent processing.
- JSON export of the execution trace.
- Unit tests for the core success and failure paths.

## Requirements

- Python 3.10 or newer
- `pip`
- Optional: an OpenAI API key for LLM-based task/company parsing. The demo works without one.

## Setup and run

From the directory containing this README:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, enter a task, and click **Run task**. Expand the execution trace to inspect the plan, tool calls, observations, and verification. The UI can export the trace as JSON.

### Optional LLM parsing

Set `OPENAI_API_KEY` in your shell before starting Streamlit. You may also set `OPENAI_MODEL`; the default is `gpt-4o-mini`.

The model is used only to extract the task type and company name. Tool permissions and the invoice workflow remain controlled by Python. If the model call fails or no key is configured, the worker falls back to deterministic parsing. Do not use real company data or credentials in this demo.

Example for the current shell:

```bash
export OPENAI_API_KEY="your-api-key"
# Optional:
export OPENAI_MODEL="gpt-4o-mini"
streamlit run app.py
```

Do not commit API keys. Keep them in environment variables or a local, ignored secrets file.

## Run the tests

```bash
python -m unittest discover -s tests -v
```

The included test suite covers:

- Requesting company information when it is missing.
- Processing an invoice and verifying the saved record.
- Avoiding duplicate records when a task is repeated.
- Failing safely when the requested company is unknown.

The four tests passed in the development run (`Ran 4 tests ... OK`). Run them again in your environment to confirm the current checkout.

## Run without the UI

```bash
python - <<'PY'
from worker import AutonomousInvoiceWorker

result = AutonomousInvoiceWorker().run(
    "Find the latest invoice from Acme Corp, extract the amount and due date, "
    "enter it into our internal system, and tell me once it is done."
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
Understand task and company
(optional LLM, with deterministic fallback)
        |
        v
Create a bounded execution plan
        |
        v
Search local invoices
        |
        v
Extract and validate fields
        |
        v
Save to local SQLite ledger
        |
        v
Read saved record back and compare values
        |
        v
Report status, evidence, and execution trace
```

### Main modules

| File or directory | Responsibility |
|---|---|
| `app.py` | Streamlit interface, trace viewer, saved-record table, JSON export, and demo reset. |
| `worker.py` | Task/company parsing, plan, bounded execution loop, tool orchestration, recovery, and outcome reporting. |
| `InvoiceTools` in `worker.py` | Permitted operations for invoice search, extraction, saving, and verification. |
| `FinanceStore` in `worker.py` | SQLite-backed simulated finance application and audit log. |
| `invoices/` | Synthetic sample invoice text files. |
| `tests/test_worker.py` | Tests for success, missing input, unknown company, and duplicate prevention. |
| `requirements.txt` | Python package dependencies. |
| `DEMO_SCRIPT.md` | Suggested walkthrough for a short demo. |

## Important design decisions

1. **Narrow scope over simulated generality.** The prototype supports local `.txt` invoices and a local SQLite ledger. It demonstrates a real end-to-end workflow instead of claiming to automate every company application.
2. **Explicit, constrained tools.** The worker can call only its registered invoice tools. It does not have arbitrary shell access or general-purpose computer control.
3. **Observe after actions.** Tool results are added to an execution trace so the workflow is inspectable and debuggable.
4. **Validate before writing.** Required fields and amount/date formats are checked. Missing or malformed values are not silently guessed.
5. **Verify independently.** After writing, the worker reads the row from SQLite and compares important invoice fields. A successful write alone is not treated as proof of completion.
6. **Idempotency.** The invoice number is unique. Repeating a task returns the existing record rather than creating a duplicate.
7. **Bounded recovery.** Search is retried once when no result is found, and a step budget prevents unbounded execution. Recovery is intentionally simple.
8. **LLM is optional and not trusted with permissions.** When configured, the model extracts the task type and company. Python controls the allowed tools and workflow. Without a key, deterministic parsing keeps the demo reproducible.

## How it maps to the assignment

| Assignment concept | Prototype behavior |
|---|---|
| Understand goal | Extracts task type/company and asks for input when company information is missing. |
| Plan | Creates an explicit sequence of tool steps. |
| Select tools | Uses invoice search, extraction, save, and verification tools. |
| Execute | Reads local files and writes a SQLite record. |
| Observe | Records tool results as execution events. |
| Adapt/recover | Retries a failed search once and stops safely on invalid extraction. |
| Maintain context | Carries discovered invoice information through the execution. |
| Human input | Requests clarification or review when it cannot safely proceed. |
| Verify | Reads the saved row back and compares important fields. |
| Provide evidence | Returns the saved record, verification checks, and JSON trace. |

## Assumptions

- The request concerns invoice processing and identifies a company.
- “Latest invoice” means the matching invoice with the greatest valid invoice date.
- Sample invoices are UTF-8 text files with fields such as invoice number, company, invoice date, due date, and total due.
- The internal system is represented by a local SQLite database, not a real finance platform.
- When required information is missing or invalid, the worker stops and requests clarification/review rather than guessing.
- The prototype does not execute payments or other irreversible external actions.

## Known limitations

- Only `.txt` invoice files are supported; PDF parsing, OCR, email, and browser interaction are not implemented.
- The baseline planner is fixed to the invoice workflow. The optional LLM does not invent arbitrary tool sequences.
- The deterministic parser handles common request wording, not every possible phrasing.
- Retry behavior is basic; there is no exponential backoff, distributed queue, or resumable long-running task store.
- The UI and SQLite database are intended for a local demo, not concurrent production use or multi-tenant data.
- Verification confirms that values were stored correctly; it does not prove that the source invoice is authentic or that the amount is commercially correct.
- Role-based access control, a secrets manager, comprehensive prompt-injection defenses, and production audit retention are not implemented.

## What I would build next

1. Add PDF/email connectors and extraction with source-span evidence.
2. Add a typed tool registry and schema-validated plans with per-tool permission scopes.
3. Add approval gates for sensitive writes and a policy engine for permitted actions.
4. Add structured retries, timeouts, idempotency keys, checkpoints, and task resumption.
5. Build an evaluation suite measuring task success, field accuracy, tool-call efficiency, recovery rate, and false-completion rate.
6. Add a browser connector for a controlled sandbox application and test dynamic UI states and recovery.
7. Add persistent company memory with provenance, freshness, and tenant isolation.
8. Add observability, structured logs, and replayable traces for debugging.

## Demo walkthrough (2–3 minutes)

1. Start the app and show the sample invoice files.
2. Submit the default Acme request.
3. Show that the worker selects the October invoice rather than the September invoice.
4. Expand the trace and explain search, extraction, save, and read-back verification.
5. Show the saved row and verification result.
6. Run the task again to demonstrate duplicate prevention.
7. Try a company not present in the invoice directory to show safe failure.

See [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) for a concise speaking outline.

## Submission status

- [x] Source code committed and pushed to GitHub.
- [x] Setup and run instructions.
- [x] Architecture, design decisions, assumptions, and limitations documented.
- [x] Frameworks and optional model/API use disclosed.
- [x] Unit tests included (4 tests passed in the development run).
- [x] Demo walkthrough instructions included.
- [ ] Record and share a demo video, or prepare a live walkthrough.
- [ ] Add the demo link to the application submission, if requested.

## Technologies and disclosure

- **Python standard library:** file operations, regular expressions, date/amount validation, SQLite, JSON, and `unittest`.
- **Streamlit:** local web interface.
- **OpenAI Python SDK:** optional task/company extraction when `OPENAI_API_KEY` is configured.
- **No browser/computer-use framework or real company connector** is used in this version.

## Repository

https://github.com/mlalitak/centralign-ai-task-worker
