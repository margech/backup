from __future__ import annotations

import shutil
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from .models import JobConfig


class SourceAdapter(ABC):
    @abstractmethod
    def create_snapshot(self, job: JobConfig, snapshot_dir: Path) -> dict:
        """Create a snapshot and return metadata."""


class FilesystemSource(SourceAdapter):
    """Back up a local or remote directory tree using rsync."""

    def _build_rsync_command(self, job: JobConfig, snapshot_dir: Path) -> list[str]:
        rsync_bin = shutil.which("rsync")
        if not rsync_bin:
            raise FileNotFoundError("rsync is not installed or not in PATH")

        command = [rsync_bin, "-a", "--delete"]
        for pattern in job.source_excludes:
            command += ["--exclude", pattern]
        for pattern in job.source_includes:
            command += ["--include", pattern]

        if job.transport == "ssh":
            if not job.remote_host:
                raise ValueError("remote_host is required for SSH transport")
            host = job.remote_host
            user = job.remote_user or "root"
            server_path = f"{user}@{host}:{job.source_path}"
            command += ["-e", "ssh -o StrictHostKeyChecking=no"]
            command += [f"{server_path}/", str(snapshot_dir)]
        else:
            source_path = Path(job.source_path)
            if not source_path.exists():
                raise FileNotFoundError(f"Source does not exist: {source_path}")
            command += [f"{source_path.as_posix()}/", str(snapshot_dir)]
        return command

    def create_snapshot(self, job: JobConfig, snapshot_dir: Path) -> dict:
        command = self._build_rsync_command(job, snapshot_dir)
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout or "rsync failed")

        file_count = sum(1 for _ in snapshot_dir.rglob("*") if _.is_file())
        return {
            "source_type": "filesystem",
            "transport": job.transport,
            "file_count": file_count,
            "excluded_patterns": job.source_excludes,
            "included_patterns": job.source_includes,
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }


class SqlDumpSource(SourceAdapter):
    """Create database dumps using native DB tooling."""

    def create_snapshot(self, job: JobConfig, snapshot_dir: Path) -> dict:
        dump_path = snapshot_dir / f"{Path(job.source_path).name or 'dump'}.sql"
        dump_path.parent.mkdir(parents=True, exist_ok=True)

        source_type = job.source_type.lower()
        if source_type == "postgres":
            tool = shutil.which("pg_dump")
            if not tool:
                raise FileNotFoundError("pg_dump is not installed or not in PATH")
            if job.transport == "ssh":
                host = job.remote_host or "localhost"
                user = job.remote_user or "root"
                ssh_cmd = f"ssh -o StrictHostKeyChecking=no {user}@{host} 'pg_dump {job.source_path}'"
                completed = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
                if completed.returncode != 0:
                    raise RuntimeError(completed.stderr or completed.stdout or "SSH PostgreSQL dump failed")
                dump_path.write_text(completed.stdout, encoding="utf-8")
                return {"source_type": job.source_type, "transport": job.transport, "dump_path": str(dump_path)}
            cmd = [tool, "--file", str(dump_path), job.source_path]
        elif source_type == "mysql":
            tool = shutil.which("mysqldump")
            if not tool:
                raise FileNotFoundError("mysqldump is not installed or not in PATH")
            if job.transport == "ssh":
                host = job.remote_host or "localhost"
                user = job.remote_user or "root"
                ssh_cmd = f"ssh -o StrictHostKeyChecking=no {user}@{host} 'mysqldump {job.source_path}'"
                completed = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
                if completed.returncode != 0:
                    raise RuntimeError(completed.stderr or completed.stdout or "SSH MySQL dump failed")
                dump_path.write_text(completed.stdout, encoding="utf-8")
                return {"source_type": job.source_type, "transport": job.transport, "dump_path": str(dump_path)}
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
            "transport": job.transport,
            "dump_path": str(dump_path),
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }


class PCloudSource(SourceAdapter):
    """rclone-backed adapter for pCloud remote sources."""

    def create_snapshot(self, job: JobConfig, snapshot_dir: Path) -> dict:
        rclone_bin = shutil.which("rclone")
        if not rclone_bin:
            raise FileNotFoundError("rclone is not installed or not in PATH")

        remote_name = job.cloud_remote or "pcloud"
        remote_path = job.cloud_path or "/"
        target_dir = snapshot_dir / "cloud"
        target_dir.mkdir(parents=True, exist_ok=True)

        cmd = [rclone_bin, "sync", f"{remote_name}:{remote_path}", str(target_dir)]
        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout or "rclone pCloud sync failed")

        return {
            "source_type": "pcloud",
            "cloud_remote": remote_name,
            "cloud_path": remote_path,
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }


def create_source(job: JobConfig) -> SourceAdapter:
    source_type = (job.source_type or "").lower()
    if source_type == "filesystem":
        return FilesystemSource()
    if source_type in {"postgres", "mysql", "sqlite"}:
        return SqlDumpSource()
    if source_type == "pcloud":
        return PCloudSource()
    raise ValueError(f"Unsupported source type: {job.source_type}")
