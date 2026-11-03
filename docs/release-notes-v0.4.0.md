# Snup 0.4.0

Veröffentlicht am 3. November 2026.

Snup 0.4.0 bündelt die rclone-basierte pCloud-Sicherung, geplante Läufe über systemd oder Cron, eine Job-spezifische Laufhistorie und eine Vorabprüfung der benötigten Abhängigkeiten. Außerdem wird das Projekt unter dem Namen Snup ausgeliefert.

## Neu in 0.4.0

- **pCloud über rclone:** Jobs können ein konfiguriertes rclone-Remote und einen Cloud-Pfad verwenden. Die Zugangsdaten bleiben in der rclone-Konfiguration; eine direkte pCloud-API-Integration ist nicht enthalten.
- **Abhängigkeiten prüfen:** `snup check` prüft Python-Version und Laufzeitpakete sowie die Linuxprogramme, die von den konfigurierten Jobs benötigt werden. Mit `--job` kann die Prüfung auf einen Job begrenzt werden.
- **Laufhistorie pro Job:** Jeder Lauf wird als JSON-Datensatz im Repository des Jobs abgelegt. `snup status` zeigt die letzten Läufe; Einträge werden 90 Tage aufbewahrt. Fehlertexte und beliebige Adapter-Metadaten werden nicht in die History übernommen.
- **systemd und Cron:** Beispielkonfigurationen für systemd-Service und Timer, Cron sowie Logrotate sind unter `deploy/` enthalten. Fehlgeschlagene Läufe liefern einen Fehler-Exit-Code; alle ausgewählten Jobs werden zuvor abgearbeitet.
- **Secret-Konfiguration:** Secrets werden aus der Prozessumgebung oder einer externen Env-Datei geladen. Zugangsdaten für rclone, SSH und Datenbankwerkzeuge bleiben bei den jeweiligen Werkzeugen.
- **Neuer Projektname:** Distribution und CLI heißen jetzt `snup`; das Python-Paket wird als `snup` importiert.

## Upgrade-Hinweise

Der Namenswechsel ist inkompatibel mit bisherigen Installationen:

- Python-Importe wechseln von `backup_tool` zu `snup`.
- Das ausführbare Kommando wechselt von `backup-tool` zu `snup`. Installiere die Version 0.4.0 neu, zum Beispiel mit `python -m pip install -e .` im Projektverzeichnis.
- systemd- und Cron-Beispiele verwenden jetzt `snup.service`, `snup.timer`, den Benutzer `snup` sowie Pfade unter `/etc/snup`, `/var/lib/snup` und `/var/log/snup`. Deaktiviere alte `backup-tool`-Timer, bevor du den neuen Timer aktivierst, damit keine doppelten Läufe entstehen.
- Stelle sicher, dass der Benutzer `snup` auf bestehende Job-Konfigurationen, Secret-Dateien, rclone-Remotes, SSH-Schlüssel, Quellen und Backup-Ziele zugreifen kann. Passe Eigentümer und Berechtigungen bei Bedarf an.
- Das Format von `jobs.yaml` bleibt unverändert. Für `snup status` sollte dieselbe `--config`-Datei wie für den Backup-Lauf angegeben werden, damit Historien in individuellen Job-Repositories gefunden werden.

## Voraussetzungen und Grenzen

- Python 3.11 oder neuer sowie die Laufzeitpakete PyYAML und python-dotenv.
- Externe Programme hängen von den konfigurierten Quellen ab, zum Beispiel `rsync`, `ssh`, `pg_dump`, `mysqldump`, `sqlite3` oder `rclone`. `snup check` prüft, ob sie im `PATH` gefunden werden; Verbindungen, Zugangsdaten und Quellpfad-Berechtigungen werden damit nicht getestet.
- Es gibt keinen eingebauten Scheduler. Die zeitgesteuerte Ausführung erfolgt über systemd oder Cron.
- Die Testsuite umfasst 35 bestandene Tests. Bestehende Deprecation-Warnungen zu `datetime.utcnow()` sind davon unberührt.
