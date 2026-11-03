from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from ..models import JobConfig
from .base import SourceAdapter


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