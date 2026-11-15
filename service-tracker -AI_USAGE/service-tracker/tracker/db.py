"""Database layer: schema, connection and all ticket operations.

All business rules (valid priorities, allowed status transitions,
assignee requirement) live here so they are enforced in one place
and can be tested without going through the command line.
"""

import os
import sqlite3
from datetime import datetime, timezone

DEFAULT_DB_PATH = "tracker.db"

PRIORITIES = ("LOW", "MEDIUM", "HIGH")
STATUSES = ("OPEN", "IN_PROGRESS", "RESOLVED")

# The only allowed moves: OPEN -> IN_PROGRESS -> RESOLVED -> OPEN
ALLOWED_TRANSITIONS = {
    "OPEN": "IN_PROGRESS",
    "IN_PROGRESS": "RESOLVED",
    "RESOLVED": "OPEN",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    requester   TEXT    NOT NULL CHECK (length(trim(requester)) > 0),
    priority    TEXT    NOT NULL CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH')),
    status      TEXT    NOT NULL DEFAULT 'OPEN'
                        CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')),
    assignee    TEXT    CHECK (assignee IS NULL OR length(trim(assignee)) > 0),
    created_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
"""


class TrackerError(Exception):
    """A user-facing error (bad input or forbidden operation)."""


def get_db_path():
    """Database file location. TRACKER_DB env var overrides the default."""
    return os.environ.get("TRACKER_DB", DEFAULT_DB_PATH)


def connect(db_path=None):
    """Open the database and make sure the schema exists."""
    conn = sqlite3.connect(db_path or get_db_path())
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def utc_now_iso():
    """Current UTC time in ISO 8601, e.g. 2026-11-15T04:40:00+00:00"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(value, field):
    """Strip a text value and reject it if it is missing or blank."""
    if value is None or not value.strip():
        raise TrackerError(f"{field} must not be empty.")
    return value.strip()


def _get_ticket(conn, ticket_id):
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise TrackerError(f"Ticket #{ticket_id} not found.")
    return row


def add_ticket(conn, title, requester, priority):
    title = _clean(title, "Title")
    requester = _clean(requester, "Requester")
    priority = (priority or "").strip().upper()
    if priority not in PRIORITIES:
        raise TrackerError(
            f"Invalid priority '{priority}'. Choose one of: {', '.join(PRIORITIES)}."
        )
    with conn:  # transaction: commits on success, rolls back on error
        cur = conn.execute(
            "INSERT INTO tickets (title, requester, priority, status, created_at) "
            "VALUES (?, ?, ?, 'OPEN', ?)",
            (title, requester, priority, utc_now_iso()),
        )
    return cur.lastrowid


def list_tickets(conn, status=None):
    if status is None:
        return conn.execute("SELECT * FROM tickets ORDER BY id ASC").fetchall()
    status = status.strip().upper()
    if status not in STATUSES:
        raise TrackerError(
            f"Invalid status '{status}'. Choose one of: {', '.join(STATUSES)}."
        )
    return conn.execute(
        "SELECT * FROM tickets WHERE status = ? ORDER BY id ASC", (status,)
    ).fetchall()


def assign_ticket(conn, ticket_id, user):
    user = _clean(user, "Assignee")
    _get_ticket(conn, ticket_id)
    with conn:
        conn.execute("UPDATE tickets SET assignee = ? WHERE id = ?", (user, ticket_id))


def update_status(conn, ticket_id, new_status):
    new_status = (new_status or "").strip().upper()
    if new_status not in STATUSES:
        raise TrackerError(
            f"Invalid status '{new_status}'. Choose one of: {', '.join(STATUSES)}."
        )
    ticket = _get_ticket(conn, ticket_id)
    current = ticket["status"]

    if ALLOWED_TRANSITIONS[current] != new_status:
        raise TrackerError(
            f"Unsupported transition {current} -> {new_status}. "
            f"From {current} the only allowed status is {ALLOWED_TRANSITIONS[current]}."
        )
    if current == "OPEN" and not ticket["assignee"]:
        raise TrackerError(
            f"Ticket #{ticket_id} must be assigned before moving to IN_PROGRESS. "
            f"Use: python -m tracker assign --id {ticket_id} --user <name>"
        )

    with conn:
        # "AND status = ?" guards against a concurrent change between read and write
        cur = conn.execute(
            "UPDATE tickets SET status = ? WHERE id = ? AND status = ?",
            (new_status, ticket_id, current),
        )
    if cur.rowcount != 1:
        raise TrackerError(f"Ticket #{ticket_id} changed while updating; try again.")


def summary(conn):
    """Counts per status, always including all three statuses (zeroes too)."""
    counts = {status: 0 for status in STATUSES}
    for row in conn.execute("SELECT status, COUNT(*) AS n FROM tickets GROUP BY status"):
        counts[row["status"]] = row["n"]
    return counts
