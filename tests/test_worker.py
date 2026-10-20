import tempfile
import unittest
from pathlib import Path
from worker import AutonomousInvoiceWorker

SAMPLE = """Invoice Number: TEST-001
Company: Acme Corp
Invoice Date: 2026-10-03
Due Date: 2026-11-02
Total Due: INR 22,750.00
"""

class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.invoices = self.root / "invoices"
        self.invoices.mkdir()
        (self.invoices / "invoice.txt").write_text(SAMPLE, encoding="utf-8")
        self.db = self.root / "finance.db"

    def tearDown(self):
        self.temp.cleanup()

    def test_processes_and_verifies_invoice(self):
        worker = AutonomousInvoiceWorker(self.invoices, self.db)
        result = worker.run("Find the latest invoice from Acme Corp and enter it into the internal system")
        self.assertEqual(result["status"], "completed", result["message"])
        self.assertTrue(result["context"]["verification"]["verified"])
        self.assertEqual(result["context"]["verification"]["record"]["amount"], 22750.0)

    def test_missing_company_requests_input(self):
        worker = AutonomousInvoiceWorker(self.invoices, self.db)
        result = worker.run("Please process the latest invoice")
        self.assertEqual(result["status"], "needs_input")

    def test_unknown_company_fails_safely(self):
        worker = AutonomousInvoiceWorker(self.invoices, self.db)
        result = worker.run("Find invoice from Unknown Ltd and enter it")
        self.assertEqual(result["status"], "failed")

    def test_repeat_is_idempotent(self):
        worker = AutonomousInvoiceWorker(self.invoices, self.db)
        first = worker.run("Find invoice from Acme Corp and enter it")
        second = worker.run("Find invoice from Acme Corp and enter it")
        self.assertEqual(first["status"], "completed")
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second["context"]["saved"]["status"], "already_exists")
        self.assertEqual(len(worker.store.list_invoices()), 1)

if __name__ == "__main__":
    unittest.main()
