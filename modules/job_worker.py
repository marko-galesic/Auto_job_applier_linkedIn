import queue
import subprocess
import sys
import threading
import time

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
        self.worker_thread = threading.Thread(target=self._run, daemon=True)
        self.worker_thread.start()

    def enqueue(self, job_id: str) -> None:
        '''
        Add a job to the internal queue for asynchronous processing.
        '''
        self.jobs_queue.put(job_id)

    def _run(self) -> None:
        '''
        Consume queued jobs in a background thread until shutdown.
        '''
        while True:
            job_id = self.jobs_queue.get()
            if job_id is None:
                break
            self._process(job_id)
            self.jobs_queue.task_done()

    def _process(self, job_id: str) -> None:
        '''
        Run the LinkedIn automation for the given job identifier.
        '''
        ##> ------ OpenAI Assistant : openai-assistant@example.com - Feature ------
        payload = self.store.get_job(job_id)
        if not payload:
            return

        self.store.update_status(job_id, status="running", progress=5)
        progress_value = 5
        try:
            automation = subprocess.Popen(
                [sys.executable, "runAiBot.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            while automation.poll() is None:
                progress_value = min(progress_value + 1, 95)
                self.store.update_status(job_id, status="running", progress=progress_value)
                time.sleep(self.poll_interval)

            if automation.returncode == 0:
                self.store.update_status(job_id, status="completed", progress=100)
            else:
                error_message = f"Automation exited with code {automation.returncode}"
                self.store.update_status(job_id, status="failed", error=error_message)
        except Exception as exc:  # pragma: no cover - defensive logging only
            self.store.update_status(job_id, status="failed", error=str(exc))
        ##<
