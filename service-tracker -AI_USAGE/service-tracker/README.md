# Service Request Tracker CLI

A small, persistent command-line tracker for IT service requests (tickets).
Built only with the Python standard library: `argparse` for the CLI and
`sqlite3` for storage. No frontend, network service or ORM.

## Setup

Requirements: **Python 3.8+**. Nothing to install.

```bash
git clone <your-repo-url>
cd service-tracker
python -m tracker --help
```

Run every command from the project root (the folder that contains `tracker/`).
The database file `tracker.db` is created automatically on first use and is
listed in `.gitignore`.

Optional: set `TRACKER_DB` to use a different database file:

```bash
TRACKER_DB=/tmp/demo.db python -m tracker summary
```

## Commands

| Command | Description |
|---|---|
| `add --title T --requester R --priority LOW\|MEDIUM\|HIGH` | Create a ticket with status `OPEN`. Prints `Created ticket #<id>`. |
| `list [--status OPEN\|IN_PROGRESS\|RESOLVED]` | List tickets in increasing id order. Prints `No tickets found` if none match. |
| `assign --id N --user NAME` | Set a non-empty assignee. |
| `update --id N --status S` | Move to the next status in the cycle (see below). |
| `summary` | Print counts for `OPEN`, `IN_PROGRESS`, `RESOLVED` (zeroes included). |

Use `python -m tracker <command> --help` for details on any command.

### Status cycle

```
OPEN ──► IN_PROGRESS ──► RESOLVED ──► OPEN
```

Only these moves are allowed. Moving `OPEN → IN_PROGRESS` requires the
ticket to have an assignee.

## Example command sequence

```bash
$ python -m tracker add --title "Laptop setup" --requester "Maya" --priority HIGH
Created ticket #1

$ python -m tracker add --title "VPN access" --requester "Ali" --priority medium
Created ticket #2

$ python -m tracker update --id 1 --status IN_PROGRESS
Error: Ticket #1 must be assigned before moving to IN_PROGRESS. Use: python -m tracker assign --id 1 --user <name>

$ python -m tracker assign --id 1 --user AgentA
Assigned ticket #1 to AgentA

$ python -m tracker update --id 1 --status IN_PROGRESS
Updated ticket #1 to IN_PROGRESS

$ python -m tracker list
#1 [IN_PROGRESS] HIGH | Laptop setup | requester: Maya | assignee: AgentA | created: 2026-11-15T04:43:16+00:00
#2 [OPEN] MEDIUM | VPN access | requester: Ali | assignee: - | created: 2026-11-15T04:43:20+00:00

$ python -m tracker list --status RESOLVED
No tickets found

$ python -m tracker update --id 1 --status OPEN
Error: Unsupported transition IN_PROGRESS -> OPEN. From IN_PROGRESS the only allowed status is RESOLVED.

$ python -m tracker summary
OPEN: 1
IN_PROGRESS: 1
RESOLVED: 0
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Operation rejected (blank value, ticket not found, unsupported transition, database error) |
| 2 | Invalid command-line arguments (unknown command, missing option, bad priority/status/id) |

Errors are printed to **stderr**; the program never shows a Python traceback.

## Database schema

File: `tracker.db` (SQLite). Single table:

```sql
CREATE TABLE tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    requester   TEXT    NOT NULL CHECK (length(trim(requester)) > 0),
    priority    TEXT    NOT NULL CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH')),
    status      TEXT    NOT NULL DEFAULT 'OPEN'
                        CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')),
    assignee    TEXT    CHECK (assignee IS NULL OR length(trim(assignee)) > 0),
    created_at  TEXT    NOT NULL   -- UTC ISO 8601, e.g. 2026-11-15T04:43:16+00:00
);
CREATE INDEX idx_tickets_status ON tickets(status);
```

Design notes:
- Validation happens in Python **and** in `CHECK` constraints, so bad data
  cannot get into the table even if the code has a bug.
- `AUTOINCREMENT` means ids are never reused.
- Every write runs inside a transaction (`with conn:`), so a failed command
  leaves existing records untouched.
- The status update uses `WHERE id = ? AND status = ?` so it only applies
  if the ticket is still in the status that was checked.

## Project structure

```
service-tracker/
├── tracker/
│   ├── __init__.py
│   ├── __main__.py   # entry point for "python -m tracker"
│   ├── cli.py        # argparse parser, output formatting, exit codes
│   └── db.py         # schema + business rules (priorities, transitions)
├── tests/
│   └── test_tracker.py
├── .gitignore
└── README.md
```

## Running the tests

```bash
python -m unittest discover -s tests -t . -v
```

(`pytest` also works if installed.) 18 tests cover: creating tickets, UTC
timestamps, priority validation, blank/missing title, listing and filtering,
empty list, assigning, nonexistent tickets, the full status cycle,
unsupported transitions, the assignee requirement, invalid arguments,
summary with zeroes, the exact example from the assignment, and persistence
across two separate `python -m tracker` processes. Tests use a temporary
database and never touch `tracker.db`.

## Assumptions

- Allowed priorities are `LOW`, `MEDIUM`, `HIGH`. Priority and status values
  are case-insensitive on input (`high` → `HIGH`) and stored in upper case.
- Leading/trailing spaces are trimmed from title, requester and assignee;
  a value that is empty after trimming is rejected.
- A ticket can be (re)assigned in any status; assigning again replaces the
  previous assignee.
- The assignee is kept when a ticket goes `RESOLVED → OPEN`, so a reopened
  ticket can go straight back to `IN_PROGRESS`.
- Setting a ticket to the status it already has (e.g. `OPEN → OPEN`) counts as
  an unsupported transition.
- `created_at` is stored with second precision and an explicit `+00:00` offset.
- The database is created in the current working directory unless `TRACKER_DB` is set.

## Known limitations

- No command to delete or edit a ticket's title, requester or priority.
- No un-assign command (an assignee can be replaced but not cleared).
- No history/audit log of status changes or who made them.
- Designed for a single local user; there is no authentication and no
  multi-user locking beyond what SQLite provides.
- `list` prints all matching rows with no paging, sorting options or search.
- `created_at` has second precision only; there is no `updated_at` column.
