from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from ..models import JobConfig
from .filesystem import FilesystemSource


class SSHSource(FilesystemSource):
    """Back up a remote directory over SSH using rsync."""

    def create_snapshot(self, job: JobConfig, snapshot_dir: Path) -> dict:
        if not job.remote_host:
            raise ValueError("remote_host is required for SSH source")

        ssh_job = replace(job, transport="ssh")
        metadata = super().create_snapshot(ssh_job, snapshot_dir)
        metadata["source_type"] = "ssh"
        metadata["transport"] = "ssh"
        return metadata
