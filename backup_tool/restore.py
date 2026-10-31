from __future__ import annotations

import shutil
from datetime import datetime
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

        keep = set()
        daily_count = self.config.get("daily", 0)
        weekly_count = self.config.get("weekly", 0)
        monthly_count = self.config.get("monthly", 0)

        # Keep newest daily snapshots.
        keep.update({snapshots[-i].name for i in range(1, daily_count + 1) if i <= len(snapshots)})

        # Keep oldest snapshots from the weekly and monthly windows.
        if weekly_count > 0:
            for idx in range(1, weekly_count + 1):
                candidate = snapshots[-(daily_count + idx)] if daily_count + idx <= len(snapshots) else None
                if candidate is not None:
                    keep.add(candidate.name)

        if monthly_count > 0:
            for idx in range(1, monthly_count + 1):
                candidate = snapshots[-(daily_count + weekly_count + idx)] if daily_count + weekly_count + idx <= len(snapshots) else None
                if candidate is not None:
                    keep.add(candidate.name)

        for snapshot in snapshots:
            if snapshot.name not in keep:
                shutil.rmtree(snapshot)
