# backup

Ein modularer Linux-Backup-Client als Python-Projekt mit Fokus auf Snapshot-basierte Sicherung, Retention, Remote-Quellen und pluggbaren Backends.

Das Projekt ist als Architektur- und Entwicklungsbasis für ein Time-Machine-ähnliches Backup-Tool konzipiert.

## Überblick

- lokale Dateisystem-Quellen mit rsync
- SSH-Quellen für entfernte Dateisysteme über rsync
- SQL-Dumps auch über SSH-Transport
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
│       ├── ssh.py
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

Virtuelle Umgebungen sind nicht verschiebbar. Erstelle `.venv` daher direkt in diesem Projektverzeichnis und kopiere sie nicht aus einem anderen Checkout.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Quellen erweitern

Jeder Source-Adapter liegt in einem eigenen Modul unter `backup_tool/sources/`. Die Registry in `sources/__init__.py` verknüpft `source_type` mit Moduldatei und Klassenname. Für einen neuen Typ werden daher ein Adapter-Modul, ein Registry-Eintrag und passende Tests ergänzt. Für entfernte Dateisysteme kann `source_type: ssh` mit `remote_host`, optional `remote_user` und dem Remote-`source_path` verwendet werden.

Beispiel für einen SSH-Job:

```yaml
jobs:
	- id: remote-files
		name: Remote Files
		source_type: ssh
		source_path: /srv/files
		transport: ssh
		remote_host: backup01.example.com
		remote_user: backupuser
		source_excludes:
			- cache/**
		retention:
			daily: 7
			weekly: 4
			monthly: 12
```

## Beispiel ausführen

Kopiere die Beispielkonfiguration ins Hauptverzeichnis. Dort werden standardmäßig sowohl `jobs.yaml` als auch `.env` gesucht:

```bash
cp examples/jobs.yaml jobs.yaml
python -m backup_tool.main list
python -m backup_tool.main run --job home-files
python -m backup_tool.main restore --snapshot /var/backups/home-files/snapshots/home-files/20261031_120000 --target /tmp/restore
```

Mit `--config /pfad/zur/jobs.yaml` kann eine andere Konfigurationsdatei angegeben werden.
Jeder Job kann mit `destination` sein eigenes Repository-Verzeichnis erhalten. Snapshots liegen darunter unter `snapshots/<job-id>/<zeitstempel>`. Der relative Symlink `snapshots/<job-id>/current` zeigt nach einem erfolgreichen Lauf auf den neuesten Snapshot. Fehlt `destination`, wird `--repo-root` verwendet (Standard: `./.backup_store`). Relative Job-Ziele beziehen sich auf das aktuelle Arbeitsverzeichnis.

## Tests

Die Test-Abhängigkeit installieren und die Suite starten:

```bash
pip install -e ".[test]"
python -m pytest
```

## E-Mail-Benachrichtigungen

Empfänger und Ereignisse werden pro Job in `examples/jobs.yaml` unter `notifiers` konfiguriert. Das CLI lädt standardmäßig `.env` aus dem aktuellen Arbeitsverzeichnis. Alternativ kann die Datei mit `--env-file` angegeben werden. Bereits in der Prozessumgebung gesetzte Werte haben Vorrang.

Kopiere die Vorlage ins Hauptverzeichnis, setze dort deine Zugangsdaten ein und beschränke die Dateirechte:

```bash
cp examples/.env.example .env
chmod 600 .env
```

Danach kann das Backup ohne vorheriges manuelles Exportieren gestartet werden:

```bash
python -m backup_tool.main run
```

Eine alternative Env-Datei lässt sich explizit setzen: `python -m backup_tool.main run --env-file /etc/backup-tool/backup.env`. Nach einer Installation mit `pip install -e .` kann stattdessen auch das Kommando `backup-tool` verwendet werden.

- `SMTP_HOST`: SMTP-Server. Ohne diese Variable wird die E-Mail still übersprungen.
- `SMTP_USER` und `SMTP_PASSWORD`: Werden nur gemeinsam verwendet. Sind beide gesetzt, aktiviert der Notifier STARTTLS und meldet sich an.
- `SMTP_FROM`: Absenderadresse; Standard ist `SMTP_USER` oder `backup@example.com`.
- Der SMTP-Port ist derzeit fest auf `587` gesetzt; eine Variable `SMTP_PORT` wird nicht ausgewertet.

