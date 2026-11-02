from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class NotifierConfig:
    type: str
    on: list[str] = field(default_factory=lambda: ["success", "failure"])
    to: Optional[str] = None
    subject: Optional[str] = None
    title: Optional[str] = None


@dataclass
class JobConfig:
    id: str
    name: str
    source_type: str
    source_path: str
    destination: Optional[str] = None
    notifiers: list[NotifierConfig] = field(default_factory=list)
    schedule: Optional[str] = None
    transport: str = "local"
    remote_host: Optional[str] = None
    remote_user: Optional[str] = None
    source_excludes: list[str] = field(default_factory=list)
    source_includes: list[str] = field(default_factory=list)
    retention: dict[str, int] = field(
        default_factory=lambda: {"daily": 7, "weekly": 4, "monthly": 12})
    cloud_remote: Optional[str] = None
    cloud_path: Optional[str] = None


@dataclass
class BackupResult:
    job_id: str
    status: str
    snapshot_path: Optional[str]
    started_at: str
    finished_at: str
    duration_seconds: float
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)
