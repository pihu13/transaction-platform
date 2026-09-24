import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from .config import WORKER_COUNT
from .db import Base, SessionLocal, engine
from .models import Customer, Transaction
from .schemas import BalanceResponse, HealthResponse, TransactionCreate, TransactionPage, TransactionResponse
from .services import counts, create_transaction, get_transaction, retry_transaction
from .worker import start_workers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    stop_event, threads = start_workers()
    app.state.worker_stop = stop_event
    yield
    stop_event.set()


app = FastAPI(title="Local Transaction Processor", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/health", response_model=HealthResponse)
def health():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return HealthResponse(status="ok", database="ok", workers=WORKER_COUNT)
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")


@app.post("/transactions", response_model=TransactionResponse, status_code=202)
def submit_transaction(payload: TransactionCreate):
    try:
        tx, created = create_transaction(payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return tx


@app.get("/transactions/{transaction_id}", response_model=TransactionResponse)
def transaction_detail(transaction_id: str):
    tx = get_transaction(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction not found")
    return tx


@app.post("/transactions/{transaction_id}/retry", response_model=TransactionResponse, status_code=202)
def retry(transaction_id: str):
    tx, result = retry_transaction(transaction_id)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="transaction not found")
    if result == "not_eligible":
        raise HTTPException(status_code=409, detail="only FAILED transactions can be retried")
    if result == "max_retries":
        raise HTTPException(status_code=409, detail="maximum retries reached")
    return tx


@app.get("/customers/{customer_id}/balance", response_model=BalanceResponse)
def balance(customer_id: str):
    with SessionLocal() as db:
        customer = db.get(Customer, customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="customer not found")
        return BalanceResponse(customer_id=customer_id, balance=customer.balance)


@app.get("/customers/{customer_id}/transactions", response_model=TransactionPage)
def customer_transactions(customer_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    with SessionLocal() as db:
        if not db.get(Customer, customer_id):
            raise HTTPException(status_code=404, detail="customer not found")
        base = select(Transaction).where(Transaction.customer_id == customer_id).order_by(Transaction.created_at.desc())
        total = db.scalar(select(func.count()).select_from(base.subquery()))
        items = db.scalars(base.offset((page - 1) * page_size).limit(page_size)).all()
        return TransactionPage(items=items, page=page, page_size=page_size, total=total)


@app.get("/transactions", response_model=TransactionPage)
def transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: str | None = None,
    type: str | None = None,
    status: str | None = None,
):
    with SessionLocal() as db:
        query = select(Transaction)
        count_query = select(func.count()).select_from(Transaction)
        filters = []
        if customer_id:
            filters.append(Transaction.customer_id == customer_id)
        if type:
            filters.append(Transaction.type == type.upper())
        if status:
            filters.append(Transaction.status == status.upper())
        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)
        query = query.order_by(Transaction.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = db.scalars(query).all()
        total = db.scalar(count_query)
        return TransactionPage(items=items, page=page, page_size=page_size, total=total)


@app.get("/dashboard")
def dashboard():
    return counts()


@app.post("/customers/{customer_id}", status_code=201)
def create_customer(customer_id: str, name: str, opening_balance: float = 0):
    # Small local-demo endpoint; production systems would put customer creation behind its own workflow/auth.
    with SessionLocal() as db:
        if db.get(Customer, customer_id):
            raise HTTPException(status_code=409, detail="customer already exists")
        customer = Customer(id=customer_id, name=name, balance=opening_balance)
        db.add(customer)
        db.commit()
        return {"id": customer.id, "name": customer.name, "balance": customer.balance}
