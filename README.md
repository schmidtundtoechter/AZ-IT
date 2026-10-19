# AZ-IT Frappe App

Interne Frappe-App für AZ-IT / Schmidt und Töchter.

**Lizenz:** MIT

## Dokumentation und Änderungsverlauf

Der vollständige [Bestand und Änderungsverlauf](CHANGELOG.md) dokumentiert alle
Skripte, Custom Fields, Property Setter und Felder eigener DocTypes.
Diese Dokumentation wird bei jeder Änderung mitgepflegt; der Pflegeablauf steht
in [AGENTS.md](AGENTS.md).

## Versionierung und lokale Entwicklung

Die Version steht ausschließlich in `az_it/__init__.py`; Flit liest sie dort aus.
Der Ausgangsstand auf `main` ist **0.5.0**. Nach einem Push auf `main` erhöht
GitHub Actions die Patch-Zahl um die Anzahl neuer Commits auf der ersten
Elternlinie seit der letzten Änderung der Versionsdatei: 0.5.1, 0.5.2 usw.
Ein Merge- oder Squash-Commit auf `main` zählt als eine Änderung. Mehrere
Commits in einem Push werden zusammen gezählt. Bloßes Speichern lokaler Dateien
erhöht die veröffentlichte Version noch nicht.

Der Workflow `.github/workflows/version.yml` schreibt dafür einen zusätzlichen
Commit. Wiederholungen ohne neue Änderungen erhöhen die Version nicht erneut.
Manuelle Minor-/Major-Releases durch Änderung von `__version__` bilden einen
neuen Ausgangspunkt. Die Versionsdatei deshalb nur für solche Releases ändern.
GitHub Actions muss aktiviert sein und mit `contents: write` auf `main` schreiben
dürfen; Branch-Regeln müssen diesen Push erlauben.

```powershell
git pull --rebase origin main
# Änderungen bearbeiten und prüfen
git add <geänderte-Dateien>
git commit -m "Beschreibung der Änderung"
git push origin main
# Nach Abschluss des Versions-Workflows den Versionscommit lokal holen:
git pull --rebase origin main
```

## Skriptbestand

`SCRIPT_INVENTORY.csv` enthält alle exportierten Client-/Server-Script-Datensätze
und sämtliche Python-, JavaScript- und Shell-Dateien (ohne leere Paketinitialisierungen).
Aktueller dokumentierter Stand: 19.10.2026. Alle 13 enthaltenen Client Scripts sind
aktiviert; alle 10 Server Scripts haben `disabled=0`.
Die beiden Client Scripts `Internal Customer Series` und
`Kunde - automatische Kundennummer` wurden aus Fixtures und Export-Auswahl entfernt.
Bei Neuinstallationen werden sie nicht angelegt; bereits vorhandene Einträge
werden auf bestehenden Sites vom Administrator manuell gelöscht.
Die automatische interne
Kundennummer vergibt ausschließlich das aktive Server Script
`Customer Internal Number Auto Assignment - Update` beim Speichern neuer Kunden.
Das sind Exportwerte aus dem Repository,
keine Bestätigung des Zustands einer laufenden ERPNext-Site.

Die sechs JavaScript-Dateien in `js_scripts` sind über `doctype_js` registriert;
weitere Serverfunktionen sind über Dokumentereignisse, API-Overrides und den
täglichen Mahnlauf eingebunden. Für diese Dateien existiert kein eigenes
Aktiviert/Deaktiviert-Feld. Ihre Einbindung steht ebenfalls in der CSV.

Auffälligkeit: `Seriennummer - Eingangsrechnung über SN-Bündel ermitteln und eintragen`
steht in `server_script.json`, fehlt aber in der Server-Script-Auswahlliste unter
`fixtures` in `hooks.py`. Ein erneuter Fixture-Export könnte diesen Datensatz
entfernen. Die bestehende Auswahl wurde nicht geändert.

Liste nach Änderungen neu erzeugen:

```sh
python tools/script_inventory.py
```

Den tatsächlich installierten Bestand inklusive Aktivierungskennzeichen kann
ein Administrator auf dem ERPNext-Server aus dem Bench-Verzeichnis auslesen,
sobald diese App-Version dort installiert ist:

```sh
bench --site <site-name> execute az_it.az_it.api.script_inventory.get_script_inventory
```

Der Befehl liest nur Daten und gibt auch die installierten Apps, die App-Version
und die globale `server_script_enabled`-Konfiguration aus. Scheduler-Verfügbarkeit
und globale Einstellungen können die Ausführung zusätzlich beeinflussen.
