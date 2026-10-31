from __future__ import annotations

import shutil
from pathlib import Path


def restore_snapshot(snapshot_path: str | Path, target_dir: str | Path) -> None:
    """Copy a restored snapshot to a target directory."""
    source = Path(snapshot_path)
    destination = Path(target_dir)
    destination.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        if child.name == "manifest.json":
            continue
        shutil.copytree(child, destination / child.name, dirs_exist_ok=True)
