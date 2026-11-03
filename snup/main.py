from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic

from .dependencies import (
    check_program_dependencies,
    check_python_dependencies,
)
from .models import BackupResult, JobConfig
from .restore import restore_snapshot
from .run_history import RunHistory
from .runner import (
    BackupAlreadyRunningError,
    BackupRunner,
    load_jobs_from_config,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Snup snapshot backup tool")
    parser.add_argument("action", choices=[
                        "run", "list", "restore", "status", "check"], help="Action to execute")
    parser.add_argument("--config", default="jobs.yaml",
                        help="Path to the YAML job definition file (default: jobs.yaml)")
    parser.add_argument("--env-file", default=".env",
                        help="Path to an environment file (default: .env)")
    parser.add_argument(
        "--job", help="Optional job id to run, filter, or check")
    parser.add_argument("--limit", type=int, default=20,
                        help="Maximum number of runs shown by status (default: 20)")
    parser.add_argument("--repo-root", default="./.backup_store",
                        help="Fallback repository root for jobs without destination")
    parser.add_argument("--snapshot", help="Snapshot directory to restore")
    parser.add_argument("--target", help="Restore target directory")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.action == "check":
        checks = check_python_dependencies()
        for check in checks:
            state = "OK" if check.available else "MISSING"
            location = f" ({check.location})" if check.location else ""
            print(f"{state}: {check.name}{location}")

        yaml_available = any(
            check.name == "Python package PyYAML" and check.available
            for check in checks
        )
        if not yaml_available:
            print(
                "Cannot inspect job-specific programs without PyYAML.",
                file=sys.stderr,
            )
            raise SystemExit(1)

        try:
            jobs = load_jobs_from_config(args.config)
        except Exception as exc:
            print(
                f"Cannot inspect job configuration ({type(exc).__name__}).",
                file=sys.stderr,
            )
            raise SystemExit(1) from exc

        selected_jobs = jobs if not args.job else [
            job for job in jobs if job.id == args.job]
        if args.job and not selected_jobs:
            print(f"No job found matching id: {args.job}", file=sys.stderr)
            raise SystemExit(1)

        program_checks = check_program_dependencies(selected_jobs)
        for check in program_checks:
            state = "OK" if check.available else "MISSING"
            location = f" ({check.location})" if check.location else ""
            print(f"{state}: {check.name}{location}")

        if any(not check.available for check in checks + program_checks):
            raise SystemExit(1)
        print("All required dependencies are available.")
        return

    if args.action == "status":
        if args.limit < 1:
            parser.error("--limit must be greater than zero")
        history_roots = {Path(args.repo_root).expanduser().resolve()}
        config_path = Path(args.config).expanduser()
        if config_path.is_file():
            status_runner = BackupRunner(args.repo_root)
            configured_jobs = load_jobs_from_config(config_path)
            history_roots.update(
                status_runner.repository_root_for(job).resolve()
                for job in configured_jobs
                if args.job is None or job.id == args.job
            )
        records = []
        for history_root in history_roots:
            records.extend(
                RunHistory(history_root).list_runs(
                    job_id=args.job,
                    limit=args.limit,
                )
            )
        records.sort(
            key=lambda record: (
                str(record.get("finished_at", "")),
                str(record.get("run_id", "")),
            ),
            reverse=True,
        )
        records = records[:args.limit]
        if not records:
            print("No backup runs recorded in the configured repositories.")
            return
        print(f"{'FINISHED (UTC)':20} {'JOB':24} {'STATUS':9} {'DURATION':>10}")
        for record in records:
            duration = float(record.get("duration_seconds") or 0)
            print(
                f"{str(record.get('finished_at', '')):20} "
                f"{str(record.get('job_id', '')):24} "
                f"{str(record.get('status', '')):9} "
                f"{duration:9.1f}s"
            )
        return

    from dotenv import load_dotenv

    load_dotenv(args.env_file)
    jobs = load_jobs_from_config(args.config)

    if args.action == "list":
        for job in jobs:
            print(f"{job.id}: {job.name} [{job.source_type}]")
        return

    if args.action == "restore":
        if not args.snapshot or not args.target:
            raise SystemExit(
                "--snapshot and --target are required for restore")
        restore_snapshot(args.snapshot, args.target)
        print(f"Restored snapshot {args.snapshot} to {args.target}")
        return

    runner = BackupRunner(args.repo_root)
    selected_jobs = jobs if not args.job else [
        job for job in jobs if job.id == args.job]
    if not selected_jobs:
        raise SystemExit(f"No job found matching id: {args.job}")

    has_failed_job = False
    for job in selected_jobs:
        started = datetime.now(timezone.utc)
        started_monotonic = monotonic()
        try:
            result = runner.run_job(job)
        except BackupAlreadyRunningError as exc:
            result = _exception_result(
                job, exc, "skipped", started, started_monotonic
            )
        except Exception as exc:
            result = _exception_result(
                job, exc, "failed", started, started_monotonic
            )

        print(f"{job.id}: {result.status} -> {result.message}")
        if result.status != "success":
            has_failed_job = True
        try:
            history = RunHistory(runner.repository_root_for(job))
            history.record(job, result)
        except Exception as exc:
            print(
                f"{job.id}: unable to archive run status ({type(exc).__name__})",
                file=sys.stderr,
            )
            has_failed_job = True

    if has_failed_job:
        raise SystemExit(1)


def _exception_result(
    job: JobConfig,
    exc: Exception,
    status: str,
    started: datetime,
    started_monotonic: float,
) -> BackupResult:
    finished = datetime.now(timezone.utc)
    message = str(exc) if status == "skipped" else (
        f"Backup failed for {job.name} ({type(exc).__name__})"
    )
    return BackupResult(
        job_id=job.id,
        status=status,
        snapshot_path=None,
        started_at=started.isoformat(
            timespec="seconds").replace("+00:00", "Z"),
        finished_at=finished.isoformat(
            timespec="seconds").replace("+00:00", "Z"),
        duration_seconds=monotonic() - started_monotonic,
        message=message,
        metadata={"error_type": type(exc).__name__},
    )


if __name__ == "__main__":
    main()
