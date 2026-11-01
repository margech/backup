import pytest

from backup_tool.models import JobConfig
from backup_tool.sources import SOURCE_REGISTRY, create_source
from backup_tool.sources.filesystem import FilesystemSource
from backup_tool.sources.pcloud import PCloudSource
from backup_tool.sources.sql_dump import SqlDumpSource


def make_job(source_type="filesystem", **kwargs):
    return JobConfig(
        id="job",
        name="Job",
        source_type=source_type,
        source_path=kwargs.pop("source_path", "/source"),
        destination="/destination",
        **kwargs,
    )


@pytest.mark.parametrize(
    ("source_type", "module_name", "class_name"),
    [
        ("filesystem", "filesystem", "FilesystemSource"),
        ("postgres", "sql_dump", "SqlDumpSource"),
        ("mysql", "sql_dump", "SqlDumpSource"),
        ("sqlite", "sql_dump", "SqlDumpSource"),
        ("pcloud", "pcloud", "PCloudSource"),
    ],
)
def test_create_source_resolves_module_and_class(source_type, module_name, class_name):
    adapter = create_source(make_job(source_type))

    assert SOURCE_REGISTRY[source_type] == (module_name, class_name)
    assert type(adapter).__module__ == f"backup_tool.sources.{module_name}"
    assert type(adapter).__name__ == class_name


def test_create_source_rejects_unknown_type():
    with pytest.raises(ValueError, match="Unsupported source type: custom"):
        create_source(make_job("custom"))


def test_filesystem_source_builds_local_rsync_command(tmp_path, monkeypatch):
    source_path = tmp_path / "source"
    source_path.mkdir()
    snapshot_dir = tmp_path / "snapshot"
    job = make_job(
        source_path=str(source_path),
        source_excludes=["*.tmp"],
        source_includes=["*.txt"],
    )
    monkeypatch.setattr("backup_tool.sources.filesystem.shutil.which",
                        lambda name: "/usr/bin/rsync")

    command = FilesystemSource()._build_rsync_command(job, snapshot_dir)

    assert command == [
        "/usr/bin/rsync",
        "-a",
        "--delete",
        "--exclude",
        "*.tmp",
        "--include",
        "*.txt",
        f"{source_path.as_posix()}/",
        str(snapshot_dir),
    ]


def test_filesystem_source_requires_remote_host_for_ssh(monkeypatch):
    monkeypatch.setattr("backup_tool.sources.filesystem.shutil.which",
                        lambda name: "/usr/bin/rsync")
    job = make_job(transport="ssh", remote_host=None)

    with pytest.raises(ValueError, match="remote_host is required"):
        FilesystemSource()._build_rsync_command(job, "/snapshot")
