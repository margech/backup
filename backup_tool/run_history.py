from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from .models import BackupResult, JobConfig


class RunHistory:
    retention_days = 90

    def __init__(self, repo_root: str | Path):
        self.directory = Path(repo_root) / "run-history"

    def record(self, job: JobConfig, result: BackupResult) -> Path:
        finished_at = datetime.fromisoformat(
            result.finished_at.replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        record_id = uuid4().hex
        job_directory = quote(result.job_id, safe="-_.")
        if job_directory in {".", ".."}:
            job_directory = f"_{job_directory}"
        job_path = self.directory / job_directory
        record_directory = (
            job_path / finished_at.strftime("%Y/%m")
        )
        for directory in (
            self.directory,
            job_path,
            record_directory.parent,
            record_directory,
        ):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)

        record_path = record_directory / f"{record_id}.json"
        temporary_path = record_directory / f".{record_id}.tmp"
        record = {
            "run_id": record_id,
            "job_id": result.job_id,
            "job_name": job.name,
            "source_type": job.source_type,
            "status": result.status,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "duration_seconds": result.duration_seconds,
            "snapshot_path": result.snapshot_path,
            "error_type": result.metadata.get("error_type") or (
                "BackupError" if result.status == "failed" else None
            ),
        }

        descriptor = os.open(
            temporary_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                json.dump(record, file, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, record_path)
        finally:
            temporary_path.unlink(missing_ok=True)

        self.prune()
        return record_path

    def list_runs(
        self, job_id: str | None = None, limit: int = 20
    ) -> list[dict[str, object]]:
        if limit < 1:
            raise ValueError("limit must be greater than zero")

        records = []
        if not self.directory.exists():
            return records

        for path in self.directory.rglob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    f"Unable to read run history: {path}") from exc
            if not isinstance(record, dict):
                raise RuntimeError(f"Invalid run history record: {path}")
            if job_id is None or record.get("job_id") == job_id:
                records.append(record)

        records.sort(key=lambda item: str(
            item.get("finished_at", "")), reverse=True)
        return records[:limit]

    def prune(self, now: datetime | None = None) -> None:
        if not self.directory.exists():
            return

        current_time = now or datetime.now(timezone.utc)
        cutoff = (current_time - timedelta(days=self.retention_days)).timestamp()
        for path in self.directory.rglob("*.json"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                continue

        for path in sorted(self.directory.rglob("*"), reverse=True):
            if path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass
