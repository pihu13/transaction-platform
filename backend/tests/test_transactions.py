from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from app.db import SessionLocal
from app.models import Customer
from app.services import process_job


def seed(client, balance="100.00"):
    response = client.post(f"/customers/c1", params={"name": "Test Customer", "opening_balance": balance})
    assert response.status_code == 201


def test_duplicate_submission_is_idempotent(app_client):
    seed(app_client)
    payload = {"transaction_id": "tx-1", "customer_id": "c1", "type": "CREDIT", "amount": "10.00"}
    first = app_client.post("/transactions", json=payload)
    second = app_client.post("/transactions", json=payload)
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]


def test_debit_cannot_overdraw(app_client):
    seed(app_client, "50.00")
    response = app_client.post("/transactions", json={"transaction_id": "tx-2", "customer_id": "c1", "type": "DEBIT", "amount": "60.00"})
    assert response.status_code == 202
    process_job("tx-2")
    detail = app_client.get("/transactions/tx-2").json()
    assert detail["status"] == "FAILED"
    assert detail["failure_reason"] == "Insufficient balance"
    assert app_client.get("/customers/c1/balance").json()["balance"] == "50.00"


def test_concurrent_debits_leave_correct_balance(app_client):
    seed(app_client, "100.00")
    for i in range(10):
        app_client.post("/transactions", json={"transaction_id": f"tx-{i}", "customer_id": "c1", "type": "DEBIT", "amount": "15.00"})

    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(lambda i: process_job(f"tx-{i}"), range(10)))

    balance = app_client.get("/customers/c1/balance").json()["balance"]
    assert Decimal(balance) == Decimal("10.00")


def test_retry_only_failed_transaction(app_client):
    seed(app_client)
    app_client.post("/transactions", json={"transaction_id": "tx-3", "customer_id": "c1", "type": "DEBIT", "amount": "200.00"})
    process_job("tx-3")
    response = app_client.post("/transactions/tx-3/retry")
    assert response.status_code == 202
    assert response.json()["status"] == "PENDING"
