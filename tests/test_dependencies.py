from types import SimpleNamespace

from snup.dependencies import (
    check_program_dependencies,
    check_python_dependencies,
    required_programs,
)
from snup.models import JobConfig, NotifierConfig


def test_python_dependency_check_reports_missing_modules(monkeypatch):
    monkeypatch.setattr(
        "snup.dependencies.importlib.util.find_spec",
        lambda module: SimpleNamespace(origin="/installed/yaml.py")
        if module == "yaml" else None,
    )

    results = check_python_dependencies()

    assert next(item for item in results if item.name ==
                "Python package PyYAML").available
    assert not next(
        item for item in results if item.name == "Python package python-dotenv"
    ).available


def test_required_programs_match_job_sources_and_notifiers(monkeypatch):
    monkeypatch.setenv("DISPLAY", ":0")
    jobs = [
        JobConfig(
            id="files",
            name="Files",
            source_type="filesystem",
            source_path="/files",
            transport="ssh",
            notifiers=[NotifierConfig(type="desktop")],
        ),
        JobConfig(
            id="database",
            name="Database",
            source_type="postgres",
            source_path="appdb",
            transport="ssh",
        ),
        JobConfig(
            id="cloud",
            name="Cloud",
            source_type="pcloud",
            source_path="/",
        ),
    ]

    assert required_programs(jobs) == {
        "notify-send", "pg_dump", "rclone", "rsync", "ssh"
    }


def test_program_check_reports_missing_and_available_tools(monkeypatch):
    job = JobConfig(
        id="files",
        name="Files",
        source_type="filesystem",
        source_path="/files",
    )
    monkeypatch.setattr(
        "snup.dependencies.shutil.which",
        lambda program: "/usr/bin/rsync" if program == "rsync" else None,
    )

    results = check_program_dependencies([job])

    assert results == [
        type(results[0])("Program rsync", True, "/usr/bin/rsync")
    ]
