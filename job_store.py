import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import JOBS_FILE, DOWNLOADS_DIR

DOWNLOADS_DIR.mkdir(exist_ok=True)


def _ensure_jobs_file() -> None:
    if not JOBS_FILE.exists():
        JOBS_FILE.write_text("[]", encoding="utf-8")


def _load_jobs() -> List[Dict[str, Any]]:
    _ensure_jobs_file()
    try:
        return json.loads(JOBS_FILE.read_text(encoding="utf-8"))
    except Exception:
        JOBS_FILE.write_text("[]", encoding="utf-8")
        return []


def _save_jobs(jobs: List[Dict[str, Any]]) -> None:
    JOBS_FILE.write_text(json.dumps(jobs, indent=2), encoding="utf-8")


def _find_job(job_id: str) -> Optional[Dict[str, Any]]:
    for job in _load_jobs():
        if job.get("id") == job_id:
            return job
    return None


def create_job(job_type: str, connection_id: str, tables: List[str]) -> Dict[str, Any]:
    jobs = _load_jobs()
    job = {
        "id": str(uuid.uuid4()),
        "type": job_type,
        "connection_id": connection_id,
        "tables": tables,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "summary": {},
        "artifact": {},
        "errors": [],
    }
    jobs.append(job)
    _save_jobs(jobs)
    return job


def update_job(job_id: str, **changes: Any) -> Optional[Dict[str, Any]]:
    jobs = _load_jobs()
    for idx, job in enumerate(jobs):
        if job.get("id") == job_id:
            job.update(changes)
            job["updated_at"] = datetime.utcnow().isoformat()
            jobs[idx] = job
            _save_jobs(jobs)
            return job
    return None


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    return _find_job(job_id)


def list_jobs(limit: int = 20) -> List[Dict[str, Any]]:
    jobs = _load_jobs()
    sorted_jobs = sorted(jobs, key=lambda item: item.get("created_at", ""), reverse=True)
    return sorted_jobs[:limit]


def download_path(job_id: str) -> Path:
    return DOWNLOADS_DIR / f"{job_id}.xlsx"
