import logging
import threading
import time
from .config import POLL_SECONDS, WORKER_COUNT
from .services import claim_job, process_job, recover_stale_jobs

log = logging.getLogger("transaction-worker")


def worker_loop(name, stop_event):
    while not stop_event.is_set():
        try:
            recover_stale_jobs()
            job_id = claim_job()
            if not job_id:
                stop_event.wait(POLL_SECONDS)
                continue
            log.info("job_claimed worker=%s transaction_id=%s", name, job_id)
            try:
                process_job(job_id)
                log.info("job_finished worker=%s transaction_id=%s", name, job_id)
            except Exception:
                log.exception("job_failed worker=%s transaction_id=%s", name, job_id)
                # Leaving PROCESSING is intentional. The recovery sweep moves it
                # back to PENDING after the timeout, avoiding an unsafe immediate retry.
        except Exception:
            log.exception("worker_loop_error worker=%s", name)
            stop_event.wait(POLL_SECONDS)


def start_workers():
    stop_event = threading.Event()
    threads = []
    for i in range(WORKER_COUNT):
        thread = threading.Thread(target=worker_loop, args=(f"worker-{i + 1}", stop_event), daemon=True)
        thread.start()
        threads.append(thread)
    return stop_event, threads
