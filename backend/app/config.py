import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./transactions.db")
WORKER_COUNT = int(os.getenv("WORKER_COUNT", "2"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
BASE_RETRY_SECONDS = int(os.getenv("BASE_RETRY_SECONDS", "2"))
PROCESSING_TIMEOUT_SECONDS = int(os.getenv("PROCESSING_TIMEOUT_SECONDS", "30"))
POLL_SECONDS = float(os.getenv("POLL_SECONDS", "1"))
