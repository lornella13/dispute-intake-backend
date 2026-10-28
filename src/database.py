import sqlite3

DB_FILE = "disputes.db"

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
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
    cursor.execute("""
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
    conn.close()
