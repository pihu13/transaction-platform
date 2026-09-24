### Below Points that is implemented

- Asynchronous transaction acknowledgement: `POST /transactions` creates a persistent job and returns without waiting for processing.
- CREDIT and DEBIT validation.
- No-negative-balance rule for DEBIT.
- Transaction-ID idempotency with a database primary key.
- Database-backed PENDING → PROCESSING → SUCCESS / FAILED workflow.
- Two local worker threads by default (`WORKER_COUNT=2`).
- Safe worker claiming using a short SQLite `BEGIN IMMEDIATE` claim transaction.
- Balance mutation and SUCCESS transition committed atomically.
- Bounded processing attempts with exponential retry delay for handled worker failures, plus a manual retry endpoint.
- Recovery of stale PROCESSING jobs after `PROCESSING_TIMEOUT_SECONDS`.
- Paginated transaction APIs and useful indexes.
- React operations dashboard with polling, filters, detail view and retry action.
- Structured, consistent worker logs containing worker and transaction IDs.
- Backend tests for idempotency, insufficient balance, concurrency and retry behaviour.

### Project layout

text
transaction-platform/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── services.py
│   │   ├── worker.py
│   │   ├── db.py
│   │   └── config.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   ├── package.json
│   └── vite.config.js
├── architecture.md
└── README.md


### Software requirment

- Python 3.11+
- Node.js 18+
- npm 9+

No database server is required. SQLite creates `backend/transactions.db` automatically.

### Run the backend

Windows PowerShell:

powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000


Linux:

bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000


The API will be available at `http://localhost:8000` and Swagger documentation at `http://localhost:8000/docs`.

## Run the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown by the terminal, normally `http://localhost:5173`.

If the API is running on another host/port, create `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

## Seed a customer

The assignment focuses on transactions, so the project includes a small local-only customer creation endpoint to make the demo easy to start.

```bash
curl -X POST "http://localhost:8000/customers/cust-001?name=Alice&opening_balance=1000"
```

PowerShell:

```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/customers/cust-001?name=Alice&opening_balance=1000"
```

## Submit a transaction

```bash
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"order-1001","customer_id":"cust-001","type":"DEBIT","amount":"125.50"}'
```

The response is an acknowledgement containing the transaction ID and current job state. The worker processes it in the background.

Check it:

```bash
curl http://localhost:8000/transactions/order-1001
curl http://localhost:8000/customers/cust-001/balance
```

## Idempotency example

Send the same `transaction_id` twice with the same transaction data. Both requests refer to the same stored transaction and only one balance mutation can occur.

If the same ID is reused with different customer/type/amount data, the API returns `409 Conflict`.

## Tests

Backend:

```bash
cd backend
pytest -q
```

Frontend smoke test:

```bash
cd frontend
npm install
npm test
```



## API summary

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/transactions` | Queue a transaction |
| GET | `/transactions/{id}` | Inspect status/attempts/failure |
| GET | `/transactions` | Paginated operations list with filters |
| POST | `/transactions/{id}/retry` | Retry a FAILED transaction |
| GET | `/customers/{id}/balance` | Current balance |
| GET | `/customers/{id}/transactions` | Customer transaction history |
| GET | `/dashboard` | PENDING/PROCESSING/SUCCESS/FAILED counts |
| GET | `/health` | Application health |
| POST | `/customers/{id}` | Local demo customer setup |

## Configuration

Environment variables:

| Variable | Default | Purpose |
|---|---:|---|
| `DATABASE_URL` | `sqlite:///./transactions.db` | Local database URL |
| `WORKER_COUNT` | `2` | Number of worker threads in the API process |
| `MAX_RETRIES` | `3` | Maximum processing attempts |
| `BASE_RETRY_SECONDS` | `2` | Base exponential retry delay |
| `PROCESSING_TIMEOUT_SECONDS` | `30` | Time before a stale PROCESSING job is recovered |
| `POLL_SECONDS` | `1` | Worker polling interval |

## Production scaling notes

SQLite is deliberately used because the assignment requires a fully local setup. It is not the intended production queue/database for a high-volume financial workload.

At roughly 100x workload I would separate the API and workers, move persistence to PostgreSQL, and replace the database queue with a durable broker such as SQS, Kafka or RabbitMQ. Balance changes would remain transactional in PostgreSQL, with a strong idempotency key/unique constraint. Metrics would include queue depth, processing latency, retry count, stale-job recoveries, failure rate and DB lock time.

## Architecture

See `architecture.md` for the component and processing flow.

## Approximate implementation effort

| Area | Approx. time |
|---|---:|
| Architecture and data model | 1.0 h |
| Backend APIs and worker | 2.5 h |
| React dashboard | 1.5 h |
| Testing and failure scenarios | 1.5 h |
| Documentation/debugging | 1.0 h |
| Total | ~7.5 h |
