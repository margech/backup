from __future__ import annotations

import json
import os
import time
import subprocess
from datetime import datetime
from pathlib import Path

from .lock import BackupLock
from .models import BackupResult, JobConfig, NotifierConfig
from .notifiers import build_notifier
from .retention import RetentionPolicy
from .sources import create_source


class BackupRunner:
    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root)
        self.repo_root.mkdir(parents=True, exist_ok=True)
        self.lock = BackupLock(self.repo_root / "backup.lock")

    def _snapshot_dir_for(self, job: JobConfig) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        snapshot_root = self.repo_root / "snapshots" / job.id
        snapshot_root.mkdir(parents=True, exist_ok=True)
        return snapshot_root / f"{timestamp}.tmp"

    def _finalize_snapshot(self, temp_dir: Path, final_dir: Path) -> None:
        if final_dir.exists():
            raise FileExistsError(f"Snapshot already exists: {final_dir}")
        temp_dir.rename(final_dir)

    def run_job(self, job: JobConfig) -> BackupResult:
        if not self.lock.acquire():
            raise RuntimeError(
                f"Another backup for {job.id} is already running.")

        started = time.time()
        started_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        temp_snapshot_dir = self._snapshot_dir_for(job)
        temp_snapshot_dir.mkdir(parents=True, exist_ok=True)

        try:
            source = create_source(job)
            metadata = source.create_snapshot(job, temp_snapshot_dir)

            final_snapshot_dir = temp_snapshot_dir.parent / \
                temp_snapshot_dir.name.replace(".tmp", "")
            self._finalize_snapshot(temp_snapshot_dir, final_snapshot_dir)

            manifest = {
                "job_id": job.id,
                "job_name": job.name,
                "source_type": job.source_type,
                "snapshot_path": str(final_snapshot_dir),
                "created_at": started_at,
                "metadata": metadata,
            }
            (final_snapshot_dir / "manifest.json").write_text(json.dumps(manifest,
                                                                         indent=2), encoding="utf-8")

            RetentionPolicy(job.retention).apply(self.repo_root, job.id)

            finished = time.time()
            result = BackupResult(
                job_id=job.id,
                status="success",
                snapshot_path=str(final_snapshot_dir),
                started_at=started_at,
                finished_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
                duration_seconds=finished - started,
                message=f"Backup successful for {job.name}",
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover - real-world failure path
            if temp_snapshot_dir.exists():
                for child in sorted(temp_snapshot_dir.rglob("*"), reverse=True):
                    if child.is_file() or child.is_symlink():
                        child.unlink()
                    elif child.is_dir():
                        child.rmdir()
                try:
                    temp_snapshot_dir.rmdir()
                except OSError:
                    pass

            finished = time.time()
            result = BackupResult(
                job_id=job.id,
                status="failed",
                snapshot_path=None,
                started_at=started_at,
                finished_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
                duration_seconds=finished - started,
                message=f"Backup failed for {job.name}: {exc}",
                metadata={"error": str(exc)},
            )
        finally:
            self.lock.release()

        self._dispatch_notifications(job, result)
        return result

    def _dispatch_notifications(self, job: JobConfig, result: BackupResult) -> None:
        for notifier_config in job.notifiers:
            notifier = build_notifier(notifier_config.__dict__)
            if not notifier:
                continue
            if result.status in notifier_config.on:
                notifier.send({
                    "job_id": job.id,
                    "job_name": job.name,
                    "status": result.status,
                    "message": result.message,
                })


def load_jobs_from_config(config_path: str | os.PathLike[str]) -> list[JobConfig]:
    import yaml

    raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    jobs_data = raw.get("jobs", [])

    jobs: list[JobConfig] = []
    for item in jobs_data:
        notifiers = []
        for raw_notifier in item.get("notifiers", []):
            notifiers.append(
                NotifierConfig(
                    type=raw_notifier.get("type", "email"),
                    on=raw_notifier.get(
                        "on", raw_notifier.get(True, ["success", "failure"])),
                    to=raw_notifier.get("to"),
                    subject=raw_notifier.get("subject"),
                    title=raw_notifier.get("title"),
                )
            )

        retention = item.get("retention", {}) or {}
        jobs.append(
            JobConfig(
                id=item["id"],
                name=item.get("name", item["id"]),
                source_type=item.get("source_type", "filesystem"),
                source_path=item.get("source_path", "."),
                destination=item.get("destination", "."),
                notifiers=notifiers,
                schedule=item.get("schedule"),
                transport=item.get("transport", "local"),
                remote_host=item.get("remote_host"),
                remote_user=item.get("remote_user"),
                source_excludes=item.get("source_excludes") or item.get(
                    "excludes") or item.get("exclude") or [],
                source_includes=item.get("source_includes") or item.get(
                    "includes") or item.get("include") or [],
                retention={
                    "daily": int(retention.get("daily", 7)),
                    "weekly": int(retention.get("weekly", 4)),
                    "monthly": int(retention.get("monthly", 12)),
                },
                account_id=item.get("account_id"),
                cloud_remote=item.get("cloud_remote"),
                cloud_path=item.get("cloud_path"),
            )
        )
    return jobs


class EmailNotifier:
    """Send notification emails."""

    def __init__(self, config: dict):
        self.config = config

    def send(self, event: dict) -> None:
        to_address = self.config.get("to")
        if not to_address:
            return

        smtp_host = os.getenv("SMTP_HOST")
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        if not smtp_host:
            return

        msg = EmailMessage()
        msg["Subject"] = self.config.get(
            "subject") or f"Backup event: {event.get('job_id', 'unknown')}"
        msg["From"] = os.getenv("SMTP_FROM", smtp_user or "backup@example.com")
        msg["To"] = to_address
        msg.set_content(event.get("message", "Backup event"))

        try:
            with smtplib.SMTP(smtp_host, 587) as server:
                if smtp_user and smtp_password:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)
        except Exception:
            # Keep the caller robust. Notification failure should not crash the backup itself.
            pass


class DesktopNotifier:
    """Send a local desktop notification if a graphical session is available."""

    def __init__(self, config: dict):
        self.config = config

    def send(self, event: dict) -> None:
        if not os.getenv("DISPLAY"):
            return

        notify_bin = subprocess.run(
            ["which", "notify-send"], capture_output=True, text=True)
        if notify_bin.returncode != 0:
            return

        title = self.config.get("title") or "Backup status"
        message = event.get("message", "Backup finished")
        subprocess.run(["notify-send", title, message], check=False)


def build_notifier(notifier_config: dict):
    notifier_type = (notifier_config.get("type") or "").lower()
    if notifier_type == "email":
        return EmailNotifier(notifier_config)
    if notifier_type == "desktop":
        return DesktopNotifier(notifier_config)
    return None
