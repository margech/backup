from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from ..models import JobConfig
from .base import SourceAdapter


class SqlDumpSource(SourceAdapter):
    """Create database dumps using native DB tooling."""

    def create_snapshot(self, job: JobConfig, snapshot_dir: Path) -> dict:
        dump_path = snapshot_dir / \
            f"{Path(job.source_path).name or 'dump'}.sql"
        dump_path.parent.mkdir(parents=True, exist_ok=True)

        source_type = job.source_type.lower()
        if source_type == "postgres":
            tool = shutil.which("pg_dump")
            if not tool:
                raise FileNotFoundError(
                    "pg_dump is not installed or not in PATH")
            if job.transport == "ssh":
                host = job.remote_host or "localhost"
                user = job.remote_user or "root"
                ssh_cmd = f"ssh -o StrictHostKeyChecking=no {user}@{host} 'pg_dump {job.source_path}'"
                completed = subprocess.run(
                    ssh_cmd, shell=True, capture_output=True, text=True)
                if completed.returncode != 0:
                    raise RuntimeError(
                        completed.stderr or completed.stdout or "SSH PostgreSQL dump failed")
                dump_path.write_text(completed.stdout, encoding="utf-8")
                return {"source_type": job.source_type, "transport": job.transport, "dump_path": str(dump_path)}
            command = [tool, "--file", str(dump_path), job.source_path]
        elif source_type == "mysql":
            tool = shutil.which("mysqldump")
            if not tool:
                raise FileNotFoundError(
                    "mysqldump is not installed or not in PATH")
            if job.transport == "ssh":
                host = job.remote_host or "localhost"
                user = job.remote_user or "root"
                ssh_cmd = f"ssh -o StrictHostKeyChecking=no {user}@{host} 'mysqldump {job.source_path}'"
                completed = subprocess.run(
                    ssh_cmd, shell=True, capture_output=True, text=True)
                if completed.returncode != 0:
                    raise RuntimeError(
                        completed.stderr or completed.stdout or "SSH MySQL dump failed")
                dump_path.write_text(completed.stdout, encoding="utf-8")
                return {"source_type": job.source_type, "transport": job.transport, "dump_path": str(dump_path)}
            command = [tool, job.source_path, "--result-file", str(dump_path)]
        elif source_type == "sqlite":
            tool = shutil.which("sqlite3")
            if not tool:
                raise FileNotFoundError(
                    "sqlite3 is not installed or not in PATH")
            command = [tool, job.source_path, ".backup", str(dump_path)]
        else:
            raise ValueError(f"Unsupported SQL source type: {job.source_type}")

        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr or completed.stdout or "SQL dump failed")

        return {
            "source_type": job.source_type,
            "transport": job.transport,
            "dump_path": str(dump_path),
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
