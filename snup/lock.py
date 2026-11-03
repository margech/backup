from __future__ import annotations

import os
from pathlib import Path


class BackupLock:
    """Simple lock to avoid concurrent backup runs for the same repository."""

    def __init__(self, lock_path: str | Path):
        self.lock_path = Path(lock_path)

    def acquire(self) -> bool:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            file = open(self.lock_path, "x", encoding="utf-8")
            file.write(str(os.getpid()))
            file.flush()
            file.close()
            return True
        except FileExistsError:
            pid_text = self.lock_path.read_text(
                encoding="utf-8", errors="ignore").strip()
            if pid_text.isdigit():
                try:
                    os.kill(int(pid_text), 0)
                except OSError:
                    self.lock_path.unlink(missing_ok=True)
                    return self.acquire()
            return False

    def release(self) -> None:
        try:
            self.lock_path.unlink(missing_ok=True)
        except OSError:
            pass
