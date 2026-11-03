import json
import os
from datetime import datetime, timezone

from snup.models import BackupResult, JobConfig
from snup.run_history import RunHistory


def make_job(job_id="documents"):
    return JobConfig(
        id=job_id,
        name="Documents",
        source_type="filesystem",
        source_path="/source",
    )


def make_result(status="success", finished_at="2026-11-03T02:00:01Z"):
    return BackupResult(
        job_id="documents",
        status=status,
        snapshot_path="/backups/documents/snapshot",
        started_at="2026-11-03T02:00:00Z",
        finished_at=finished_at,
        duration_seconds=1,
        message="Backup result",
        metadata={"error": "token=must-not-be-saved"},
    )


def test_record_writes_private_atomic_history_without_error_details(tmp_path):
    history = RunHistory(tmp_path)

    record_path = history.record(make_job(), make_result("failed"))

    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["status"] == "failed"
    assert record["error_type"] == "BackupError"
    assert "message" not in record
    assert "must-not-be-saved" not in record_path.read_text(encoding="utf-8")
    assert os.stat(record_path).st_mode & 0o777 == 0o600
    assert os.stat(record_path.parent).st_mode & 0o777 == 0o700
    assert os.stat(record_path.parent.parent).st_mode & 0o777 == 0o700
    assert os.stat(record_path.parent.parent.parent).st_mode & 0o777 == 0o700
    assert os.stat(
        record_path.parent.parent.parent.parent).st_mode & 0o777 == 0o700
    assert record_path.parent.parent.parent.name == "documents"
    assert not list(record_path.parent.glob("*.tmp"))


def test_list_runs_filters_by_job_and_returns_newest_first(tmp_path):
    history = RunHistory(tmp_path)
    history.record(make_job(), make_result())
    second_result = make_result(finished_at="2026-11-04T02:00:01Z")
    history.record(make_job(), second_result)
    history.record(
        JobConfig(id="photos", name="Photos",
                  source_type="filesystem", source_path="/photos"),
        BackupResult(
            job_id="photos",
            status="success",
            snapshot_path=None,
            started_at="2026-11-04T02:00:00Z",
            finished_at="2026-11-04T02:00:01Z",
            duration_seconds=1,
            message="Backup successful",
        ),
    )

    all_runs = history.list_runs(limit=10)
    documents_runs = history.list_runs(job_id="documents", limit=10)

    assert len(all_runs) == 3
    assert all_runs[0]["finished_at"] == "2026-11-04T02:00:01Z"
    assert [run["job_id"] for run in documents_runs] == [
        "documents", "documents"
    ]
    assert all(
        path.parent.parent.parent.name == "documents"
        for path in (history.directory / "documents").rglob("*.json")
    )
    assert list((history.directory / "photos").rglob("*.json"))


def test_record_prunes_entries_older_than_retention(tmp_path):
    history = RunHistory(tmp_path)
    old_record = history.record(
        make_job(), make_result(finished_at="2026-01-01T00:00:01Z")
    )
    old_timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
    os.utime(old_record, (old_timestamp, old_timestamp))

    history.record(make_job(), make_result())

    assert not old_record.exists()
