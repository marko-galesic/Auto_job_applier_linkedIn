import queue
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from modules.helpers import print_lg
from modules.job_store import JobStore


class JobWorker:
    """Background worker that processes jobs outside request threads."""

    def __init__(self, store: JobStore, poll_interval: float = 0.1) -> None:
        '''
        Initialize the background worker with a job store and queue.
        '''
        self.store = store
        self.poll_interval = poll_interval
        self.jobs_queue: "queue.Queue[str]" = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self._log_event("Initializing JobWorker and ensuring background thread is running")
        self._ensure_worker_thread()

    def enqueue(self, job_id: str) -> None:
        '''
        Add a job to the internal queue for asynchronous processing.
        '''
        self._ensure_worker_thread()
        self._log_event(f"Enqueuing job_id={job_id}")
        self.jobs_queue.put(job_id)

    def _ensure_worker_thread(self) -> None:
        '''
        Lazily start or restart the background worker thread if it stops.
        '''
        if self.worker_thread and self.worker_thread.is_alive():
            return

        self.worker_thread = threading.Thread(target=self._run, daemon=True)
        self._log_event("Starting background worker thread")
        self.worker_thread.start()

    def _run(self) -> None:
        '''
        Consume queued jobs in a background thread until shutdown.
        '''
        while True:
            job_id = self.jobs_queue.get()
            if job_id is None:
                break
            self._log_event(f"Dequeued job_id={job_id} for processing")
            ##> ------ OpenAI Assistant : openai-assistant@example.com - Bug fix ------
            try:
                self._process(job_id)
            except Exception as exc:  # pragma: no cover - defensive fallback
                self._log_event(f"Unhandled exception for job_id={job_id}: {exc}")
                self.store.update_status(job_id, status="failed", error=str(exc))
            finally:
                self.jobs_queue.task_done()
            ##<

    def _process(self, job_id: str) -> None:
        '''
        Run the LinkedIn automation for the given job identifier.
        '''
        ##> ------ OpenAI Assistant : openai-assistant@example.com - Feature ------
        payload = self.store.get_job(job_id)
        if not payload:
            self._log_event(f"Job record not found for job_id={job_id}")
            return

        self._log_event(f"Launching automation for job_id={job_id}")
        self.store.update_status(job_id, status="running", progress=5)
        progress_value = 5
        try:
            log_path = Path("logs") / "runai.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.utcnow().isoformat() + "Z"
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(f"\n---- {timestamp} job_id={job_id} ----\n")
                automation = subprocess.Popen(
                    [sys.executable, "runAiBot.py"],
                    stdout=log_file,
                    stderr=log_file,
                )
                self._log_event(
                    f"Started runAiBot.py for job_id={job_id} with pid={automation.pid}"
                )
                while automation.poll() is None:
                    progress_value = min(progress_value + 1, 95)
                    self.store.update_status(
                        job_id, status="running", progress=progress_value
                    )
                    time.sleep(self.poll_interval)

            if automation.returncode == 0:
                self._log_event(f"Automation completed successfully for job_id={job_id}")
                self.store.update_status(job_id, status="completed", progress=100)
            else:
                error_message = f"Automation exited with code {automation.returncode}"
                self._log_event(f"Automation failed for job_id={job_id}: {error_message}")
                self.store.update_status(job_id, status="failed", error=error_message)
        except Exception as exc:  # pragma: no cover - defensive logging only
            self._log_event(f"Exception while running automation for job_id={job_id}: {exc}")
            self.store.update_status(job_id, status="failed", error=str(exc))
        ##<

    def _log_event(self, message: str) -> None:
        '''
        Write lifecycle events to the shared application log.
        '''
        ##> ------ OpenAI Assistant : openai-assistant@example.com - Feature ------
        print_lg(f"[JobWorker] {message}")
        ##<
