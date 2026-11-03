import json

from backup_tool.models import BackupResult, JobConfig, NotifierConfig
from backup_tool.runner import BackupRunner, load_jobs_from_config


def test_load_jobs_from_config_applies_options_and_defaults(tmp_path):
    config_path = tmp_path / "jobs.yaml"
    config_path.write_text(
        """
jobs:
  - id: documents
    source_path: /home/user/Documents
    excludes: [cache]
    includes: ['*.txt']
    retention:
      daily: '3'
    notifiers:
      - type: desktop
        on: [failure]
""",
        encoding="utf-8",
    )

    jobs = load_jobs_from_config(config_path)

    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == "documents"
    assert job.name == "documents"
    assert job.source_type == "filesystem"
    assert job.destination is None
    assert job.source_excludes == ["cache"]
    assert job.source_includes == ["*.txt"]
    assert job.retention == {"daily": 3, "weekly": 4, "monthly": 12}
    assert job.notifiers == [NotifierConfig(type="desktop", on=["failure"])]


def test_run_job_creates_snapshot_manifest_and_dispatches_notification(
    tmp_path, monkeypatch
):
    events = []

    class FakeSource:
        def create_snapshot(self, job, snapshot_dir):
            (snapshot_dir / "backup.txt").write_text("contents", encoding="utf-8")
            return {"file_count": 1}

    class FakeNotifier:
        def send(self, event):
            events.append(event)

    monkeypatch.setattr("backup_tool.runner.create_source",
                        lambda job: FakeSource())
    monkeypatch.setattr("backup_tool.runner.build_notifier",
                        lambda config: FakeNotifier())

    job = JobConfig(
        id="documents",
        name="Documents",
        source_type="filesystem",
        source_path="/unused",
        destination=str(tmp_path / "job-repository"),
        retention={"daily": 0, "weekly": 0, "monthly": 0},
        notifiers=[NotifierConfig(type="desktop", on=["success"])],
    )
    runner = BackupRunner(tmp_path)

    result = runner.run_job(job)

    assert result.status == "success"
    job_repository = tmp_path / "job-repository"
    snapshot = job_repository / "snapshots" / job.id / \
        result.snapshot_path.split("/")[-1]
    assert snapshot.is_dir()
    current_link = job_repository / "snapshots" / job.id / "current"
    assert current_link.is_symlink()
    assert current_link.resolve() == snapshot
    assert (snapshot / "backup.txt").read_text(encoding="utf-8") == "contents"
    manifest = json.loads(
        (snapshot / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["job_id"] == job.id
    assert manifest["metadata"] == {"file_count": 1}
    assert not (job_repository / "backup.lock").exists()
    assert not (tmp_path / "backup.lock").exists()
    assert events == [{
        "job_id": job.id,
        "job_name": job.name,
        "status": "success",
        "message": result.message,
    }]


def test_run_job_failure_removes_temporary_snapshot_and_releases_lock(
    tmp_path, monkeypatch
):
    class FailingSource:
        def create_snapshot(self, job, snapshot_dir):
            (snapshot_dir / "partial.txt").write_text("partial", encoding="utf-8")
            raise RuntimeError("source unavailable")

    monkeypatch.setattr("backup_tool.runner.create_source",
                        lambda job: FailingSource())
    job = JobConfig(
        id="documents",
        name="Documents",
        source_type="filesystem",
        source_path="/unused",
    )

    result = BackupRunner(tmp_path).run_job(job)

    assert result.status == "failed"
    assert result.metadata == {
        "error": "source unavailable",
        "error_type": "RuntimeError",
    }
    assert not list((tmp_path / "snapshots" / job.id).glob("*.tmp"))
    assert not (tmp_path / "backup.lock").exists()


def test_load_jobs_from_config_uses_job_destination(tmp_path):
    config_path = tmp_path / "jobs.yaml"
    config_path.write_text(
        "jobs:\n  - id: documents\n    destination: /backups/documents\n",
        encoding="utf-8",
    )

    jobs = load_jobs_from_config(config_path)

    assert jobs[0].destination == "/backups/documents"


def test_email_notifier_dispatches_through_runner(tmp_path, monkeypatch):
    sent_messages = []

    class FakeSMTP:
        def __init__(self, host, port):
            assert host == "smtp.example.com"
            assert port == 587

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def starttls(self):
            pass

        def login(self, username, password):
            assert username == "backup@example.com"
            assert password == "secret"

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "backup@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setattr("backup_tool.notifiers.smtplib.SMTP", FakeSMTP)

    job = JobConfig(
        id="documents",
        name="Documents",
        source_type="filesystem",
        source_path="/unused",
        notifiers=[NotifierConfig(type="email", to="admin@example.com")],
    )
    result = BackupResult(
        job_id=job.id,
        status="success",
        snapshot_path=None,
        started_at="2026-11-02T00:00:00Z",
        finished_at="2026-11-02T00:00:01Z",
        duration_seconds=1,
        message="Backup successful",
    )

    BackupRunner(tmp_path)._dispatch_notifications(job, result)

    assert len(sent_messages) == 1
    assert sent_messages[0]["To"] == "admin@example.com"
