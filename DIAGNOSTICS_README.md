# System Diagnostics Web-App

Die System-Diagnostics Web-App ermöglicht das Ausführen der System-Tests über eine Weboberfläche.

## Zugriff

Nach der Installation der App ist die Diagnose-Seite erreichbar unter:

```
https://your-site.com/system_diagnostics
```

Oder lokal:

```
http://localhost:8000/system_diagnostics
```

## Features

- ✅ Interaktive Web-Oberfläche mit Button zum Starten der Tests
- ✅ Grafische Darstellung der Test-Ergebnisse
- ✅ Fortschrittsbalken für erfolgreiche/fehlgeschlagene Tests
- ✅ Gruppierung nach Test-Kategorien
- ✅ Debug-Ausgaben bei fehlgeschlagenen Tests
- ✅ Optional: Node.js Tests können deaktiviert werden
- ✅ Responsive Design

## Test-Kategorien

1. **Netzwerk & DNS Tests**
   - GitHub Erreichbarkeit
   - erptest.az-it.systems Erreichbarkeit
   - deb.nodesource.com Erreichbarkeit
   - DNS-Auflösung

2. **HTTPS / TLS Tests**
   - GitHub HTTPS
   - erptest.az-it.systems HTTPS
   - Google Fonts HTTPS
   - Zertifikats-Validierung

3. **Zertifikat Details**
   - SSL-Zertifikat SAN Überprüfung

4. **Node.js Umgebung** (optional)
   - Node.js Version
   - sudo Node.js Version

5. **wkhtmltopdf**
   - Version Check
   - HTTPS zu PDF Konvertierung

## Verwendung

1. Öffnen Sie die Seite `/system_diagnostics`
2. Optional: Deaktivieren Sie die Node.js Tests
3. Klicken Sie auf "Diagnose starten"
4. Warten Sie auf die Ergebnisse
5. Scrollen Sie durch die detaillierten Test-Ergebnisse
6. Klicken Sie auf "Debug-Ausgabe anzeigen" bei fehlgeschlagenen Tests

## Technische Details

### Dateien

- `az_it/templates/pages/system_diagnostics.html` - Frontend Template
- `az_it/az_it/page/system_diagnostics/system_diagnostics.py` - Backend Python Logic

### Backend

Das Python-Backend führt die gleichen Tests aus wie das Bash-Script `check-az.sh`, verwendet aber Python `subprocess` um die Befehle auszuführen.

### Frontend

Das Frontend verwendet:
- Bootstrap für das Layout
- Font Awesome für Icons
- Frappe Framework JavaScript API
- jQuery für DOM-Manipulation
- CSS Animationen für bessere UX