Die Werte werden beim CLI-Start in die Prozessumgebung geladen. Datenbank-Tools erhalten diese Umgebung ebenfalls: PostgreSQL verwendet beispielsweise seine üblichen `PG*`-Variablen, MySQL seine unterstützten `MYSQL_*`-Variablen. SSH verwendet Schlüssel oder Agent.

### pCloud mit rclone

Richte das Remote einmalig interaktiv ein:

```bash
rclone config
```

Im Dialog:

1. `n` für ein neues Remote wählen.
2. Einen Namen vergeben, zum Beispiel `pcloud`.
3. Als Storage `Pcloud` auswählen.
4. Client-ID und Client-Secret leer lassen, sofern du keine eigene pCloud-App verwendest.
5. Die erweiterten Einstellungen überspringen und die automatische Anmeldung im Browser bestätigen.
6. Im Browser bei pCloud anmelden, den Zugriff erlauben und das Remote im Dialog speichern.

rclone führt dabei die OAuth-Anmeldung aus und speichert das Token in seiner Konfiguration. Prüfe den Zugriff zum Beispiel so:

```bash
rclone lsf pcloud:/Documents
```

Im Job muss `cloud_remote` exakt dem vergebenen rclone-Remote-Namen entsprechen. Bei einem anderen Namen, etwa `mein-pcloud`, muss auch `cloud_remote: mein-pcloud` gesetzt werden:

```yaml
source_type: pcloud
cloud_remote: pcloud
cloud_path: /Documents
```

Die Zugangsdaten bleiben in der rclone-Konfiguration und gehören nicht in `.env` oder `jobs.yaml`. Für weitere Konten kannst du weitere Remotes einrichten und den jeweiligen Namen in `cloud_remote` eintragen.
Der lokale Snapshot-Unterordner erhält den Namen des letzten Teils von `cloud_path` (zum Beispiel `Documents` bei `/Documents`). Wird die Cloud-Wurzel gesichert, wird stattdessen der rclone-Remote-Name verwendet.

Fehlt der Empfänger `to` im Job, wird ebenfalls keine E-Mail gesendet. Sind `SMTP_USER` oder `SMTP_PASSWORD` nicht beide gesetzt, sendet der aktuelle Code ohne Authentifizierung und ohne STARTTLS. SMTP-Fehler werden abgefangen und nicht angezeigt; sie verhindern daher den Backup-Lauf nicht, sind aber auch nicht direkt sichtbar.

Desktop-Benachrichtigungen benötigen eine gesetzte Variable `DISPLAY` und das Programm `notify-send`. Fehlt eine der Voraussetzungen, wird die Benachrichtigung still übersprungen.

## Geplante Ausführung

Die CLI führt pro Aufruf einen einmaligen Backup-Lauf aus. Die Beispiele unter `deploy/` lassen diesen Aufruf entweder durch systemd oder Cron starten; aktiviere für dieselben Jobs nicht beide Varianten gleichzeitig. Ein fehlgeschlagener Job führt nach Abschluss der übrigen ausgewählten Jobs zu einem Exit-Code ungleich null.

Jeder Jobversuch wird nach Job-ID getrennt als JSON-Datensatz im Repository des Jobs gespeichert: bei gesetztem `destination` unter `<destination>/run-history/<job-id>/`, andernfalls unter `<repo-root>/run-history/<job-id>/`. Erfolgreiche, fehlgeschlagene und wegen eines bestehenden Locks übersprungene Läufe sind enthalten.

```bash
python -m backup_tool.main status
python -m backup_tool.main status --config /etc/backup-tool/jobs.yaml --job home-files --limit 10
```

`status` liest dieselbe Job-Konfiguration wie `run`, um die einzelnen Repository-Pfade zu finden. Verwende bei einer abweichenden Konfiguration dieselbe `--config`-Datei für beide Aufrufe. `--repo-root` gilt für Jobs ohne `destination`. Das Archiv bewahrt die letzten 90 Tage auf. Dateien erhalten Modus `0600`, die History-Verzeichnisse Modus `0700`. Es werden keine Fehlertexte oder beliebigen Adapter-Metadaten archiviert; der Fehlertyp bleibt für die Diagnose erhalten. Detaillierte Prozessausgaben stehen weiterhin im systemd-Journal beziehungsweise im Cron-Log.

