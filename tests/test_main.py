import os
from types import SimpleNamespace

import pytest

from backup_tool.main import main


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


def test_main_exits_nonzero_when_backup_fails(monkeypatch):
    monkeypatch.setattr("sys.argv", ["backup-tool", "run"])
    processed_jobs = []
    backup_results = iter([
        SimpleNamespace(status="failed", message="backup failed"),
        SimpleNamespace(status="success", message="backup successful"),
    ])

    def run_job(job):
        processed_jobs.append(job.id)
        return next(backup_results)

    jobs = [SimpleNamespace(id="first"), SimpleNamespace(id="second")]
    monkeypatch.setattr(
        "backup_tool.main.load_jobs_from_config",
        lambda config_path: jobs,
    )
    monkeypatch.setattr(
        "backup_tool.main.BackupRunner",
        lambda repo_root: SimpleNamespace(
            run_job=run_job
        ),
    )

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 1
    assert processed_jobs == ["first", "second"]
