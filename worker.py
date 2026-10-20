"""Autonomous invoice task worker for the CentrAlign AI intern assignment.

Uses a small, explicit tool loop and a local SQLite finance app. No real company
systems or credentials are accessed. An optional LLM planner can be added later;
the baseline planner is deterministic so the project runs without API keys.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INVOICE_DIR = BASE_DIR / "invoices"
DEFAULT_DB = BASE_DIR / "finance.db"


@dataclass
class AgentEvent:
    time: str
    kind: str
    message: str
    data: dict[str, Any] | None = None


class FinanceStore:
    """A simulated internal finance application backed by SQLite."""

    def __init__(self, db_path: Path = DEFAULT_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT NOT NULL,
                invoice_number TEXT NOT NULL UNIQUE,
                company TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                due_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT NOT NULL
            )""")

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=3)

    def log(self, action: str, detail: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute("INSERT INTO audit_log(created_at, action, detail) VALUES(?,?,?)",
                         (datetime.now().isoformat(timespec="seconds"), action, json.dumps(detail)))

    def create_invoice(self, record: dict[str, Any]) -> dict[str, Any]:
        """Idempotent create: duplicate invoice numbers return the existing row."""
        with self.connect() as conn:
            existing = conn.execute("SELECT * FROM invoices WHERE invoice_number=?",
                                    (record["invoice_number"],)).fetchone()
            if existing:
                names = [d[0] for d in conn.execute("SELECT * FROM invoices LIMIT 0").description]
                result = dict(zip(names, existing))
                self.log("duplicate_prevented", {"invoice_number": record["invoice_number"]})
                return {"status": "already_exists", "record": result}
            cur = conn.execute("""INSERT INTO invoices
                (source_file, invoice_number, company, amount, currency, due_date, created_at)
                VALUES(?,?,?,?,?,?,?)""",
                (record["source_file"], record["invoice_number"], record["company"],
                 record["amount"], record["currency"], record["due_date"],
                 datetime.now().isoformat(timespec="seconds")))
            row = conn.execute("SELECT * FROM invoices WHERE id=?", (cur.lastrowid,)).fetchone()
            names = [d[0] for d in conn.execute("SELECT * FROM invoices LIMIT 0").description]
            result = dict(zip(names, row))
        self.log("invoice_created", result)
        return {"status": "created", "record": result}

    def get_by_number(self, invoice_number: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            cur = conn.execute("SELECT * FROM invoices WHERE invoice_number=?", (invoice_number,))
            row = cur.fetchone()
            if not row:
                return None
            return dict(zip([d[0] for d in cur.description], row))

    def list_invoices(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            cur = conn.execute("SELECT * FROM invoices ORDER BY id DESC")
            return [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]


class InvoiceTools:
    def __init__(self, invoice_dir: Path, store: FinanceStore):
        self.invoice_dir = Path(invoice_dir)
        self.store = store

    def search_invoices(self, company: str) -> dict[str, Any]:
        """Search supported local .txt invoices; choose newest by invoice date."""
        if not self.invoice_dir.exists():
            return {"ok": False, "error": f"Invoice directory not found: {self.invoice_dir}"}
        matches = []
        for path in self.invoice_dir.glob("*.txt"):
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                continue
            found_company = re.search(r"^Company:\s*(.+)$", content, re.M | re.I)
            invoice_date = re.search(r"^Invoice Date:\s*(\d{4}-\d{2}-\d{2})$", content, re.M | re.I)
            if not found_company or not invoice_date:
                continue
            if company.lower() in found_company.group(1).strip().lower():
                matches.append({"path": str(path), "company": found_company.group(1).strip(),
                                "invoice_date": invoice_date.group(1)})
        matches.sort(key=lambda x: x["invoice_date"], reverse=True)
        if not matches:
            return {"ok": False, "error": f"No supported invoice found for '{company}'.", "retryable": True}
        return {"ok": True, "selected": matches[0], "matches_found": len(matches), "matches": matches}

    def extract_invoice(self, path: str) -> dict[str, Any]:
        """Extract required fields and return validation errors instead of guessing."""
        file_path = Path(path).resolve()
        allowed_dir = self.invoice_dir.resolve()
        if allowed_dir not in file_path.parents or file_path.suffix.lower() != ".txt":
            return {"ok": False, "error": "File is outside the allowed invoice directory or unsupported."}
        try:
            text = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "error": f"Could not read invoice: {exc}"}
        patterns = {
            "invoice_number": r"^Invoice Number:\s*([A-Za-z0-9_-]+)\s*$",
            "company": r"^Company:\s*(.+?)\s*$",
            "amount": r"^Total Due:\s*(?:INR|₹|USD|\$)\s*([0-9,]+(?:\.\d{2})?)\s*$",
            "currency": r"^Total Due:\s*(INR|₹|USD|\$)",
            "due_date": r"^Due Date:\s*(\d{4}-\d{2}-\d{2})\s*$",
        }
        fields: dict[str, Any] = {"source_file": file_path.name}
        missing = []
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.M | re.I)
            if not match:
                missing.append(key)
            else:
                fields[key] = match.group(1).strip()
        if missing:
            return {"ok": False, "error": "Required fields missing or not understood.", "missing": missing}
        try:
            fields["amount"] = float(fields["amount"].replace(",", ""))
            datetime.strptime(fields["due_date"], "%Y-%m-%d")
            datetime.strptime(re.search(r"^Invoice Date:\s*(\d{4}-\d{2}-\d{2})$", text, re.M | re.I).group(1), "%Y-%m-%d")
        except (ValueError, AttributeError):
            return {"ok": False, "error": "Amount or date has an invalid format."}
        fields["currency"] = {"₹": "INR", "$": "USD"}.get(fields["currency"], fields["currency"].upper())
        return {"ok": True, "invoice": fields, "validation": {"required_fields_present": True, "amount_positive": fields["amount"] > 0}}

    def save_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        if invoice.get("amount", 0) <= 0:
            return {"ok": False, "error": "Refusing to save a non-positive invoice amount."}
        result = self.store.create_invoice(invoice)
        return {"ok": True, **result}

    def verify_invoice(self, invoice_number: str, expected: dict[str, Any]) -> dict[str, Any]:
        actual = self.store.get_by_number(invoice_number)
        if actual is None:
            return {"ok": False, "verified": False, "error": "Saved record was not found on read-back."}
        checks = {key: actual.get(key) == expected.get(key)
                  for key in ("invoice_number", "company", "amount", "currency", "due_date", "source_file")}
        return {"ok": all(checks.values()), "verified": all(checks.values()), "checks": checks, "record": actual}


class AutonomousInvoiceWorker:
    """Small observable tool loop: plan -> act -> inspect -> verify -> report."""
    def __init__(self, invoice_dir: Path = DEFAULT_INVOICE_DIR, db_path: Path = DEFAULT_DB,
                 max_steps: int = 8, retry_limit: int = 1):
        self.store = FinanceStore(db_path)
        self.tools = InvoiceTools(invoice_dir, self.store)
        self.max_steps = max_steps
        self.retry_limit = retry_limit
        self.events: list[AgentEvent] = []

    def emit(self, kind: str, message: str, data: dict[str, Any] | None = None) -> None:
        self.events.append(AgentEvent(datetime.now().isoformat(timespec="seconds"), kind, message, data))

    @staticmethod
    def parse_company(task: str) -> str | None:
        patterns = [r"(?:invoice|invoices)\s+(?:from|for)\s+['\"]?(.+?)(?=\s+(?:extract|enter|and|then|into|tell)\b|[,.;]|$)",
                    r"from\s+['\"]?([A-Za-z0-9 &_-]+?)(?:,|\s+extract|\s+and|\s+enter|\s+into|\s+then|$)"]
        for pattern in patterns:
            match = re.search(pattern, task, re.I)
            if match:
                return match.group(1).strip()
        return None

    def identify_company(self, task: str) -> tuple[str | None, str]:
        """Use an optional LLM for intent parsing; deterministic fallback is always available."""
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                client = OpenAI()
                response = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    temperature=0,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": "Extract the company name from an invoice-processing request. Return JSON with keys task_type (invoice_processing or unsupported) and company (string or null). Do not invent a company."},
                        {"role": "user", "content": task},
                    ],
                )
                parsed = json.loads(response.choices[0].message.content or "{}")
                if parsed.get("task_type") == "invoice_processing" and parsed.get("company"):
                    return str(parsed["company"]).strip(), "llm"
                return None, "llm"
            except Exception as exc:
                self.emit("recovery", "LLM intent parsing failed; using deterministic parser.", {"error": str(exc)[:240]})
        return self.parse_company(task), "rules"

    def run(self, task: str) -> dict[str, Any]:
        self.events = []
        self.emit("goal", "Received task", {"task": task})
        company, parser = self.identify_company(task)
        self.emit("understand", "Interpreted the task request", {"company": company, "parser": parser})
        if not company:
            self.emit("human_input", "Could not identify a company name; asking for clarification.")
            return self._result("needs_input", "Please specify the company whose invoice should be processed.")
        plan = [
            {"tool": "search_invoices", "args": {"company": company}, "purpose": "Find the newest matching invoice"},
            {"tool": "extract_invoice", "args_from": "search_result.selected.path", "purpose": "Extract and validate invoice fields"},
            {"tool": "save_invoice", "args_from": "extracted.invoice", "purpose": "Enter validated data into the simulated finance app"},
            {"tool": "verify_invoice", "args_from": "extracted.invoice", "purpose": "Read back the record and compare saved values"},
        ]
        self.emit("plan", "Created an execution plan", {"steps": plan, "company": company})
        context: dict[str, Any] = {}
        steps = 0
        for step in plan:
            if steps >= self.max_steps:
                self.emit("failure", "Maximum step budget reached.")
                return self._result("failed", "Stopped to avoid an unbounded execution loop.")
            steps += 1
            tool_name = step["tool"]
            self.emit("action", f"Executing {tool_name}: {step['purpose']}", step)
            if tool_name == "search_invoices":
                result = self.tools.search_invoices(step["args"]["company"])
                if not result.get("ok") and result.get("retryable"):
                    self.emit("recovery", "Search found no match; retrying once with case-insensitive broad matching.")
                    time.sleep(0.02)
                    result = self.tools.search_invoices(step["args"]["company"].strip())
                context["search_result"] = result
            elif tool_name == "extract_invoice":
                path = context.get("search_result", {}).get("selected", {}).get("path")
                if not path:
                    self.emit("failure", "Cannot extract because search did not return a file.", context.get("search_result"))
                    return self._result("failed", context.get("search_result", {}).get("error", "Invoice search failed."))
                result = self.tools.extract_invoice(path)
                context["extracted"] = result
            elif tool_name == "save_invoice":
                invoice = context.get("extracted", {}).get("invoice")
                if not invoice:
                    self.emit("failure", "Cannot save because extraction did not validate required fields.", context.get("extracted"))
                    return self._result("needs_input", "The invoice could not be safely extracted; please review the source file.")
                if not context["extracted"].get("validation", {}).get("amount_positive"):
                    return self._result("needs_input", "The invoice amount is not positive; human review is required.")
                result = self.tools.save_invoice(invoice)
                context["saved"] = result
            elif tool_name == "verify_invoice":
                invoice = context.get("extracted", {}).get("invoice")
                if not invoice or not context.get("saved", {}).get("ok"):
                    return self._result("failed", "No saved invoice is available to verify.")
                result = self.tools.verify_invoice(invoice["invoice_number"], invoice)
                context["verification"] = result
            else:
                return self._result("failed", f"Unknown tool: {tool_name}")
            self.emit("observation", f"Observed result from {tool_name}", result)
            if not result.get("ok"):
                self.emit("failure", f"Tool {tool_name} failed", result)
                if tool_name == "extract_invoice":
                    return self._result("needs_input", result.get("error", "Invoice extraction failed."), context)
                return self._result("failed", result.get("error", f"{tool_name} failed."), context)
        verification = context.get("verification", {})
        if not verification.get("verified"):
            self.emit("failure", "Verification failed; refusing to claim completion.", verification)
            return self._result("failed", "A record may have been written, but read-back verification failed.", context)
        record = verification["record"]
        status = context["saved"]["status"]
        self.emit("complete", "Invoice saved and independently verified", {"record_id": record["id"], "status": status})
        return self._result("completed", f"Invoice {record['invoice_number']} for {record['company']} was {('already present' if status == 'already_exists' else 'saved')} and verified.", context)

    def _result(self, status: str, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"status": status, "message": message, "context": context or {}, "events": [asdict(e) for e in self.events]}
