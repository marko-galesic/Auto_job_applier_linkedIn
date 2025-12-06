import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


class JobStore:
    """SQLite-backed job persistence layer."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        directory = os.path.dirname(db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    payload TEXT,
                    result TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create_job(self, payload: Dict[str, Any]) -> str:
        job_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, status, progress, payload, result, error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, "queued", 0, json.dumps(payload or {}), None, None, now, now),
            )
        return job_id

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, status, progress, payload, result, error, created_at, updated_at FROM jobs"
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, status, progress, payload, result, error, created_at, updated_at FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def update_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        job = self.get_job(job_id)
        if not job:
            return
        new_progress = progress if progress is not None else job.get("progress", 0)
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, progress = ?, result = ?, error = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, new_progress, json.dumps(result) if result is not None else job.get("result"), error, now, job_id),
            )

    def update_payload(self, job_id: str, payload_updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        job = self.get_job(job_id)
        if not job:
            return None
        existing_payload = job.get("payload", {})
        merged_payload = {**existing_payload, **payload_updates}
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET payload = ?, updated_at = ? WHERE id = ?",
                (json.dumps(merged_payload), now, job_id),
            )
        job.update({"payload": merged_payload, "updated_at": now})
        return job

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        (
            job_id,
            status,
            progress,
            payload,
            result,
            error,
            created_at,
            updated_at,
        ) = row
        return {
            "id": job_id,
            "status": status,
            "progress": progress,
            "payload": json.loads(payload) if payload else {},
            "result": json.loads(result) if result else None,
            "error": error,
            "created_at": created_at,
            "updated_at": updated_at,
        }
