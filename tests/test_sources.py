import pytest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from snup.models import JobConfig
from snup.sources import SOURCE_REGISTRY, create_source
from snup.sources.filesystem import FilesystemSource
from snup.sources.pcloud import PCloudSource
from snup.sources.sql_dump import SqlDumpSource
from snup.sources.ssh import SSHSource


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
        ("ssh", "ssh", "SSHSource"),
        ("postgres", "sql_dump", "SqlDumpSource"),
        ("mysql", "sql_dump", "SqlDumpSource"),
        ("sqlite", "sql_dump", "SqlDumpSource"),
        ("pcloud", "pcloud", "PCloudSource"),
    ],
)
def test_create_source_resolves_module_and_class(source_type, module_name, class_name):
    adapter = create_source(make_job(source_type))

    assert SOURCE_REGISTRY[source_type] == (module_name, class_name)
    assert type(adapter).__module__ == f"snup.sources.{module_name}"
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
    monkeypatch.setattr("snup.sources.filesystem.shutil.which",
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
    monkeypatch.setattr("snup.sources.filesystem.shutil.which",
                        lambda name: "/usr/bin/rsync")
    job = make_job(transport="ssh", remote_host=None)

    with pytest.raises(ValueError, match="remote_host is required"):
        FilesystemSource()._build_rsync_command(job, "/snapshot")


def test_ssh_source_runs_rsync_with_remote_path_and_metadata(tmp_path, monkeypatch):
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir()
    run = Mock(return_value=SimpleNamespace(
        returncode=0, stderr="", stdout=""))
    monkeypatch.setattr("snup.sources.filesystem.shutil.which",
                        lambda name: "/usr/bin/rsync")
    monkeypatch.setattr("snup.sources.filesystem.subprocess.run", run)
    job = make_job(
        "ssh",
        transport="local",
        remote_host="backup.example.com",
        remote_user="backup",
        source_path="/srv/files",
    )

    metadata = SSHSource().create_snapshot(job, snapshot_dir)

    command = run.call_args.args[0]
    assert "-e" in command
    assert "ssh -o StrictHostKeyChecking=no" in command
    assert "backup@backup.example.com:/srv/files/" in command
    assert metadata["source_type"] == "ssh"
    assert metadata["transport"] == "ssh"


def test_ssh_source_requires_remote_host():
    job = make_job("ssh")

    with pytest.raises(ValueError, match="remote_host is required for SSH source"):
        SSHSource().create_snapshot(job, Path("/snapshot"))


def test_pcloud_source_uses_configured_rclone_remote(tmp_path, monkeypatch):
    run = Mock(return_value=SimpleNamespace(
        returncode=0, stderr="", stdout=""))
    monkeypatch.setattr("snup.sources.pcloud.shutil.which",
                        lambda name: "/usr/bin/rclone")
    monkeypatch.setattr("snup.sources.pcloud.subprocess.run", run)
    job = make_job("pcloud", cloud_remote="personal", cloud_path="/Documents")
    snapshot_dir = tmp_path / "snapshot"

    metadata = PCloudSource().create_snapshot(job, snapshot_dir)

    assert run.call_args.args[0] == [
        "/usr/bin/rclone",
        "sync",
        "personal:/Documents",
        str(snapshot_dir / "Documents"),
    ]
    assert metadata["cloud_remote"] == "personal"
    assert metadata["cloud_path"] == "/Documents"


def test_pcloud_source_uses_remote_name_for_cloud_root(tmp_path, monkeypatch):
    run = Mock(return_value=SimpleNamespace(
        returncode=0, stderr="", stdout=""))
    monkeypatch.setattr("snup.sources.pcloud.shutil.which",
                        lambda name: "/usr/bin/rclone")
    monkeypatch.setattr("snup.sources.pcloud.subprocess.run", run)
    job = make_job("pcloud", cloud_remote="personal", cloud_path="/")
    snapshot_dir = tmp_path / "snapshot"

    PCloudSource().create_snapshot(job, snapshot_dir)

    assert run.call_args.args[0][-1] == str(snapshot_dir / "personal")
