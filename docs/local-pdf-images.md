# Bilder in lokal erzeugten PDFs (wkhtmltopdf)

## Problem

Auf lokalen Frappe-Entwicklungssystemen werden in PDF-Dokumenten (z.B. Print Designer Druckformate) keine Bilder angezeigt. Die Vorschau im Browser zeigt die Bilder korrekt, in der heruntergeladenen PDF fehlen sie jedoch lautlos (keine Fehlermeldung, nur weißer/leerer Bereich).

## Ursache

Frappe reicht relative Bild-URLs (z.B. `/files/LogoAZ.jpg`) an wkhtmltopdf weiter, nachdem es sie zu absoluten URLs erweitert hat – z.B. `http://localhost:8000/files/LogoAZ.jpg`. wkhtmltopdf ruft diese URL dann HTTP-seitig ab.

Das Problem entsteht durch zwei zusammenwirkende Faktoren:

### 1. Frappe identifiziert Sites über den HTTP-`Host`-Header

Frappe ist ein Multi-Site-System. Wenn mehrere Sites auf demselben Server laufen, identifiziert Frappe die richtige Site anhand des HTTP-`Host`-Headers der eingehenden Anfrage.

Wenn `host_name` in der `site_config.json` auf `http://localhost:8000` gesetzt ist, baut Frappe alle Bild-URLs mit `localhost` als Hostname auf. wkhtmltopdf sendet dann eine Anfrage mit `Host: localhost`. Frappe kann daraus keine Site ableiten (kein `currentsite.txt`, kein Site-Match) → **HTTP 500**.

### 2. `*.localhost`-Subdomains werden im Container nicht per DNS aufgelöst

Wenn `host_name` auf den korrekten Site-Hostnamen (z.B. `http://erptest.az-it.localhost:8000`) gesetzt wird, schlägt wkhtmltopdf fehl, weil `erptest.az-it.localhost` im Docker-Container nicht in `/etc/hosts` eingetragen ist und kein DNS-Server diese `*.localhost`-Subdomains auflöst.

Browser (Chrome, Firefox) lösen `*.localhost` automatisch auf `127.0.0.1` auf – wkhtmltopdf (patched Qt, kein Browser) tut das **nicht**.

### Zusammenfassung

| `host_name` | Problem |
|---|---|
| `http://localhost:8000` | wkhtmltopdf sendet `Host: localhost` → Frappe findet keine Site → HTTP 500 → kein Bild |
| `http://erptest.az-it.localhost:8000` | Hostname nicht in `/etc/hosts` → DNS-Auflösung schlägt fehl → kein Bild |
| `http://erptest.az-it.localhost:8000` + Eintrag in `/etc/hosts` | ✓ funktioniert |

## Lösung

Für jede lokale Site müssen zwei Dinge stimmen:

1. **`host_name` in `site_config.json`** muss auf den echten Site-Hostnamen zeigen (nicht `localhost`)
2. **Der Hostname muss in `/etc/hosts`** auf `127.0.0.1` zeigen

### Konfigurierte Sites

| Site | `host_name` |
|---|---|
| `d-code.localhost` | `http://d-code.localhost:8000` |
| `d-code-1.localhost` | `http://d-code-1.localhost:8000` |
| `erp.az-it.localhost` | `http://erp.az-it.localhost:8000` |
| `erptest.az-it.localhost` | `http://erptest.az-it.localhost:8000` |
| `studio.localhost` | `http://studio.localhost:8000` |

### `/etc/hosts`-Einträge (werden bei Container-Neustart zurückgesetzt!)

```
127.0.0.1 erp.az-it.localhost erptest.az-it.localhost
127.0.0.1 d-code.localhost d-code-1.localhost
127.0.0.1 studio.localhost
```

### Persistenz via `docker-compose.yml`

Da `/etc/hosts` nach jedem Container-Neustart zurückgesetzt wird, wurden die Einträge in `frappe_docker/devcontainer-example/docker-compose.yml` unter `extra_hosts` eingetragen. Docker trägt diese beim Container-Start automatisch in `/etc/hosts` ein:

```yaml
extra_hosts:
  - "erp.az-it.localhost:127.0.0.1"
  - "erptest.az-it.localhost:127.0.0.1"
  - "d-code.localhost:127.0.0.1"
  - "d-code-1.localhost:127.0.0.1"
  - "studio.localhost:127.0.0.1"
```

## Neue lokale Site hinzufügen

Wenn eine neue lokale Site angelegt wird, müssen folgende Schritte durchgeführt werden:

1. `host_name` in `sites/<neue-site>/site_config.json` setzen:
   ```json
   "host_name": "http://<neue-site>:8000"
   ```

2. Eintrag in `/etc/hosts` (sofort aktiv, aber nicht persistent):
   ```bash
   echo "127.0.0.1 <neue-site>" | sudo tee -a /etc/hosts
   ```

3. Eintrag in `frappe_docker/devcontainer-example/docker-compose.yml` unter `extra_hosts` (persistent):
   ```yaml
   - "<neue-site>:127.0.0.1"
   ```

## Backup-Sync-Script (`backup_sync.py`)

Das Script `backup_sync.py` überschreibt beim Restore die `site_config.json`. Es setzt deshalb nach jedem Restore automatisch den korrekten `host_name` und stellt sicher, dass der Hostname in `/etc/hosts` eingetragen ist (Funktion `_ensure_hosts_entry`).
