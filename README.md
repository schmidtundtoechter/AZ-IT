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
- [ ] **Backup lokal einspielen** – das Backup in die lokale Site `d-code.localhost` importieren
- [ ] **App-Versionen vergleichen** – alle installierten Apps und deren Versionen/Branches zwischen Remote und lokaler Bench abgleichen
  - Fehlende Apps lokal nachinstallieren
  - Bei Branch-/Versionsabweichungen lokale Bench aktualisieren
  - ⚠️ **Sicherheit:** Auf dem Remote-System darf unter keinen Umständen etwas verändert werden (nur lesender Zugriff)