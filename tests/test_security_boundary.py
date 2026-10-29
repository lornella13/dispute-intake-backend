"""Security boundary tests for the Dispute Intake Module.

All tests use an isolated temporary SQLite database so the real
development database (disputes.db) is never modified.
"""

import os
import sys
import tempfile

# Add backend root to path so we can import and patch database.py
# before the FastAPI app (which calls init_db()) is loaded.
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

import database  # noqa: E402

# Isolate the test database in a temp file BEFORE importing the app,
# so init_db() and all test writes go to the temp file, never to disputes.db.
_real_db_path = os.path.join(backend_root, "disputes.db")
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
database.DB_FILE = _tmp_db.name
_tmp_db.close()

# Defensive guard: refuse to run if we are about to touch the real database.
assert database.DB_FILE != _real_db_path, (
    f"Test database is pointing at the real DB: {database.DB_FILE}"
)

# Ensure tables exist in the temporary database (init_db is idempotent).
# Called explicitly because src.main may already be imported from another
# test module, in which case its import-time init_db() would not re-run.
database.init_db()

from fastapi.testclient import TestClient  # noqa: E402
from src.main import app  # noqa: E402

client = TestClient(app)


def _auth_headers(username: str, password: str) -> dict:
    """Log in and return Authorization headers for a given operator."""
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.status_code}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_signature_cross_bank_isolation_boundary():
    """Greenbank creates a complaint; Bluemobile attempts to read it → 404."""
    # Defensive check: ensure we are still isolated from the real DB.
    assert database.DB_FILE != _real_db_path

    # 1. Greenbank operator files a complaint containing a private note
    green_headers = _auth_headers("aline_green", "green123")
    payload = {
        "transfer_reference": "TXN-881222",
        "amount": "15000",
        "currency": "RWF",
        "category": "debited_not_credited",
        "description": "CRITICAL PRIVATE NOTE: Suspected internal failure.",
    }

    create_res = client.post("/complaints", json=payload, headers=green_headers)
    assert create_res.status_code == 200
    complaint_id = create_res.json()["complaint_id"]

    # 2. Bluemobile operator attempts to read Greenbank's private record
    blue_headers = _auth_headers("brian_blue", "blue123")
    attack_res = client.get(f"/complaints/{complaint_id}", headers=blue_headers)

    # 3. Assert strict multi-tenant 404 security compliance
    assert attack_res.status_code == 404


def test_cross_bank_isolation_reverse_direction():
    """Bluemobile creates a complaint; Greenbank attempts to read it → 404."""
    # Defensive check: ensure we are still isolated from the real DB.
    assert database.DB_FILE != _real_db_path

    # 1. Bluemobile operator files a complaint containing a private note
    blue_headers = _auth_headers("brian_blue", "blue123")
    payload = {
        "transfer_reference": "TXN-100001",
        "amount": "5000",
        "currency": "RWF",
        "category": "duplicate",
        "description": "Bluemobile private intake note.",
    }

    create_res = client.post("/complaints", json=payload, headers=blue_headers)
    assert create_res.status_code == 200
    complaint_id = create_res.json()["complaint_id"]

    # 2. Greenbank operator attempts to read Bluemobile's private record
    green_headers = _auth_headers("aline_green", "green123")
    attack_res = client.get(f"/complaints/{complaint_id}", headers=green_headers)

    # 3. Assert strict multi-tenant 404 security compliance
    assert attack_res.status_code == 404
    body = attack_res.json()
    assert "complaint_id" not in body
    assert "transfer_reference" not in body
    assert "description" not in body
