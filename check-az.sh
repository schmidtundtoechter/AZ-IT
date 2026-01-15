#!/usr/bin/env bash

set -u
set -o pipefail

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Test-Ergebnisse
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

echo -e "${BOLD}============================================================${NC}"
echo -e "${BOLD} SYSTEMDIAGNOSE – PDF / TLS / WKHTMLTOPDF / NODE${NC}"
echo -e " Host: $(hostname)"
echo -e " Datum: $(date)"
echo -e " Benutzer: $(whoami)"
echo -e "${BOLD}============================================================${NC}"
echo

# ------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------
test_pass() {
  echo -e "${GREEN}✓${NC} $1"
  ((TESTS_PASSED++))
}

test_fail() {
  echo -e "${RED}✗${NC} $1"
  ((TESTS_FAILED++))
  FAILED_TESTS+=("$1")
}

test_header() {
  echo
  echo -e "${BLUE}${BOLD}$1${NC}"
}

show_debug() {
  echo -e "${YELLOW}Debug-Ausgabe:${NC}"
  echo "----------------------------------------"
  echo "$1"
  echo "----------------------------------------"
  echo
}


# ------------------------------------------------------------
# 1. Basis-Netzwerk & DNS
# ------------------------------------------------------------
test_header "1) Netzwerk & DNS Tests"

# Test: GitHub erreichbar
if ping -c 1 -W 2 github.com >/dev/null 2>&1; then
  test_pass "GitHub erreichbar"
else
  test_fail "GitHub nicht erreichbar"
  show_debug "$(ping -c 1 github.com 2>&1)"
fi

# Test: erptest.az-it.systems erreichbar
if ping -c 1 -W 2 erptest.az-it.systems >/dev/null 2>&1; then
  test_pass "erptest.az-it.systems erreichbar"
else
  test_fail "erptest.az-it.systems nicht erreichbar"
  show_debug "$(ping -c 1 erptest.az-it.systems 2>&1)"
fi

# Test: deb.nodesource.com erreichbar
if ping -c 1 -W 2 deb.nodesource.com >/dev/null 2>&1; then
  test_pass "deb.nodesource.com erreichbar"
else
  test_fail "deb.nodesource.com nicht erreichbar"
  show_debug "$(ping -c 1 deb.nodesource.com 2>&1)"
fi