Die Beispiele verwenden `/opt/backup-tool/.venv/bin/backup-tool`, `/etc/backup-tool/jobs.yaml`, `/etc/backup-tool/backup.env` und `/var/lib/backup-tool` als Beispielpfade. Passe diese Pfade in den Dateien unter `deploy/` an deine Installation an. Der systemd-Service erlaubt Schreibzugriffe auf `/var/lib/backup-tool` und `/var/backups`; ergänze `ReadWritePaths` in `deploy/systemd/backup-tool.service` für alle weiteren Job-Ziele.

Der Dienst läuft als Systembenutzer `backup`. Lege Konfiguration und Verzeichnisse an und gib dem Benutzer Zugriff auf Quellen, Ziele und benötigte Programme:

```bash
sudo install -d -o root -g backup -m 0750 /etc/backup-tool
sudo install -d -o backup -g backup -m 0750 /var/lib/backup-tool /var/log/backup-tool
sudo install -o root -g backup -m 0640 jobs.yaml /etc/backup-tool/jobs.yaml
sudo install -o backup -g backup -m 0600 .env /etc/backup-tool/backup.env
```

SSH-Schlüssel, `known_hosts` und rclone-Remotes müssen für denselben Benutzer `backup` eingerichtet sein. Für rclone lässt sich die Konfiguration beispielsweise mit `sudo -u backup rclone config` einrichten. Ein Login-`ssh-agent` steht einem geplanten Lauf nicht automatisch zur Verfügung.

### systemd

Installiere die Unit-Dateien, lade die systemd-Konfiguration neu und teste zunächst den Dienst manuell:

```bash
sudo install -m 0644 deploy/systemd/backup-tool.service deploy/systemd/backup-tool.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start backup-tool.service
sudo systemctl enable --now backup-tool.timer
```

Der Timer startet täglich um 02:00 Uhr, mit bis zu 15 Minuten zufälliger Verzögerung. `Persistent=true` lässt einen verpassten Termin nach einem ausgeschalteten Rechner nachholen. Prüfe Zeitplan und Laufprotokolle mit `systemctl list-timers backup-tool.timer` und `journalctl -u backup-tool.service`. Die Service-Unit hat kein Laufzeitlimit; setze `TimeoutStartSec` auf einen passenden Maximalwert, wenn ein solcher gewünscht ist.

### Cron

Installiere Logrotation und füge den Inhalt von `deploy/cron/backup-tool.crontab` mit `sudo -u backup crontab -e` in die bestehende Crontab des Benutzers `backup` ein. Die Beispieldatei ist für eine Benutzer-Crontab gedacht und enthält keine Benutzer-Spalte. Sie verwendet `/usr/bin/flock`, damit überlappende Aufrufe übersprungen werden.

```bash
sudo install -m 0644 deploy/logrotate/backup-tool /etc/logrotate.d/backup-tool
```

Die Cron-Ausgabe wird nach `/var/log/backup-tool/cron.log` geschrieben und wöchentlich rotiert. Stelle sicher, dass der Cron-Daemon läuft und `/usr/bin/flock` installiert ist. Cron holt verpasste Läufe nach einem ausgeschalteten Rechner nicht nach. Fehler werden vom Programm mit einem Fehler-Exit-Code gemeldet und stehen in der Logdatei; für Benachrichtigungen können die vorhandenen Notifier verwendet werden.

## Wichtige Hinweise

- Für lokale Dateisystem-Backups wird `rsync` benötigt.
- Für SSH-Quellen müssen `rsync` und SSH installiert sein; der konfigurierte Host muss erreichbar sein.
- Für SQL-Dumps müssen DB-Tools wie `pg_dump`, `mysqldump` oder `sqlite3` installiert sein.
- Für pCloud muss `rclone` installiert und das in `cloud_remote` genannte Remote konfiguriert sein.
- Die Notifier laufen nur, wenn die Umgebung dafür geeignet ist.
- Ein integrierter Scheduler ist nicht implementiert; geplante Ausführung erfolgt über systemd oder cron.

## Nächste Schritte

- pCloud-Account-Management pro Nutzer
- sichere Token- und Secret-Konfiguration
- multi-user backup jobs
- zentralisierter Backup-Store mit Laufzeit- und Status-Management
