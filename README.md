# backup

Ein erster, modularer Backup-Tool-Prototyp für Linux mit:

- Dateisystem-Backups auf Basis von rsync
- SQL-Dump-Quellen (PostgreSQL/MySQL/SQLite als Basis)
- pluggable Source-Adapter für zukünftige Quellen
- pluggable Notifier (E-Mail, Desktop-Notification)
- Retention/restore-Ansatz als Grundlage für spätere Erweiterungen

Das Projekt ist bewusst als MVP gestaltet: Es kann funktionieren, aber es ist noch kein vollwertiger Time-Machine-Clone.

## Ziel

Das Tool soll als modulare Grundlage dienen für:

- lokale Backups
- SSH/Remote-Quellen
- SQL-Dumps
- später pCloud/Cloud-Backends
- automatisierte Benachrichtigungen

## Architektur

- backup_tool/sources.py: Adapter für Quellen (Dateisystem, SQL, pCloud placeholder)
- backup_tool/notifiers.py: E-Mail- und Desktop-Notifier
- backup_tool/runner.py: startet Backup-Jobs und verwaltet Status
- backup_tool/models.py: Datamodelle
- backup_tool/main.py: CLI-Einstieg

## Schnellstart

1. Installieren:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Beispiel-Jobdatei anlegen:

```bash
mkdir -p examples
cp examples/jobs.yaml examples/jobs.yaml
```

3. Backup ausführen:

```bash
python -m backup_tool.main run --config examples/jobs.yaml --job home-files
```

4. Alle Jobs ausführen:

```bash
python -m backup_tool.main run --config examples/jobs.yaml
```

## Beispiel-Konfiguration

```yaml
jobs:
  - id: home-files
    name: Home Files
    source_type: filesystem
    source_path: /home/user
    destination: /var/backups/home-files
    notifiers:
      - type: email
        to: admin@example.com
        on: [success, failure]
      - type: desktop
        on: [success, failure]
```

## Wichtige Hinweise

- Das Projekt erwartet einen funktionierenden `rsync`-Befehl auf Linux.
- Für SQL-Backups müssen die jeweiligen CLI-Tools installiert sein (`pg_dump`, `mysqldump`, `sqlite3`).
- pCloud ist in dieser ersten Version als Platzhalter geplant; ein echter Adapter kann später ergänzt werden.
- E-Mail- und Desktop-Notifikationen sind pluggbar und greifen nur aus, wenn die Umgebung dafür geeignet ist.

## Nächste Schritte

- Remote-SSH-Quellen ergänzen
- Retention-Policy umsetzen
- pCloud-Adapter implementieren
- Restore-Workflow ergänzen
- Job-Status und Log-Archiv erweitern
