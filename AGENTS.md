# Arbeit an AZ-IT

- Ausschließlich in diesem Checkout arbeiten. Die benachbarten Ordner unter
  `C:\Users\marcu\Repositories` sind eigenständige Arbeitsstände.
- `CHANGELOG.md` ist die verbindliche Dokumentation für Bestand und Änderungen.
  Bei jeder Änderung einen verständlichen Eintrag unter „Noch nicht veröffentlicht“
  ergänzen: betroffene Skripte/Felder, neues Verhalten, Grund und relevante Prüfung.
  Auch Dokumentation, Werkzeuge, Konfiguration und entfernte Funktionen vermerken.
- Nach Änderungen an Skripten, Hooks, Feldern, Property Settern oder Werkzeugen
  `python tools/update_documentation.py` ausführen. Der Befehl aktualisiert den
  Bestandsabschnitt in `CHANGELOG.md` sowie `SCRIPT_INVENTORY.csv`.
  Den manuellen Änderungsverlauf oberhalb des Bestandsabschnitts beibehalten.
- Vor Abschluss `python tools/update_documentation.py --check` und
  `git diff --check` ausführen. Fachliche Beschreibungen zusätzlich mitprüfen;
  die automatische Bestandsliste ersetzt keinen verständlichen Änderungseintrag.
- Bei einer Veröffentlichung die unveröffentlichten Einträge der tatsächlichen
  Version mit Datum zuordnen. Keine Versionsnummer für noch lokale Änderungen erfinden.
- Die veralteten Client Scripts `Internal Customer Series` und
  `Kunde - automatische Kundennummer` wurden entfernt. Nicht erneut als Fixtures
  oder in die Export-Auswahl aufnehmen. Auf bestehenden Sites löscht der Nutzer
  diese Datensätze manuell; hierfür wurde kein Löschpatch beauftragt.
