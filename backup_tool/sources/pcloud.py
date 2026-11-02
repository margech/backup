from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from ..models import JobConfig
from .base import SourceAdapter


class PCloudSource(SourceAdapter):
    """Create a pCloud snapshot using a configured rclone remote."""

    def create_snapshot(self, job: JobConfig, snapshot_dir: Path) -> dict:
        rclone_bin = shutil.which("rclone")
        if not rclone_bin:
            raise FileNotFoundError("rclone is not installed or not in PATH")

        remote_name = job.cloud_remote or "pcloud"
        remote_path = job.cloud_path or "/"
        target_dir = snapshot_dir / "cloud"
        target_dir.mkdir(parents=True, exist_ok=True)

        command = [rclone_bin, "sync",
                   f"{remote_name}:{remote_path}", str(target_dir)]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr or completed.stdout or "rclone pCloud sync failed"
            )

        return {
            "source_type": "pcloud",
            "cloud_remote": remote_name,
            "cloud_path": remote_path,
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
