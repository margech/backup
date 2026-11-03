from __future__ import annotations

import shutil
from pathlib import Path


def restore_snapshot(snapshot_path: str | Path, target_dir: str | Path) -> None:
    """Restore a snapshot directory to a target path."""
    source = Path(snapshot_path)
    destination = Path(target_dir)
    destination.mkdir(parents=True, exist_ok=True)

    for child in source.iterdir():
        if child.name == "manifest.json":
            continue
        target_child = destination / child.name
        if child.is_dir():
            shutil.copytree(child, target_child, dirs_exist_ok=True)
        else:
            shutil.copy2(child, target_child)
