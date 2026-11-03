import os
from types import SimpleNamespace

import pytest

from backup_tool.models import BackupResult, JobConfig
from backup_tool.main import main
from backup_tool.run_history import RunHistory
from backup_tool.runner import BackupAlreadyRunningError


def test_main_loads_env_file_before_command(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "SMTP_PASSWORD=loaded-from-file\n", encoding="utf-8"
    )
    config_path = tmp_path / "jobs.yaml"
    config_path.write_text("jobs: []\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["backup-tool", "list"],
    )

    main()

    assert os.environ["SMTP_PASSWORD"] == "loaded-from-file"


def test_main_archives_all_results_and_exits_nonzero_on_failure(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["backup-tool", "run"])
    processed_jobs = []
    backup_results = iter([
        BackupResult(
            job_id="first",
            status="failed",
            snapshot_path=None,
            started_at="2026-11-03T02:00:00Z",
            finished_at="2026-11-03T02:00:01Z",
            duration_seconds=1,
            message="backup failed",
            metadata={"error": "token=must-not-be-saved"},
        ),
        BackupResult(
            job_id="second",
            status="success",
            snapshot_path="/backups/second/snapshot",
            started_at="2026-11-03T02:01:00Z",
            finished_at="2026-11-03T02:01:01Z",
            duration_seconds=1,
            message="backup successful",
        ),
    ])

    def run_job(job):
        processed_jobs.append(job.id)
        return next(backup_results)

    jobs = [
        JobConfig(id="first", name="First",
                  source_type="filesystem", source_path="/first",
                  destination=str(tmp_path / "first-repository")),
        JobConfig(id="second", name="Second",
                  source_type="filesystem", source_path="/second",
                  destination=str(tmp_path / "second-repository")),
    ]
    monkeypatch.setattr(
        "backup_tool.main.load_jobs_from_config",
        lambda config_path: jobs,
    )
    monkeypatch.setattr(
        "backup_tool.main.BackupRunner",
        lambda repo_root: SimpleNamespace(
            run_job=run_job,
            repository_root_for=lambda job: job.destination or (
                tmp_path / ".backup_store"
            ),
        ),
    )

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 1
    assert processed_jobs == ["first", "second"]
    first_records = RunHistory(
        tmp_path / "first-repository").list_runs()
    second_records = RunHistory(
        tmp_path / "second-repository").list_runs()
    assert first_records[0]["status"] == "failed"
    assert first_records[0]["error_type"] == "BackupError"
    assert second_records[0]["status"] == "success"
    assert "must-not-be-saved" not in str(first_records + second_records)


def test_main_archives_lock_conflict_as_skipped(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["backup-tool", "run"])
    job = JobConfig(
        id="documents",
        name="Documents",
        source_type="filesystem",
        source_path="/documents",
    )
    monkeypatch.setattr(
        "backup_tool.main.load_jobs_from_config",
        lambda config_path: [job],
    )

    def run_job(selected_job):
        raise BackupAlreadyRunningError("backup already running")

    monkeypatch.setattr(
        "backup_tool.main.BackupRunner",
        lambda repo_root: SimpleNamespace(
            run_job=run_job,
            repository_root_for=lambda selected_job: tmp_path / ".backup_store",
        ),
    )

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 1
    record = RunHistory(tmp_path / ".backup_store").list_runs()[0]
    assert record["status"] == "skipped"
    assert record["error_type"] == "BackupAlreadyRunningError"


def test_status_lists_history_without_loading_job_config(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    state_dir = tmp_path / "state"
    job = JobConfig(
        id="documents",
        name="Documents",
        source_type="filesystem",
        source_path="/documents",
    )
    result = BackupResult(
        job_id=job.id,
        status="success",
        snapshot_path="/backups/documents/snapshot",
        started_at="2026-11-03T02:00:00Z",
        finished_at="2026-11-03T02:00:01Z",
        duration_seconds=1,
        message="Backup successful",
    )
    RunHistory(state_dir).record(job, result)
    monkeypatch.setattr(
        "sys.argv",
        ["backup-tool", "status", "--repo-root",
            str(state_dir), "--job", "documents"],
    )
    monkeypatch.setattr(
        "backup_tool.main.load_jobs_from_config",
        lambda config_path: pytest.fail("status must not load jobs.yaml"),
    )

    main()

    output = capsys.readouterr().out
    assert "documents" in output
    assert "success" in output


def test_status_reads_histories_from_configured_job_repositories(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    first_job = JobConfig(
        id="documents",
        name="Documents",
        source_type="filesystem",
        source_path="/documents",
        destination=str(tmp_path / "documents-repository"),
    )
    second_job = JobConfig(
        id="photos",
        name="Photos",
        source_type="filesystem",
        source_path="/photos",
        destination=str(tmp_path / "photos-repository"),
    )
    for job in (first_job, second_job):
        RunHistory(job.destination).record(
            job,
            BackupResult(
                job_id=job.id,
                status="success",
                snapshot_path=None,
                started_at="2026-11-03T02:00:00Z",
                finished_at="2026-11-03T02:00:01Z",
                duration_seconds=1,
                message="Backup successful",
            ),
        )
    config_path = tmp_path / "jobs.yaml"
    config_path.write_text(
        "jobs:\n"
        f"  - id: documents\n    destination: {first_job.destination}\n"
        "    source_path: /documents\n"
        f"  - id: photos\n    destination: {second_job.destination}\n"
        "    source_path: /photos\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        ["backup-tool", "status", "--config",
            str(config_path), "--limit", "10"],
    )

    main()

    output = capsys.readouterr().out
    assert "documents" in output
    assert "photos" in output
