from __future__ import annotations

import shutil
from pathlib import Path


class RetentionPolicy:
    """Simple retention policy based on daily/weekly/monthly counts."""

    def __init__(self, config: dict[str, int] | None = None):
        if config is None:
            config = {"daily": 7, "weekly": 4, "monthly": 12}
        self.config = config

    def apply(self, repo_root: Path, job_id: str) -> None:
        snapshot_root = repo_root / "snapshots" / job_id
        if not snapshot_root.exists():
            return

        snapshots = sorted(
            [p for p in snapshot_root.iterdir() if p.is_dir()],
            key=lambda p: p.name,
        )
        if not snapshots:
            return

        keep: set[str] = set()
        daily_count = self.config.get("daily", 0)
        weekly_count = self.config.get("weekly", 0)
        monthly_count = self.config.get("monthly", 0)

        for idx in range(1, min(daily_count, len(snapshots)) + 1):
            keep.add(snapshots[-idx].name)

        if weekly_count > 0:
            for idx in range(1, min(weekly_count, len(snapshots) - daily_count) + 1):
                candidate = snapshots[-(daily_count + idx)]
                keep.add(candidate.name)

        if monthly_count > 0:
            offset = daily_count + weekly_count
            for idx in range(1, min(monthly_count, max(0, len(snapshots) - offset)) + 1):
                candidate = snapshots[-(offset + idx)]
                keep.add(candidate.name)

        for snapshot in snapshots:
            if snapshot.name not in keep:
                shutil.rmtree(snapshot)
