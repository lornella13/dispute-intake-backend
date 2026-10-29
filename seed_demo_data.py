"""Synthetic seed data script for the Dispute Intake Module.

Creates clearly fake complaint and audit_log records for both Greenbank and
Bluemobile. This is for demonstration/testing purposes only.

IMPORTANT:
- Requires an explicit target database path via --db or DISPUTE_DB_PATH env var.
- NEVER clears or overwrites existing records. Uses INSERT OR IGNORE so
  re-running is safe and idempotent.
- Does NOT touch the real development database unless explicitly pointed at it.
"""

import argparse
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Synthetic demo data (clearly fake — not real customer data)
# ---------------------------------------------------------------------------

SYNTHETIC_COMPLAINTS = [
    # Greenbank complaints
    {
        "id": "CMP-SEED001",
        "bank": "Greenbank",
        "operator_username": "aline_green",
        "transfer_reference": "TXN-100001",
        "amount": "15000.00",
        "currency": "RWF",
        "category": "debited_not_credited",
        "description": "Synthetic demo: customer reports funds debited but not credited to recipient account.",
        "evidence": "statement_jan.pdf",
        "registration_status": "REGISTERED",
        "hub_claim_id": "CLM-A1B2C3D4",
        "hub_error_message": None,
        "created_at": "2026-01-15T09:30:00+00:00",
    },
    {
        "id": "CMP-SEED002",
        "bank": "Greenbank",
        "operator_username": "aline_green",
        "transfer_reference": "TXN-100002",
        "amount": "25000.50",
        "currency": "RWF",
        "category": "wrong_recipient",
        "description": "Synthetic demo: payment sent to wrong account number. Customer statement attached.",
        "evidence": "customer_statement_feb.pdf",
        "registration_status": "REGISTERED",
        "hub_claim_id": "CLM-E5F6G7H8",
        "hub_error_message": None,
        "created_at": "2026-02-03T14:15:00+00:00",
    },
    {
        "id": "CMP-SEED003",
        "bank": "Greenbank",
        "operator_username": "aline_green",
        "transfer_reference": "TXN-100999",
        "amount": "5000.00",
        "currency": "RWF",
        "category": "duplicate",
        "description": "Synthetic demo: duplicate transfer reference detected. Hub rejected this registration.",
        "evidence": None,
        "registration_status": "REJECTED",
        "hub_claim_id": None,
        "hub_error_message": "Scheme violation: Exceeded bounds.",
        "created_at": "2026-02-10T11:00:00+00:00",
    },
    # Bluemobile complaints
    {
        "id": "CMP-SEED004",
        "bank": "Bluemobile",
        "operator_username": "brian_blue",
        "transfer_reference": "TXN-200001",
        "amount": "12000.00",
        "currency": "RWF",
        "category": "scam",
        "description": "Synthetic demo: customer reports suspected scam transaction. Police report attached.",
        "evidence": "police_report_mar.pdf",
        "registration_status": "REGISTERED",
        "hub_claim_id": "CLM-I9J0K1L2",
        "hub_error_message": None,
        "created_at": "2026-03-12T10:45:00+00:00",
    },
    {
        "id": "CMP-SEED005",
        "bank": "Bluemobile",
        "operator_username": "brian_blue",
        "transfer_reference": "TXN-200002",
        "amount": "8000.75",
        "currency": "RWF",
        "category": "duplicate",
        "description": "Synthetic demo: duplicate entry for same transaction. No evidence required.",
        "evidence": None,
        "registration_status": "REGISTERED",
        "hub_claim_id": "CLM-M3N4O5P6",
        "hub_error_message": None,
        "created_at": "2026-03-20T16:20:00+00:00",
    },
    {
        "id": "CMP-SEED006",
        "bank": "Bluemobile",
        "operator_username": "brian_blue",
        "transfer_reference": "TXN-200999",
        "amount": "3000.00",
        "currency": "RWF",
        "category": "debited_not_credited",
        "description": "Synthetic demo: funds debited but not credited. Hub rejected due to reference ending in 999.",
        "evidence": None,
        "registration_status": "REJECTED",
        "hub_claim_id": None,
        "hub_error_message": "Scheme violation: Exceeded bounds.",
        "created_at": "2026-04-02T08:10:00+00:00",
    },
]

