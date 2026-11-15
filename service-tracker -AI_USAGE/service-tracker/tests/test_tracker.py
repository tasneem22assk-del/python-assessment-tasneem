"""Automated tests for the Service Request Tracker.

Run with:  python -m unittest discover -s tests -v
Each test uses its own temporary database, so tracker.db is never touched.
"""

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime

from tracker.cli import main
from tracker.db import connect

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TrackerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test.db")

    def tearDown(self):
        self.tmpdir.cleanup()

    def cli(self, *argv):
        """Run a command in-process; return (exit_code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv), db_path=self.db_path)
        return code, out.getvalue().strip(), err.getvalue().strip()

    def add(self, title="Laptop setup", requester="Maya", priority="HIGH"):
        return self.cli("add", "--title", title, "--requester", requester,
                        "--priority", priority)

    def rows(self):
        conn = connect(self.db_path)  # creates the schema if the file is new
        try:
            return [dict(r) for r in conn.execute("SELECT * FROM tickets ORDER BY id")]
        finally:
            conn.close()


class TestAdd(TrackerTestCase):
    def test_add_creates_open_ticket_with_utc_timestamp(self):
        code, out, _ = self.add()
        self.assertEqual(code, 0)
        self.assertEqual(out, "Created ticket #1")
        ticket = self.rows()[0]
        self.assertEqual(ticket["status"], "OPEN")
        self.assertEqual(ticket["priority"], "HIGH")
        self.assertIsNone(ticket["assignee"])
        created = datetime.fromisoformat(ticket["created_at"])
        self.assertEqual(created.utcoffset().total_seconds(), 0)  # stored in UTC

    def test_ids_increase(self):
        self.assertEqual(self.add()[1], "Created ticket #1")
        self.assertEqual(self.add(title="Printer")[1], "Created ticket #2")

    def test_priority_is_case_insensitive(self):
        code, _, _ = self.add(priority="low")
        self.assertEqual(code, 0)
        self.assertEqual(self.rows()[0]["priority"], "LOW")

    def test_invalid_priority_rejected(self):
        code, _, err = self.add(priority="URGENT")
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", err)
        self.assertEqual(self.rows(), [])

    def test_missing_title_rejected(self):
        code, _, _ = self.cli("add", "--requester", "Maya", "--priority", "HIGH")
        self.assertEqual(code, 2)

    def test_blank_title_rejected(self):
        code, _, err = self.add(title="   ")
        self.assertEqual(code, 1)
        self.assertIn("Title must not be empty", err)
        self.assertEqual(self.rows(), [])


class TestList(TrackerTestCase):
    def test_empty_list(self):
        code, out, _ = self.cli("list")
        self.assertEqual(code, 0)
        self.assertEqual(out, "No tickets found")

    def test_list_all_in_id_order_and_filter(self):
        self.add(title="A")
        self.add(title="B")
        self.add(title="C")
        self.cli("assign", "--id", "2", "--user", "AgentA")
        self.cli("update", "--id", "2", "--status", "IN_PROGRESS")

        _, out, _ = self.cli("list")
        lines = out.splitlines()
        self.assertEqual([l.split()[0] for l in lines], ["#1", "#2", "#3"])

        _, out, _ = self.cli("list", "--status", "OPEN")
        self.assertEqual([l.split()[0] for l in out.splitlines()], ["#1", "#3"])

        _, out, _ = self.cli("list", "--status", "RESOLVED")
        self.assertEqual(out, "No tickets found")


class TestAssign(TrackerTestCase):
    def test_assign_sets_user(self):
        self.add()
        code, _, _ = self.cli("assign", "--id", "1", "--user", "AgentA")
        self.assertEqual(code, 0)
        self.assertEqual(self.rows()[0]["assignee"], "AgentA")

    def test_empty_assignee_rejected(self):
        self.add()
        code, _, err = self.cli("assign", "--id", "1", "--user", "  ")
        self.assertEqual(code, 1)
        self.assertIn("Assignee must not be empty", err)
        self.assertIsNone(self.rows()[0]["assignee"])

    def test_nonexistent_ticket_rejected(self):
        code, _, err = self.cli("assign", "--id", "99", "--user", "AgentA")
        self.assertEqual(code, 1)
        self.assertIn("Ticket #99 not found", err)


class TestUpdate(TrackerTestCase):
    def test_in_progress_requires_assignee(self):
        self.add()
        code, _, err = self.cli("update", "--id", "1", "--status", "IN_PROGRESS")
        self.assertEqual(code, 1)
        self.assertIn("must be assigned", err)
        self.assertEqual(self.rows()[0]["status"], "OPEN")

    def test_full_cycle(self):
        self.add()
        self.cli("assign", "--id", "1", "--user", "AgentA")
        for status in ("IN_PROGRESS", "RESOLVED", "OPEN"):
            code, _, _ = self.cli("update", "--id", "1", "--status", status)
            self.assertEqual(code, 0, status)
            self.assertEqual(self.rows()[0]["status"], status)

    def test_unsupported_transitions_rejected(self):
        self.add()
        self.cli("assign", "--id", "1", "--user", "AgentA")
        bad_moves = [
            ("OPEN", "RESOLVED"),
            ("OPEN", "OPEN"),
        ]
        for _, target in bad_moves:
            code, _, err = self.cli("update", "--id", "1", "--status", target)
            self.assertEqual(code, 1)
            self.assertIn("Unsupported transition", err)
        self.cli("update", "--id", "1", "--status", "IN_PROGRESS")
        code, _, _ = self.cli("update", "--id", "1", "--status", "OPEN")
        self.assertEqual(code, 1)
        self.assertEqual(self.rows()[0]["status"], "IN_PROGRESS")

    def test_invalid_arguments_do_not_crash(self):
        self.add()
        cases = [
            ("update", "--id", "abc", "--status", "OPEN"),
            ("update", "--id", "-1", "--status", "OPEN"),
            ("update", "--id", "1", "--status", "DONE"),
            ("update", "--id", "1"),
            ("delete", "--id", "1"),
            (),
        ]
        for argv in cases:
            code, _, _ = self.cli(*argv)
            self.assertEqual(code, 2, argv)
        self.assertEqual(self.rows()[0]["status"], "OPEN")  # nothing corrupted


class TestSummary(TrackerTestCase):
    def test_summary_includes_zeroes_in_order(self):
        _, out, _ = self.cli("summary")
        self.assertEqual(out, "OPEN: 0\nIN_PROGRESS: 0\nRESOLVED: 0")

    def test_example_from_assignment(self):
        self.assertEqual(self.add()[1], "Created ticket #1")
        self.cli("assign", "--id", "1", "--user", "AgentA")
        self.cli("update", "--id", "1", "--status", "IN_PROGRESS")
        _, out, _ = self.cli("summary")
        self.assertEqual(out, "OPEN: 0\nIN_PROGRESS: 1\nRESOLVED: 0")


class TestPersistence(TrackerTestCase):
    def test_data_survives_between_separate_processes(self):
        """Runs the real 'python -m tracker' twice to prove data is saved on disk."""
        env = dict(os.environ, TRACKER_DB=self.db_path)
        run = lambda *a: subprocess.run(
            [sys.executable, "-m", "tracker", *a], cwd=PROJECT_ROOT, env=env,
            capture_output=True, text=True,
        )
        first = run("add", "--title", "VPN access", "--requester", "Ali",
                    "--priority", "MEDIUM")
        self.assertEqual(first.stdout.strip(), "Created ticket #1")
        second = run("list")
        self.assertIn("VPN access", second.stdout)
        self.assertEqual(second.returncode, 0)


if __name__ == "__main__":
    unittest.main()
