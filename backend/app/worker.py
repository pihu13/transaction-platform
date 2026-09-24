import logging
import threading
from .config import POLL_SECONDS, WORKER_COUNT
from .services import claim_job, process_job, recover_stale_jobs

log = logging.getLogger("transaction-worker")

_worker_stop = None
_worker_threads = []

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
        except Exception:
            log.exception("worker_loop_error worker=%s", name)
            stop_event.wait(POLL_SECONDS)


def start_workers():
    global _worker_stop, _worker_threads

    if _worker_threads:
        return _worker_stop, _worker_threads

    stop_event = threading.Event()
    threads = []

    for i in range(WORKER_COUNT):
        thread = threading.Thread(
            target=worker_loop,
            args=(f"worker-{i + 1}", stop_event),
            name=f"worker-{i + 1}",
            daemon=False,
        )
        thread.start()
        threads.append(thread)

    _worker_stop = stop_event
    _worker_threads = threads
    return stop_event, threads


def stop_workers():
    global _worker_stop, _worker_threads

    if _worker_stop:
        _worker_stop.set()

    for thread in _worker_threads:
        thread.join(timeout=5)