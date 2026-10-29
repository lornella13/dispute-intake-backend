"""Regression tests for the Dispute Intake Module backend.

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

# Isolate the test database in a temp file before importing the app.
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
database.DB_FILE = _tmp_db.name
_tmp_db.close()

from fastapi.testclient import TestClient  # noqa: E402
from src.main import app  # noqa: E402

client = TestClient(app)


def _login(username: str, password: str) -> str:
    """Log in and return the access token."""
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.status_code}"
    return resp.json()["access_token"]


def _auth_headers(username: str, password: str) -> dict:
    """Return Authorization headers for a given operator."""
    token = _login(username, password)
    return {"Authorization": f"Bearer {token}"}


# --- Task 2: Reverse-direction bank isolation ---

def test_cross_bank_isolation_bluemobile_to_greenbank():
    """Bluemobile operator cannot read a Greenbank private complaint."""
    blue_headers = _auth_headers("brian_blue", "blue123")

    # Bluemobile creates a complaint
    create_res = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100001",
            "amount": "5000",
            "currency": "RWF",
            "category": "debited_not_credited",
            "description": "Bluemobile private intake note",
        },
        headers=blue_headers,
    )
    assert create_res.status_code == 200
    complaint_id = create_res.json()["complaint_id"]

    # Greenbank attempts to read Bluemobile's complaint
    green_headers = _auth_headers("aline_green", "green123")
    read_res = client.get(f"/complaints/{complaint_id}", headers=green_headers)

    assert read_res.status_code == 404
    body = read_res.json()
    assert "complaint_id" not in body
    assert "transfer_reference" not in body
    assert "description" not in body


# --- Task 3: Login regression tests ---

def test_login_greenbank_valid():
    resp = client.post("/auth/login", json={"username": "aline_green", "password": "green123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]  # non-empty signed token
    assert data["token_type"] == "bearer"
    assert data["bank"] == "Greenbank"


def test_login_bluemobile_valid():
    resp = client.post("/auth/login", json={"username": "brian_blue", "password": "blue123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]  # non-empty signed token
    assert data["token_type"] == "bearer"
    assert data["bank"] == "Bluemobile"


def test_login_invalid_credentials():
    resp = client.post("/auth/login", json={"username": "unknown_user", "password": "wrong_password"})
    assert resp.status_code == 401


def test_protected_endpoint_without_authentication():
    resp = client.get("/complaints")
    assert resp.status_code == 401


# --- Task 4: Complaint workflow regression tests ---

def test_create_valid_complaint():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100002",
            "amount": "15000",
            "currency": "RWF",
            "category": "debited_not_credited",
            "description": "Valid complaint without evidence",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "complaint_id" in data
    assert data["registration_status"] in ("REGISTERED", "REJECTED")
    assert "request_id" in data


def test_wrong_recipient_without_evidence_rejected():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100003",
            "amount": "1000",
            "currency": "RWF",
            "category": "wrong_recipient",
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_scam_without_evidence_rejected():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100004",
            "amount": "2000",
            "currency": "RWF",
            "category": "scam",
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_transfer_reference_ending_999_is_rejected_by_hub():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100999",
            "amount": "1000",
            "currency": "RWF",
            "category": "duplicate",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["registration_status"] == "REJECTED"
    assert data["hub_claim_id"] is None


# --- Task 5: Transfer reference validation tests ---

def test_transfer_reference_valid_format_accepted():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-000001",
            "amount": "1000",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 200


def test_transfer_reference_too_short_rejected():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-123",
            "amount": "1000",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_transfer_reference_letters_instead_of_digits_rejected():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-ABCDEF",
            "amount": "1000",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_transfer_reference_missing_prefix_rejected():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "100001",
            "amount": "1000",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 400


# --- Task 6: Amount validation tests ---

def test_amount_positive_integer_string_accepted():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100010",
            "amount": "15000",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 200


def test_amount_decimal_string_accepted():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100011",
            "amount": "15000.50",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 200


def test_amount_zero_rejected():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100012",
            "amount": "0",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_amount_negative_rejected():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100013",
            "amount": "-100",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_amount_malformed_rejected():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100014",
            "amount": "abc",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_amount_empty_rejected():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100015",
            "amount": "",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 400


# --- Task 7: Category validation tests ---

def test_valid_categories_accepted():
    headers = _auth_headers("aline_green", "green123")
    for category in ["debited_not_credited", "wrong_recipient", "duplicate", "scam"]:
        resp = client.post(
            "/complaints",
            json={
                "transfer_reference": f"TXN-10002{['debited_not_credited', 'wrong_recipient', 'duplicate', 'scam'].index(category)}",
                "amount": "1000",
                "currency": "RWF",
                "category": category,
                "evidence": "statement.pdf" if category in ("wrong_recipient", "scam") else None,
            },
            headers=headers,
        )
        assert resp.status_code == 200, f"Category {category} should be accepted"


def test_invalid_category_rejected():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100030",
            "amount": "1000",
            "currency": "RWF",
            "category": "fraud",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 400


# --- Task 8: Evidence validation tests ---

def test_wrong_recipient_with_evidence_accepted():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100040",
            "amount": "1000",
            "currency": "RWF",
            "category": "wrong_recipient",
            "evidence": "statement.pdf",
        },
        headers=headers,
    )
    assert resp.status_code == 200


def test_scam_with_evidence_accepted():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100041",
            "amount": "2000",
            "currency": "RWF",
            "category": "scam",
            "evidence": "police_report.pdf",
        },
        headers=headers,
    )
    assert resp.status_code == 200


def test_debited_not_credited_without_evidence_accepted():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100042",
            "amount": "1000",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 200


def test_duplicate_without_evidence_accepted():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints",
        json={
            "transfer_reference": "TXN-100043",
            "amount": "1000",
            "currency": "RWF",
            "category": "duplicate",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 200


# --- Task 9: POST /complaints/validate endpoint tests ---

def test_validate_valid_complaint_returns_200():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints/validate",
        json={
            "transfer_reference": "TXN-200001",
            "amount": "15000",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert "message" in data


def test_validate_invalid_transfer_reference_returns_400():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints/validate",
        json={
            "transfer_reference": "INVALID-REF",
            "amount": "15000",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_validate_invalid_amount_returns_400():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints/validate",
        json={
            "transfer_reference": "TXN-200002",
            "amount": "0",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_validate_invalid_category_returns_400():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints/validate",
        json={
            "transfer_reference": "TXN-200003",
            "amount": "15000",
            "currency": "RWF",
            "category": "fraud",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_validate_missing_evidence_for_wrong_recipient_returns_400():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints/validate",
        json={
            "transfer_reference": "TXN-200004",
            "amount": "15000",
            "currency": "RWF",
            "category": "wrong_recipient",
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_validate_missing_evidence_for_scam_returns_400():
    headers = _auth_headers("aline_green", "green123")
    resp = client.post(
        "/complaints/validate",
        json={
            "transfer_reference": "TXN-200005",
            "amount": "15000",
            "currency": "RWF",
            "category": "scam",
        },
        headers=headers,
    )
    assert resp.status_code == 400


def test_validate_does_not_create_complaint():
    """Validate endpoint must not create complaints or audit records (no side effects)."""
    headers = _auth_headers("aline_green", "green123")

    # Count complaints before validation
    list_before = client.get("/complaints", headers=headers)
    assert list_before.status_code == 200
    count_before = len(list_before.json())

    # Submit valid data to validate endpoint
    resp = client.post(
        "/complaints/validate",
        json={
            "transfer_reference": "TXN-200006",
            "amount": "15000",
            "currency": "RWF",
            "category": "debited_not_credited",
            "evidence": None,
        },
        headers=headers,
    )
    assert resp.status_code == 200

    # Count complaints after validation - should be unchanged
    list_after = client.get("/complaints", headers=headers)
    assert list_after.status_code == 200
    count_after = len(list_after.json())
    assert count_after == count_before


# --- Task 10: POST /api/v1/customer-disputes hub mock tests ---

def test_hub_mock_accepted_registration_returns_claim_id():
    """A valid transfer reference (not ending in 999) is accepted by the hub mock."""
    resp = client.post(
        "/api/v1/customer-disputes",
        json={"transfer_reference": "TXN-100001"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "REGISTERED"
    assert data["claim_id"] is not None
    assert data["claim_id"].startswith("CLM-")
    assert data["message"] == "Success"


def test_hub_mock_rejected_registration_returns_null_claim_id():
    """A transfer reference ending in 999 is rejected by the hub mock."""
    resp = client.post(
        "/api/v1/customer-disputes",
        json={"transfer_reference": "TXN-100999"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "REJECTED"
    assert data["claim_id"] is None
    assert "Exceeded bounds" in data["message"]


def test_hub_mock_no_private_data_in_request():
    """The hub mock only receives the transfer reference, never private complaint data."""
    resp = client.post(
        "/api/v1/customer-disputes",
        json={"transfer_reference": "TXN-100002"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "description" not in data
    assert "evidence" not in data
    assert "operator_username" not in data
    assert "bank" not in data
    assert data["status"] == "REGISTERED"


# --- Task 11: Authentication security tests ---

def test_login_invalid_password():
    resp = client.post("/auth/login", json={"username": "aline_green", "password": "wrong_password"})
    assert resp.status_code == 401


def test_login_unknown_user():
    resp = client.post("/auth/login", json={"username": "nonexistent", "password": "anything"})
    assert resp.status_code == 401


def test_login_empty_password():
    resp = client.post("/auth/login", json={"username": "aline_green", "password": ""})
    assert resp.status_code == 401


def test_invalid_token_rejected():
    resp = client.get("/complaints", headers={"Authorization": "Bearer not-a-valid-token"})
    assert resp.status_code == 401


def test_tampered_token_rejected():
    """A token with a tampered signature must be rejected."""
    login_resp = client.post("/auth/login", json={"username": "aline_green", "password": "green123"})
    token = login_resp.json()["access_token"]
    parts = token.split(".")
    tampered = f"{parts[0]}.{parts[1]}.tampered_signature"
    resp = client.get("/complaints", headers={"Authorization": f"Bearer {tampered}"})
    assert resp.status_code == 403


def test_expired_token_rejected():
    """An expired token must be rejected."""
    import sys
    import os
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    from services.auth import create_access_token, JWT_CONFIG

    expired_token = create_access_token(
        data={"sub": "aline_green", "bank": "Greenbank"},
        secret_key=JWT_CONFIG["secret_key"],
        expires_delta_minutes=-1,
    )
    resp = client.get("/complaints", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 403


def test_missing_token_rejected():
    resp = client.get("/complaints")
    assert resp.status_code == 401


def test_wrong_scheme_rejected():
    resp = client.get("/complaints", headers={"Authorization": "Basic some-token"})
    assert resp.status_code == 401
