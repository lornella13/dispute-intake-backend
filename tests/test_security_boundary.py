import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_signature_cross_bank_isolation_boundary():
    # 1. Greenbank operator files a complaint containing a private note
    green_headers = {"Authorization": "Bearer op_green_token"}
    payload = {
        "transfer_reference": "TXN-AUTHENTIC-88122",
        "amount": "15000",
        "currency": "RWF",
        "category": "debited_not_credited",
        "description": "CRITICAL PRIVATE NOTE: Suspected internal failure."
    }
    
    create_res = client.post("/complaints", json=payload, headers=green_headers)
    assert create_res.status_code == 200
    complaint_id = create_res.json()["complaint_id"]
    
    # 2. Bluemobile operator attempts to read Greenbank's private record
    blue_headers = {"Authorization": "Bearer op_blue_token"}
    attack_res = client.get(f"/complaints/{complaint_id}", headers=blue_headers)
    
    # 3. Assert strict multi-tenant 404 security compliance
    assert attack_res.status_code == 404
