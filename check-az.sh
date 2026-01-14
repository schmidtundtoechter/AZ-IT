#!/usr/bin/env bash

set -u
set -o pipefail

echo "============================================================"
echo " SYSTEMDIAGNOSE – PDF / TLS / WKHTMLTOPDF / NODE"
echo " Host: $(hostname)"
echo " Datum: $(date)"
echo " Benutzer: $(whoami)"
echo "============================================================"
echo

# ------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------
section () {
  echo
  echo "------------------------------------------------------------"
  echo "$1"
  echo "------------------------------------------------------------"
}

cmd () {
  echo
  echo "> $*"
  "$@" || echo "!! Kommando fehlgeschlagen (Exit $?)"
}

# ------------------------------------------------------------
# 1. Basis-Netzwerk & DNS
# ------------------------------------------------------------
section "1) Netzwerk & DNS"

cmd ping -c 1 github.com
cmd ping -c 1 erptest.az-it.systems

cmd getent hosts erptest.az-it.systems

# ------------------------------------------------------------
# 2. HTTPS / TLS – CURL
# ------------------------------------------------------------
section "2) HTTPS / TLS (curl)"

cmd curl -Iv https://github.com
cmd curl -Iv https://erptest.az-it.systems

echo
echo "Hinweis:"
echo "- Erwartet: TLS OK, kein Zertifikatsfehler"
echo "- Fehler hier => wkhtmltopdf-Problem vorprogrammiert"

# ------------------------------------------------------------
# 3. HTTPS / TLS – OpenSSL (SAN / Zertifikat)
# ------------------------------------------------------------
section "3) Zertifikat Details (openssl)"

cmd openssl s_client \
  -connect erptest.az-it.systems:443 \
  -servername erptest.az-it.systems \
  -showcerts </dev/null

echo
echo "Achte auf:"
echo "- Subject Alternative Name (SAN)"
echo "- Muss DNS:erptest.az-it.systems enthalten"
echo "- Vollständige Zertifikatskette"

# ------------------------------------------------------------
# 4. Node.js – User vs. sudo
# ------------------------------------------------------------
section "4) Node.js Umgebung"

cmd node -v
cmd which node

cmd sudo node -v
cmd sudo which node

echo
echo "Bewertung:"
echo "- node und sudo node sollten idealerweise gleiche Major-Version haben"
echo "- Abweichung => Probleme bei Build / Assets"

# ------------------------------------------------------------
# 5. wkhtmltopdf – Pfad & Version
# ------------------------------------------------------------
section "5) wkhtmltopdf"

cmd which wkhtmltopdf
cmd wkhtmltopdf --version

echo
echo "Bewertung:"
echo "- Empfohlen: 0.12.6 (patched qt)"

# ------------------------------------------------------------
# 6. wkhtmltopdf – HTTPS Direktzugriff
# ------------------------------------------------------------
section "6) wkhtmltopdf HTTPS Direkt-Test"

cmd wkhtmltopdf \
  https://erptest.az-it.systems \
  /tmp/wkhtml_https_test.pdf

# ------------------------------------------------------------
# 7. Asset-Test (kritisch für PDF)
# ------------------------------------------------------------
section "7) Frappe Asset-Test (print.css)"

ASSET_URL="https://erptest.az-it.systems/assets/frappe/dist/css/print.bundle.RXLI3KAN.css"

echo "Asset URL:"
echo "  $ASSET_URL"

cmd curl -Iv "$ASSET_URL"
cmd wget "$ASSET_URL"

echo
echo "Bewertung:"
echo "- 200 OK nötig"

echo
echo "============================================================"
echo " DIAGNOSE ENDE"
echo "============================================================"
