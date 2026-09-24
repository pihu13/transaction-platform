from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from .config import BASE_RETRY_SECONDS, MAX_RETRIES, PROCESSING_TIMEOUT_SECONDS
from .db import SessionLocal
from .models import Customer, Transaction


def now():
    return datetime.now(timezone.utc)


def create_transaction(data):
    with SessionLocal() as db:
        existing = db.get(Transaction, data.transaction_id)
        if existing:
            if (existing.customer_id, existing.type, existing.amount) != (data.customer_id, data.type, data.amount):
                raise ValueError("transaction_id already exists with different transaction data")
            return existing, False
        if not db.get(Customer, data.customer_id):
            raise LookupError("customer not found")
        tx = Transaction(
            id=data.transaction_id,
            customer_id=data.customer_id,
            type=data.type,
            amount=data.amount,
            status="PENDING",
            attempts=0,
            available_at=now(),
        )
        db.add(tx)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            tx = db.get(Transaction, data.transaction_id)
            if tx is None:
                raise
            return tx, False
        db.refresh(tx)
        return tx, True


def get_transaction(transaction_id):
    with SessionLocal() as db:
        return db.get(Transaction, transaction_id)


def recover_stale_jobs():
    cutoff = now() - timedelta(seconds=PROCESSING_TIMEOUT_SECONDS)
    with SessionLocal() as db:
        result = db.execute(
            update(Transaction)
            .where(Transaction.status == "PROCESSING", Transaction.claimed_at < cutoff)
            .values(status="PENDING", available_at=now(), claimed_at=None, updated_at=now())
        )
        db.commit()
        return result.rowcount


def claim_job():
    # SQLite has no SELECT ... FOR UPDATE. BEGIN IMMEDIATE takes the database write
    # lock for the short claim transaction, so two local workers cannot claim one row.
    with SessionLocal() as db:
        db.execute(text("BEGIN IMMEDIATE"))
        job = db.scalar(
            select(Transaction)
            .where(Transaction.status == "PENDING", Transaction.available_at <= now())
            .order_by(Transaction.created_at)
            .limit(1)
        )
        if job is None:
            db.commit()
            return None
        if job.attempts >= MAX_RETRIES:
            job.status = "FAILED"
            job.failure_reason = "Maximum processing attempts reached"
            job.updated_at = now()
            db.commit()
            return None
        job.status = "PROCESSING"
        job.attempts += 1
        job.claimed_at = now()
        job.updated_at = now()
        db.commit()
        return job.id


def process_job(transaction_id):
    with SessionLocal() as db:
        tx = db.get(Transaction, transaction_id)
        if not tx or tx.status != "PROCESSING":
            return

        customer = db.get(Customer, tx.customer_id)
        if not customer:
            tx.status = "FAILED"
            tx.failure_reason = "Customer no longer exists"
            tx.claimed_at = None
            db.commit()
            return

        if tx.type == "CREDIT":
            customer.balance = Decimal(customer.balance) + Decimal(tx.amount)
        else:
            # The conditional update is the balance guard. It is evaluated while
            # this DB transaction is open, so a debit cannot push the balance below zero.
            result = db.execute(
                update(Customer)
                .where(Customer.id == tx.customer_id, Customer.balance >= tx.amount)
                .values(balance=Customer.balance - tx.amount)
            )
            if result.rowcount != 1:
                tx.status = "FAILED"
                tx.failure_reason = "Insufficient balance"
                tx.claimed_at = None
                db.commit()
                return

        # Balance update and SUCCESS state are committed together. A process crash
        # before commit rolls both back; a crash after commit leaves an already-successful job.
        tx.status = "SUCCESS"
        tx.failure_reason = None
        tx.claimed_at = None
        db.commit()


def fail_for_retry(transaction_id, reason):
    with SessionLocal() as db:
        tx = db.get(Transaction, transaction_id)
        if not tx:
            return
        if tx.attempts >= MAX_RETRIES:
            tx.status = "FAILED"
            tx.failure_reason = reason
            tx.claimed_at = None
            db.commit()
            return
        delay = BASE_RETRY_SECONDS * (2 ** max(tx.attempts - 1, 0))
        tx.status = "PENDING"
        tx.failure_reason = reason
        tx.available_at = now() + timedelta(seconds=delay)
        tx.claimed_at = None
        db.commit()


def retry_transaction(transaction_id):
    with SessionLocal() as db:
        tx = db.get(Transaction, transaction_id)
        if not tx:
            return None, "not_found"
        if tx.status != "FAILED":
            return tx, "not_eligible"
        if tx.attempts >= MAX_RETRIES:
            return tx, "max_retries"
        tx.status = "PENDING"
        tx.failure_reason = None
        tx.available_at = now()
        tx.claimed_at = None
        db.commit()
        db.refresh(tx)
        return tx, "queued"


def counts():
    with SessionLocal() as db:
        rows = db.execute(select(Transaction.status, func.count()).group_by(Transaction.status)).all()
        result = {"PENDING": 0, "PROCESSING": 0, "SUCCESS": 0, "FAILED": 0}
        result.update({status: count for status, count in rows})
        return result