SYNTHETIC_AUDIT_LOGS = [
    {
        "id": "AUD-SEED001",
        "request_id": "REQ-SEED001",
        "operator_username": "aline_green",
        "bank": "Greenbank",
        "action": "CREATE_COMPLAINT",
        "target_id": "CMP-SEED001",
        "timestamp": "2026-01-15T09:30:00+00:00",
    },
    {
        "id": "AUD-SEED002",
        "request_id": "REQ-SEED002",
        "operator_username": "aline_green",
        "bank": "Greenbank",
        "action": "CREATE_COMPLAINT",
        "target_id": "CMP-SEED002",
        "timestamp": "2026-02-03T14:15:00+00:00",
    },
    {
        "id": "AUD-SEED003",
        "request_id": "REQ-SEED003",
        "operator_username": "aline_green",
        "bank": "Greenbank",
        "action": "CREATE_COMPLAINT",
        "target_id": "CMP-SEED003",
        "timestamp": "2026-02-10T11:00:00+00:00",
    },
    {
        "id": "AUD-SEED004",
        "request_id": "REQ-SEED004",
        "operator_username": "brian_blue",
        "bank": "Bluemobile",
        "action": "CREATE_COMPLAINT",
        "target_id": "CMP-SEED004",
        "timestamp": "2026-03-12T10:45:00+00:00",
    },
    {
        "id": "AUD-SEED005",
        "request_id": "REQ-SEED005",
        "operator_username": "brian_blue",
        "bank": "Bluemobile",
        "action": "CREATE_COMPLAINT",
        "target_id": "CMP-SEED005",
        "timestamp": "2026-03-20T16:20:00+00:00",
    },
    {
        "id": "AUD-SEED006",
        "request_id": "REQ-SEED006",
        "operator_username": "brian_blue",
        "bank": "Bluemobile",
        "action": "CREATE_COMPLAINT",
        "target_id": "CMP-SEED006",
        "timestamp": "2026-04-02T08:10:00+00:00",
    },
]


def resolve_db_path(args: argparse.Namespace) -> str:
    """Determine the target database path.

    Priority: --db argument > DISPUTE_DB_PATH env var > error.
    Never defaults to the real development database.
    """
    if args.db:
        return args.db
    env_path = os.getenv("DISPUTE_DB_PATH")
    if env_path:
        return env_path
    raise SystemExit(
        "Error: No target database specified. "
        "Pass --db <path> or set DISPUTE_DB_PATH environment variable. "
        "This script will not default to the real development database."
    )


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist (idempotent)."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id TEXT PRIMARY KEY,
            bank TEXT NOT NULL,
            operator_username TEXT NOT NULL,
            transfer_reference TEXT NOT NULL,
            amount TEXT NOT NULL,
            currency TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            evidence TEXT,
            registration_status TEXT NOT NULL,
            hub_claim_id TEXT,
            hub_error_message TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            operator_username TEXT NOT NULL,
            bank TEXT NOT NULL,
            action TEXT NOT NULL,
            target_id TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()


def seed(db_path: str, dry_run: bool = False) -> None:
    """Insert synthetic records into the target database.

    Uses INSERT OR IGNORE so re-running is safe — existing rows are never
    overwritten or deleted.
    """
    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        cur = conn.cursor()

        complaints_inserted = 0
        for c in SYNTHETIC_COMPLAINTS:
            if dry_run:
                print(f"[DRY RUN] Would insert complaint {c['id']} ({c['bank']})")
                continue
            cur.execute(
                """INSERT OR IGNORE INTO complaints
                   (id, bank, operator_username, transfer_reference, amount,
                    currency, category, description, evidence,
                    registration_status, hub_claim_id, hub_error_message, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    c["id"], c["bank"], c["operator_username"],
                    c["transfer_reference"], c["amount"], c["currency"],
                    c["category"], c["description"], c["evidence"],
                    c["registration_status"], c["hub_claim_id"],
                    c["hub_error_message"], c["created_at"],
                ),
            )
            if cur.rowcount > 0:
                complaints_inserted += 1

        audit_inserted = 0
        for a in SYNTHETIC_AUDIT_LOGS:
            if dry_run:
                print(f"[DRY RUN] Would insert audit log {a['id']} ({a['action']})")
                continue
            cur.execute(
                """INSERT OR IGNORE INTO audit_logs
                   (id, request_id, operator_username, bank, action, target_id, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    a["id"], a["request_id"], a["operator_username"],
                    a["bank"], a["action"], a["target_id"], a["timestamp"],
                ),
            )
            if cur.rowcount > 0:
                audit_inserted += 1

        if not dry_run:
            conn.commit()
            print(f"Seeded {complaints_inserted} new complaints and "
                  f"{audit_inserted} new audit log records into {db_path}")
        else:
            print(f"[DRY RUN] Would seed {len(SYNTHETIC_COMPLAINTS)} complaints "
                  f"and {len(SYNTHETIC_AUDIT_LOGS)} audit log records")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed synthetic demo data into the Dispute Intake SQLite database."
    )
    parser.add_argument(
        "--db",
        help="Path to target SQLite database file. "
             "Alternatively set DISPUTE_DB_PATH environment variable.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be inserted without writing to the database.",
    )
    args = parser.parse_args()

    db_path = resolve_db_path(args)
    print(f"Target database: {db_path}")
    if args.dry_run:
        print("Mode: DRY RUN (no writes)")
    seed(db_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
