import os

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
