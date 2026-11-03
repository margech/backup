from __future__ import annotations

import argparse

from dotenv import load_dotenv

from .restore import restore_snapshot
from .runner import BackupRunner, load_jobs_from_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Modular backup tool")
    parser.add_argument("action", choices=[
                        "run", "list", "restore"], help="Action to execute")
    parser.add_argument("--config", default="jobs.yaml",
                        help="Path to the YAML job definition file (default: jobs.yaml)")
    parser.add_argument("--env-file", default=".env",
                        help="Path to an environment file (default: .env)")
    parser.add_argument("--job", help="Optional job id to run only one job")
    parser.add_argument("--repo-root", default="./.backup_store",
                        help="Fallback repository root for jobs without destination")
    parser.add_argument("--snapshot", help="Snapshot directory to restore")
    parser.add_argument("--target", help="Restore target directory")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
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
        result = runner.run_job(job)
        print(f"{job.id}: {result.status} -> {result.message}")
        if result.status != "success":
            has_failed_job = True

    if has_failed_job:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
