# AZ-IT Frappe App

Interne Frappe-App für AZ-IT / Schmidt und Töchter.

**Lizenz:** MIT

---

## ToDo

### Backup-Sync-Script (Remote → Lokal)

Ziel: Automatisiertes Script, das ein Backup vom Remote-System holt und lokal einspielt.

- [x] **Backup auslösen** – per SSH auf dem Remote-System (`erp.az-it.systems`) eine Frappe-Sicherung inkl. Files starten (`backup_sync.py`)
  - Bench-Verzeichnis auf dem Remote-System automatisch ermitteln (3 Methoden: Standardpfade, laufender Prozess, `which bench`)
  - Alternativ auch das Testsystem (`erptest.az-it.systems`) unterstützen (Auswahl anbieten)
- [x] **Backup-Dateien herunterladen** – die 4 erzeugten Backup-Dateien (DB, Files, private Files, Config) per `rsync` auf die lokale Maschine übertragen
- [x] **Backup lokal einspielen** – das Backup in die lokale Site `erptest.az-it.localhost` / `erp.az-it.localhost` importieren (`bench restore --force` + `bench migrate`)
- [x] **App-Versionen vergleichen** – alle installierten Apps und deren Versionen zwischen Remote und lokaler Bench abgleichen (`--only-apps`)
  - Fehlende Apps lokal nachinstallieren
  - Bei Versionsabweichungen lokale Bench-Update-Befehle ausgeben
  - ⚠️ **Sicherheit:** Auf dem Remote-System darf unter keinen Umständen etwas verändert werden (nur lesender Zugriff)

---

## Verwendung: `backup_sync.py`

```bash
cd /workspace/development/frappe-bench
source env/bin/activate
python apps/az_it/backup_sync.py [OPTIONEN]
```

| Option | Beschreibung |
|---|---|
| `--system live\|test` | Zielsystem (`live` = erp.az-it.systems, `test` = erptest.az-it.systems). Ohne Angabe: interaktive Auswahl. |
| `--only-apps` | Nur App-Versionen vergleichen und fehlende Apps installieren, dann beenden. |
| `--skip-backup` | Kein neues Backup auslösen – neuestes vorhandenes lokales Backup verwenden. |
| `--skip-download` | Kein Download – setzt `--skip-backup` voraus. |
| `--skip-restore` | Restore und Migrate überspringen. |

**Typische Anwendungsfälle:**

```bash
# Vollständiger Sync (Backup + Download + Restore)
python apps/az_it/backup_sync.py --system test

# Nur App-Versionen prüfen (schnell, kein Backup)
python apps/az_it/backup_sync.py --system test --only-apps

# Letztes Backup nochmal einspielen (kein erneuter Download)
python apps/az_it/backup_sync.py --system test --skip-backup
```
