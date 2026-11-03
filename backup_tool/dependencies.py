from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from dataclasses import dataclass
from typing import Iterable

from .models import JobConfig


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    available: bool
    location: str | None = None


PYTHON_MODULES = (
    ("PyYAML", "yaml"),
    ("python-dotenv", "dotenv"),
)


def check_python_dependencies() -> list[DependencyStatus]:
    current_version = ".".join(str(part) for part in sys.version_info[:3])
    results = [
        DependencyStatus(
            f"Python >=3.11 (detected {current_version})",
            sys.version_info >= (3, 11),
        )
    ]
    for package, module in PYTHON_MODULES:
        try:
            spec = importlib.util.find_spec(module)
        except (ImportError, ValueError):
            spec = None
        results.append(
            DependencyStatus(
                f"Python package {package}",
                spec is not None,
                spec.origin if spec is not None else None,
            )
        )
    return results


def required_programs(jobs: Iterable[JobConfig]) -> set[str]:
    programs = set()
    has_desktop_notifier = False

    for job in jobs:
        source_type = job.source_type.lower()
        transport = (job.transport or "local").lower()

        if source_type in {"filesystem", "ssh"}:
            programs.add("rsync")
        if source_type == "ssh" or (
            source_type == "filesystem" and transport == "ssh"
        ):
            programs.add("ssh")
        if source_type == "postgres":
            programs.add("pg_dump")
        elif source_type == "mysql":
            programs.add("mysqldump")
        elif source_type == "sqlite":
            programs.add("sqlite3")
        elif source_type == "pcloud":
            programs.add("rclone")

        if source_type in {"postgres", "mysql"} and transport == "ssh":
            programs.add("ssh")

        has_desktop_notifier |= any(
            notifier.type.lower() == "desktop" for notifier in job.notifiers
        )

    if has_desktop_notifier and os.environ.get("DISPLAY"):
        programs.add("notify-send")
    return programs


def check_program_dependencies(jobs: Iterable[JobConfig]) -> list[DependencyStatus]:
    results = []
    for program in sorted(required_programs(jobs)):
        location = shutil.which(program)
        results.append(
            DependencyStatus(
                f"Program {program}",
                location is not None,
                location,
            )
        )
    return results
