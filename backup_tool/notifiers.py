from __future__ import annotations

import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from .models import JobConfig


class SourceAdapter(ABC):
    """Base class for all source adapters."""

    @abstractmethod
    def create_snapshot(self, job: JobConfig, snapshot_dir: Path) -> dict:
        """Create a snapshot for the given job and return metadata."""


class FilesystemSource(SourceAdapter):
    """Back up a directory tree using rsync."""

    def create_snapshot(self, job: JobConfig, snapshot_dir: Path) -> dict:
        source_path = Path(job.source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source does not exist: {source_path}")

        rsync_bin = shutil.which("rsync")
        if not rsync_bin:
            raise FileNotFoundError("rsync is not installed or not in PATH")

        cmd = [rsync_bin, "-a", "--delete", f"{source_path.as_posix()}/", str(snapshot_dir)]
        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout or "rsync failed")

        # Count files and directories for metadata.
        file_count = sum(1 for _ in snapshot_dir.rglob("*") if _.is_file())
        return {
            "source_type": "filesystem",
            "file_count": file_count,
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }


class SqlDumpSource(SourceAdapter):
    """Create a dump for common relational database tools."""

    def create_snapshot(self, job: JobConfig, snapshot_dir: Path) -> dict:
        name = job.source_path or "dump"
        dump_path = snapshot_dir / f"{name}.sql"
        dump_path.parent.mkdir(parents=True, exist_ok=True)

        source_type = job.source_type.lower()
        if source_type == "postgres":
            tool = shutil.which("pg_dump")
            if not tool:
                raise FileNotFoundError("pg_dump is not installed or not in PATH")
            cmd = [tool, "--file", str(dump_path), job.source_path]
        elif source_type == "mysql":
            tool = shutil.which("mysqldump")
            if not tool:
                raise FileNotFoundError("mysqldump is not installed or not in PATH")
            cmd = [tool, job.source_path, "--result-file", str(dump_path)]
        elif source_type == "sqlite":
            tool = shutil.which("sqlite3")
            if not tool:
                raise FileNotFoundError("sqlite3 is not installed or not in PATH")
            cmd = [tool, job.source_path, ".backup", str(dump_path)]
        else:
            raise ValueError(f"Unsupported SQL source type: {job.source_type}")

        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout or "SQL dump failed")

        return {
            "source_type": job.source_type,
            "dump_path": str(dump_path),
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }


class PCloudSource(SourceAdapter):
    """Stub for future pCloud integration. This is intentionally explicit."""

    def create_snapshot(self, job: JobConfig, snapshot_dir: Path) -> dict:
        raise NotImplementedError(
            "pCloud support is not implemented yet. Use filesystem/SQL adapters or add a dedicated cloud adapter."
        )


def create_source(job: JobConfig) -> SourceAdapter:
    source_type = (job.source_type or "").lower()
    if source_type == "filesystem":
        return FilesystemSource()
    if source_type in {"postgres", "mysql", "sqlite"}:
        return SqlDumpSource()
    if source_type == "pcloud":
        return PCloudSource()
    raise ValueError(f"Unsupported source type: {job.source_type}")
