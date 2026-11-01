from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import JobConfig


class SourceAdapter(ABC):
    @abstractmethod
    def create_snapshot(self, job: JobConfig, snapshot_dir: Path) -> dict:
        """Create a snapshot and return metadata."""