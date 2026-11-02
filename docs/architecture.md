# Architektur-Entwurf

## Ziel

Das Projekt soll ein modularer, erweiterbarer Backup-Client werden, der mehrere Quelltypen kennt und Snapshot-basierte Historie ohne vollständige Duplikate erzeugt.

## Grundideen

### 1. Job-basierte Architektur

Jeder Backup-Lauf ist ein Job.

Ein Job kapselt:
- Quelle (Dateisystem, SQL, pCloud)
- Transport (local, ssh)
- eigenes Ziel-Repository (`destination`)
- Retention-Policy
- Benachrichtigungen
- Include-/Exclude-Muster

### 2. Snapshot-Mechanik

Ein Backup wird zunächst in einem temporären Ordner erzeugt.

Nach erfolgreichem Lauf wird der Ordner als gültiger Snapshot finalisiert. Dadurch bleiben unvollständige Snapshots nicht sichtbar.
Unter `snapshots/<job-id>/current` wird ein relativer Symlink atomar auf den zuletzt finalisierten Snapshot aktualisiert. Die Retention zählt den Link nicht als Snapshot und behält dessen Ziel.

### 3. Retention-Policy

Die Policy ist separat definiert und arbeitet mit täglichen, wöchentlichen und monatlichen Zeitschnitten.
Sie wird im jeweiligen Job-Repository unter `destination` angewendet. Fehlt dieses Feld, verwendet die CLI `--repo-root` als gemeinsamen Fallback.

### 4. Notifier

Notifikationen sind pluggbar. Es gibt derzeit E-Mail und Desktop-Notification.

### 5. Remote-Transport

Transport wird getrennt von der Quelle behandelt.

- local
- ssh
- pCloud/Cloud-Backends (vorbereitet)

## Quellenmodell

Die folgenden Source-Typen sind vorgesehen:

- filesystem
- ssh (entferntes Dateisystem über rsync/SSH)
- postgres
- mysql
- sqlite
- pcloud

Source-Adapter liegen im Paket `backup_tool/sources/`, jeweils in einem eigenen Modul. `base.py` definiert den gemeinsamen Adapter-Vertrag; `filesystem.py`, `ssh.py`, `sql_dump.py` und `pcloud.py` enthalten die Implementierungen. Die Registry ordnet jeden `source_type` sowohl einem Modul als auch einem Klassennamen zu. `create_source` lädt das Modul und instanziiert die registrierte Klasse.

`source_type: ssh` sichert ein entferntes Dateisystem über rsync und SSH. Datenbankquellen können weiterhin unabhängig davon mit `transport: ssh` konfiguriert werden.

Für eine neue Quelle werden ein Adapter-Modul, ein Registry-Eintrag und passende Tests ergänzt.

## Sicherheits- und Betriebsaspekte

- Locking gegen parallele Backups
- zentrale Logs / Status
- keine Token im Git-Repo
- Secret-Management per Env-Variablen, Secret-File oder Keyring

## Offene Punkte

- echte pCloud-Token-Handling pro Nutzer
- systemd timer / cron integration
- multi-user Job-Konfiguration
- zentralisierte Restore-UI oder CLI