# Test: deb.nodesource.com HTTPS
CURL_OUTPUT=$(curl -sS -I https://deb.nodesource.com 2>&1)
if echo "$CURL_OUTPUT" | grep -q "HTTP.*200\|HTTP.*301\|HTTP.*302"; then
  test_pass "deb.nodesource.com HTTPS Verbindung"
else
  test_fail "deb.nodesource.com HTTPS fehlgeschlagen"
  show_debug "$(curl -Iv https://deb.nodesource.com 2>&1)\n\nHinweis: Führen Sie './inspect-ca.sh deb.nodesource.com nodesource-root-ca.crt' aus, um das Zertifikat zu analysieren."
fi

# Test: DNS-Auflösung
DNS_OUTPUT=$(getent hosts erptest.az-it.systems 2>&1)
if echo "$DNS_OUTPUT" | grep -q "85.13.161.229"; then
  test_pass "DNS-Auflösung für erptest.az-it.systems"
else
  test_fail "DNS-Auflösung fehlgeschlagen"
  show_debug "$DNS_OUTPUT"
fi

# ------------------------------------------------------------
# 2. HTTPS / TLS – CURL
# ------------------------------------------------------------
test_header "2) HTTPS / TLS Tests (curl)"

# Test: GitHub HTTPS
CURL_OUTPUT=$(curl -sS -I https://github.com 2>&1)
if echo "$CURL_OUTPUT" | grep -q "HTTP.*200\|HTTP.*301\|HTTP.*302"; then
  test_pass "GitHub HTTPS Verbindung"
else
  test_fail "GitHub HTTPS Verbindung fehlgeschlagen"
  show_debug "$(curl -Iv https://github.com 2>&1)\n\nHinweis: Führen Sie './inspect-ca.sh github.com github-root-ca.crt' aus, um das Zertifikat zu analysieren."
fi

# Test: erptest HTTPS
CURL_OUTPUT=$(curl -sS -I https://erptest.az-it.systems 2>&1)
if echo "$CURL_OUTPUT" | grep -q "HTTP.*200\|HTTP.*301\|HTTP.*302"; then
  test_pass "erptest.az-it.systems HTTPS Verbindung"
else
  test_fail "erptest.az-it.systems HTTPS fehlgeschlagen"
  show_debug "$(curl -Iv https://erptest.az-it.systems 2>&1)\n\nHinweis: Führen Sie './inspect-ca.sh erptest.az-it.systems erptest-root-ca.crt' aus, um das Zertifikat zu analysieren."
fi

# ------------------------------------------------------------
# 3. HTTPS / TLS – OpenSSL (SAN / Zertifikat)
# ------------------------------------------------------------
test_header "3) Zertifikat Details"

# Test: SSL-Zertifikat mit korrektem SAN
OPENSSL_OUTPUT=$(echo | openssl s_client -connect erptest.az-it.systems:443 -servername erptest.az-it.systems 2>&1)
if echo "$OPENSSL_OUTPUT" | grep -q "DNS:erptest.az-it.systems"; then
  test_pass "SSL-Zertifikat mit korrektem SAN"
else
  test_fail "SSL-Zertifikat SAN fehlt oder falsch"
  show_debug "$OPENSSL_OUTPUT"
fi

# Test: Verify return code
if echo "$OPENSSL_OUTPUT" | grep -q "Verify return code: 0 (ok)"; then
  test_pass "SSL-Zertifikat Validierung erfolgreich"
else
  test_fail "SSL-Zertifikat Validierung fehlgeschlagen"
  show_debug "$(echo "$OPENSSL_OUTPUT" | grep -A 5 "Verify return code")"
fi

# ------------------------------------------------------------
# 4. Node.js – User vs. sudo
# ------------------------------------------------------------
test_header "4) Node.js Umgebung"

# Test: Node.js verfügbar
NODE_VERSION=$(node -v 2>&1)
if [[ $NODE_VERSION =~ ^v[0-9]+ ]]; then
  test_pass "Node.js verfügbar: $NODE_VERSION"
else
  test_fail "Node.js nicht verfügbar"
  show_debug "$NODE_VERSION"
fi

# Test: sudo Node.js
SUDO_NODE_VERSION=$(sudo node -v 2>&1)
if [[ $SUDO_NODE_VERSION =~ ^v[0-9]+ ]]; then
  NODE_MAJOR=$(echo "$NODE_VERSION" | sed 's/v\([0-9]*\).*/\1/')
  SUDO_MAJOR=$(echo "$SUDO_NODE_VERSION" | sed 's/v\([0-9]*\).*/\1/')
  
  if [ "$NODE_MAJOR" = "$SUDO_MAJOR" ]; then
    test_pass "sudo Node.js Version stimmt überein: $SUDO_NODE_VERSION"
  else
    test_fail "sudo Node.js Version unterschiedlich: User=$NODE_VERSION, sudo=$SUDO_NODE_VERSION"
    show_debug "User node: $(which node)\nsudo node: $(sudo which node)"
  fi
else
  test_fail "sudo Node.js nicht verfügbar"
  show_debug "$SUDO_NODE_VERSION"
fi

# ------------------------------------------------------------
# 5. wkhtmltopdf – Pfad & Version
# ------------------------------------------------------------
test_header "5) wkhtmltopdf"

# Test: wkhtmltopdf verfügbar
WKHTMLTOPDF_VERSION=$(wkhtmltopdf --version 2>&1)
if [[ $WKHTMLTOPDF_VERSION =~ wkhtmltopdf ]]; then
  if [[ $WKHTMLTOPDF_VERSION =~ 0\.12\.6 ]]; then
    test_pass "wkhtmltopdf Version 0.12.6 (empfohlen)"
  else
    VERSION_NUM=$(echo "$WKHTMLTOPDF_VERSION" | grep -oP '\d+\.\d+\.\d+' | head -1)
    test_pass "wkhtmltopdf verfügbar: $VERSION_NUM (Empfehlung: 0.12.6)"
  fi
else
  test_fail "wkhtmltopdf nicht verfügbar"
  show_debug "$WKHTMLTOPDF_VERSION"
fi

# ------------------------------------------------------------
# 6. wkhtmltopdf – HTTPS Direktzugriff
# ------------------------------------------------------------
test_header "6) wkhtmltopdf HTTPS Tests"

# Test: wkhtmltopdf kann HTTPS verarbeiten
WKHTML_TEST="/tmp/wkhtml_https_test_$$.pdf"
WKHTML_OUTPUT=$(wkhtmltopdf https://erptest.az-it.systems "$WKHTML_TEST" 2>&1)
if [ -f "$WKHTML_TEST" ] && [ -s "$WKHTML_TEST" ]; then
  test_pass "wkhtmltopdf kann HTTPS-Seite zu PDF konvertieren"
  rm -f "$WKHTML_TEST"
else
  test_fail "wkhtmltopdf HTTPS-zu-PDF Konvertierung fehlgeschlagen"
  show_debug "$WKHTML_OUTPUT"
fi

# ------------------------------------------------------------
# 7. Asset-Test (kritisch für PDF)
# ------------------------------------------------------------
test_header "7) Frappe Asset Tests"

ASSET_URL="https://erptest.az-it.systems/assets/frappe/dist/css/print.bundle.RXLI3KAN.css"

# Test: Asset-URL erreichbar
ASSET_OUTPUT=$(curl -sS -I "$ASSET_URL" 2>&1)
if echo "$ASSET_OUTPUT" | grep -q "HTTP.*200"; then
  test_pass "Frappe print.css Asset erreichbar"
else
  test_fail "Frappe print.css Asset nicht erreichbar (200 OK benötigt)"
  show_debug "Asset URL: $ASSET_URL\n\n$(curl -Iv "$ASSET_URL" 2>&1)"
fi

# Test: Asset Download
ASSET_FILE="/tmp/print.bundle_$$.css"
if wget -q -O "$ASSET_FILE" "$ASSET_URL" 2>&1 && [ -s "$ASSET_FILE" ]; then
  test_pass "Frappe print.css Asset herunterladbar"
  rm -f "$ASSET_FILE"
else
  test_fail "Frappe print.css Asset Download fehlgeschlagen"
  show_debug "$(wget -O "$ASSET_FILE" "$ASSET_URL" 2>&1)"
fi

echo
echo -e "${BOLD}============================================================${NC}"
echo -e "${BOLD} ZUSAMMENFASSUNG${NC}"
echo -e "${BOLD}============================================================${NC}"
echo -e "${GREEN}Tests bestanden:${NC} $TESTS_PASSED"
echo -e "${RED}Tests fehlgeschlagen:${NC} $TESTS_FAILED"

if [ $TESTS_FAILED -gt 0 ]; then
  echo
  echo -e "${RED}${BOLD}Fehlgeschlagene Tests:${NC}"
  for test in "${FAILED_TESTS[@]}"; do
    echo -e "  ${RED}✗${NC} $test"
  done
  echo
  echo -e "${YELLOW}Scrollen Sie nach oben für detaillierte Debug-Ausgaben.${NC}"
  exit 1
else
  echo
  echo -e "${GREEN}${BOLD}✓ Alle Tests erfolgreich!${NC}"
  exit 0
fi

