from __future__ import annotations

from typing import Iterable

from .models import JobConfig
from .runner import BackupRunner


class BackupScheduler:
    """Simple scheduler wrapper for running jobs defined in a config."""

    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.runner = BackupRunner(repo_root)

    def run_jobs(self, jobs: Iterable[JobConfig]) -> list:
        results = []
        for job in jobs:
            results.append(self.runner.run_job(job))
        return results
