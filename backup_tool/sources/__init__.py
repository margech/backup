from __future__ import annotations

from importlib import import_module

from ..models import JobConfig
from .base import SourceAdapter

SOURCE_REGISTRY: dict[str, tuple[str, str]] = {
    "filesystem": ("filesystem", "FilesystemSource"),
    "postgres": ("sql_dump", "SqlDumpSource"),
    "mysql": ("sql_dump", "SqlDumpSource"),
    "sqlite": ("sql_dump", "SqlDumpSource"),
    "pcloud": ("pcloud", "PCloudSource"),
}


def create_source(job: JobConfig) -> SourceAdapter:
    source_type = (job.source_type or "").lower()
    try:
        module_name, class_name = SOURCE_REGISTRY[source_type]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported source type: {job.source_type}") from exc

    module = import_module(f"{__name__}.{module_name}")
    adapter_class = getattr(module, class_name)
    return adapter_class()
