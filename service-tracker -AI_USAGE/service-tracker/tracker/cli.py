"""Command-line interface: parses arguments and prints results.

Exit codes:
    0  success
    1  rejected operation (bad value, missing ticket, forbidden transition)
    2  invalid command-line arguments (reported by argparse)
"""

import argparse
import sqlite3
import sys

from tracker import db


def positive_int(text):
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not a valid ticket id.")
    if value <= 0:
        raise argparse.ArgumentTypeError("Ticket id must be a positive integer.")
    return value


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python -m tracker",
        description="Service Request Tracker - create and follow support tickets.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    p_add = sub.add_parser("add", help="Create a new ticket (status OPEN).")
    p_add.add_argument("--title", required=True, help="Short description of the request.")
    p_add.add_argument("--requester", required=True, help="Who asked for it.")
    p_add.add_argument(
        "--priority", required=True, type=str.upper, choices=db.PRIORITIES,
        help="LOW, MEDIUM or HIGH (case-insensitive).",
    )

    p_list = sub.add_parser("list", help="List tickets in increasing id order.")
    p_list.add_argument(
        "--status", type=str.upper, choices=db.STATUSES, help="Only show this status."
    )

    p_update = sub.add_parser("update", help="Change a ticket's status.")
    p_update.add_argument("--id", required=True, type=positive_int, dest="ticket_id")
    p_update.add_argument(
        "--status", required=True, type=str.upper, choices=db.STATUSES,
        help="Allowed cycle: OPEN -> IN_PROGRESS -> RESOLVED -> OPEN.",
    )

    p_assign = sub.add_parser("assign", help="Set the ticket's assignee.")
    p_assign.add_argument("--id", required=True, type=positive_int, dest="ticket_id")
    p_assign.add_argument("--user", required=True, help="Non-empty assignee name.")

    sub.add_parser("summary", help="Count tickets per status.")
    return parser


def format_ticket(t):
    assignee = t["assignee"] or "-"
    return (
        f"#{t['id']} [{t['status']}] {t['priority']} | {t['title']} | "
        f"requester: {t['requester']} | assignee: {assignee} | created: {t['created_at']}"
    )


def run(args, conn):
    if args.command == "add":
        ticket_id = db.add_ticket(conn, args.title, args.requester, args.priority)
        print(f"Created ticket #{ticket_id}")

    elif args.command == "list":
        tickets = db.list_tickets(conn, args.status)
        if not tickets:
            print("No tickets found")
        for t in tickets:
            print(format_ticket(t))

    elif args.command == "assign":
        db.assign_ticket(conn, args.ticket_id, args.user)
        print(f"Assigned ticket #{args.ticket_id} to {args.user.strip()}")

    elif args.command == "update":
        db.update_status(conn, args.ticket_id, args.status)
        print(f"Updated ticket #{args.ticket_id} to {args.status}")

    elif args.command == "summary":
        for status, count in db.summary(conn).items():
            print(f"{status}: {count}")


def main(argv=None, db_path=None):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse already printed the usage/error message
        return exc.code if isinstance(exc.code, int) else 2

    try:
        conn = db.connect(db_path)
    except sqlite3.Error as exc:
        print(f"Error: cannot open database: {exc}", file=sys.stderr)
        return 1

    try:
        run(args, conn)
        return 0
    except db.TrackerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"Error: database problem: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
