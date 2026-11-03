# Roadmap

## v0.1

- erster MVP
- Dateisystem-Backups per rsync
- einfache SQL-Dump-Adapter
- CLI-Lauf

## v0.2

- Snapshot-Logik
- Retention-Policy
- Restore-Funktion
- Include-/Exclude-Muster

## v0.3

- remote SSH sources via a dedicated adapter module
- lockfile protection
- pCloud-ready backend
- robustere Job-Architektur mit separaten Source-Modulen und Modul-/Klassen-Registry

## v0.4 (in Arbeit)

- [x] pCloud-Zugriff über konfigurierte rclone-Remotes
- [x] sichere Secret-Management-Architektur
- [x] systemd und cron-Integration
- Status-/Log-Archiv
- Prüfung, ob alle Pythonpakete und alle Linuxprogramme vorhenden sind, die für das Backup-Tool benötigt werden.

## v0.5 (geplant)

- bessere Restore-UI/CLI
- optionales Web-Frontend oder Dashboard
- automatisches Monitoring
- erweiterte Retention-Strategien

## Weitere zukünftige Features

- technische Prüfung der Zugriffsrechte von Secret-Dateien
- direkte pCloud-API-Integration
