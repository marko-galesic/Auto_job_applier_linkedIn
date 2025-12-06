import queue
import threading
import time
from typing import Any, Dict

from modules.job_store import JobStore


class JobWorker:
    """Background worker that processes jobs outside request threads."""

    def __init__(self, store: JobStore, poll_interval: float = 0.1) -> None:
        self.store = store
        self.poll_interval = poll_interval
        self.jobs_queue: "queue.Queue[str]" = queue.Queue()
        self.worker_thread = threading.Thread(target=self._run, daemon=True)
        self.worker_thread.start()

    def enqueue(self, job_id: str) -> None:
        self.jobs_queue.put(job_id)

    def _run(self) -> None:
        while True:
            job_id = self.jobs_queue.get()
            if job_id is None:
                break
            self._process(job_id)
            self.jobs_queue.task_done()

    def _process(self, job_id: str) -> None:
        payload = self.store.get_job(job_id)
        if not payload:
            return
        self.store.update_status(job_id, status="running", progress=0)
        try:
            for progress in (10, 40, 70, 100):
                time.sleep(self.poll_interval)
                self.store.update_status(job_id, status="running", progress=progress)

            result: Dict[str, Any] = {
                "summary": "Job finished",
                "details": {
                    "personals": bool(payload.get("payload", {}).get("personals")),
                    "questions": bool(payload.get("payload", {}).get("questions")),
                    "search_filters": bool(payload.get("payload", {}).get("search_filters")),
                },
            }
            self.store.update_status(job_id, status="completed", progress=100, result=result)
        except Exception as exc:  # pragma: no cover - defensive logging only
            self.store.update_status(job_id, status="failed", error=str(exc))
