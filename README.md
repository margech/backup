# backup

Ein modularer Linux-Backup-Client als Python-Projekt mit Fokus auf Snapshot-basierte Sicherung, Retention, Remote-Quellen und pluggbaren Backends.

Das Projekt ist als Architektur- und Entwicklungsbasis für ein Time-Machine-ähnliches Backup-Tool konzipiert.

## Überblick

- lokale Dateisystem-Quellen mit rsync
- Remote-Quellen über SSH
- SQL-Dump-Quellen (PostgreSQL/MySQL/SQLite)
- pCloud-vorbereiteter Backend-Adapter über rclone
- Snapshot-Mechanik mit temporären Ordnern und Finalisierung
- Retention-Policy für daily/weekly/monthly
- Restore-Funktion
- Locking gegen parallele Backups
- pluggable Notifier (E-Mail, Desktop)

## Versionsstand

- v0.1: erster MVP mit grundlegendem Backup-Runner
- v0.2: Snapshot-Engine, Retention und Restore
- v0.3: SSH- und pCloud-ready Architektur mit Locking

## Projektstruktur

```text
backup/
├── backup_tool/
│   ├── __init__.py
│   ├── lock.py
│   ├── main.py
│   ├── models.py
│   ├── notifiers.py
│   ├── restore.py
│   ├── retention.py
│   ├── runner.py
│   ├── scheduler.py
│   └── sources/
│       ├── __init__.py
│       ├── base.py
│       ├── filesystem.py
│       ├── pcloud.py
│       └── sql_dump.py
├── docs/
│   ├── architecture.md
│   └── roadmap.md
├── examples/
│   └── jobs.yaml
├── tests/
│   ├── test_runner.py
│   ├── test_sources.py
│   └── test_storage.py
├── pyproject.toml
├── README.md
├── requirements.txt
└── LICENSE
```

## Schnellstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quellen erweitern

Jeder Source-Adapter liegt in einem eigenen Modul unter `backup_tool/sources/`. Die Registry in `sources/__init__.py` verknüpft `source_type` mit Moduldatei und Klassenname. Für einen neuen Typ werden daher ein Adapter-Modul, ein Registry-Eintrag und passende Tests ergänzt.

## Beispiel ausführen

```bash
python -m backup_tool.main list --config examples/jobs.yaml
python -m backup_tool.main run --config examples/jobs.yaml --job home-files --repo-root /var/backups/store
python -m backup_tool.main restore --config examples/jobs.yaml --snapshot /var/backups/store/snapshots/home-files/20261031_120000 --target /tmp/restore
```

## Tests

Die Test-Abhängigkeit installieren und die Suite starten:

```bash
pip install -e ".[test]"
python -m pytest
```

## Wichtige Hinweise

- Für lokale Dateisystem-Backups wird `rsync` benötigt.
- Für SQL-Dumps müssen DB-Tools wie `pg_dump`, `mysqldump` oder `sqlite3` installiert sein.
- Für pCloud muss `rclone` installiert und konfiguriert sein.
- Die Notifier laufen nur, wenn die Umgebung dafür geeignet ist.
- Ein integrierter Scheduler ist noch nicht implementiert; geplante Ausführung erfolgt vorerst über systemd oder cron.

## Nächste Schritte

- pCloud-Account-Management pro Nutzer
- sichere Token- und Secret-Konfiguration
- systemd/cron-Integration
- multi-user backup jobs
- zentralisierter Backup-Store mit Laufzeit- und Status-Management
