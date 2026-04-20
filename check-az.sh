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

# Standard-Konfiguration
VERBOSE=0
SUDO_TEST=0
SERVER_NAME=""
SERVER_HOST=""
SYSTEM_CA_BUNDLE="/etc/ssl/certs/ca-certificates.crt"

# Test-Ergebnisse
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# ------------------------------------------------------------
# Hilfsfunktion: Usage
# ------------------------------------------------------------
usage() {
  local exit_code="${1:-0}"
  echo "Usage: $0 [OPTIONS]"
  echo "       $0 [OPTIONS] <server-name>"
  echo
  echo "Optionen:"
  echo "  -v, --verbose    Zeige Debug-Ausgaben an"
  echo "  -s, --sudo       Führe sudo Node.js-Tests durch"
  echo "  -h, --help       Zeige diese Hilfe an"
  echo "  <server-name>    Pflichtargument, z. B. erptest"
  echo
  echo "Beispiele:"
  echo "  $0 erptest       # Normale Ausführung"
  echo "  $0 -v erptest    # Mit Debug-Ausgaben"
  echo "  $0 -s erptest    # Mit sudo Node.js-Tests"
  echo "  $0 -v -s erptest # Mit Debug-Ausgaben und sudo-Tests"
  exit "$exit_code"
}

# ------------------------------------------------------------
# Argument-Parsing
# ------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case $1 in
    -v|--verbose)
      VERBOSE=1
      shift
      ;;
    -s|--sudo)
      SUDO_TEST=1
      shift
      ;;
    -h|--help)
      usage 0
      ;;
    -*)
      echo "Unbekannte Option: $1"
      usage 1
      ;;
    *)
      if [ -z "$SERVER_NAME" ]; then
        SERVER_NAME="$1"
      else
        echo "Zu viele Positionsargumente: $1"
        usage 1
      fi
      shift
      ;;
  esac
done

if [ -z "$SERVER_NAME" ]; then
  echo "Fehler: <server-name> ist erforderlich (z. B. erptest)."
  usage 1
fi

SERVER_HOST="${SERVER_NAME}.az-it.systems"

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
  if [ $VERBOSE -eq 1 ]; then
    echo -e "${YELLOW}Debug-Ausgabe:${NC}"
    echo "----------------------------------------"
    echo -e "$1"
    echo "----------------------------------------"
    echo
  fi
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

# Test: Server erreichbar
if ping -c 1 -W 2 "$SERVER_HOST" >/dev/null 2>&1; then
  test_pass "$SERVER_HOST erreichbar"
else
  test_fail "$SERVER_HOST nicht erreichbar"
  show_debug "$(ping -c 1 "$SERVER_HOST" 2>&1)"
fi

# Test: deb.nodesource.com erreichbar
if ping -c 1 -W 2 deb.nodesource.com >/dev/null 2>&1; then
  test_pass "deb.nodesource.com erreichbar"
else
  test_fail "deb.nodesource.com nicht erreichbar"
  show_debug "$(ping -c 1 deb.nodesource.com 2>&1)"
fi

# Test: DNS-Auflösung
# Ermittle die eigene IP-Adresse (ursprünglich war es 10.0.2.126)
OWN_IP=$(hostname -I | awk '{print $1}')
if [ -z "$OWN_IP" ]; then
  OWN_IP=$(ip addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1)
fi

DNS_OUTPUT=$(getent hosts "$SERVER_HOST" 2>&1)
RESOLVED_IP=$(echo "$DNS_OUTPUT" | awk '{print $1}')

if echo "$DNS_OUTPUT" | grep -q "$OWN_IP"; then
  test_pass "DNS-Auflösung für $SERVER_HOST → $OWN_IP"
else
  if [ -z "$RESOLVED_IP" ]; then
    test_fail "DNS-Auflösung fehlgeschlagen: $SERVER_HOST konnte nicht aufgelöst werden"
    show_debug "Erwartete IP: $OWN_IP\nDNS-Ausgabe: $DNS_OUTPUT"
  else
    test_fail "DNS-Auflösung fehlgeschlagen: $SERVER_HOST löst auf falsche IP auf"
    show_debug "Erwartete IP (eigene): $OWN_IP\nAufgelöste IP: $RESOLVED_IP\nVollständige DNS-Ausgabe:\n$DNS_OUTPUT"
  fi
fi

# ------------------------------------------------------------
# 2. HTTPS / TLS – CURL
# ------------------------------------------------------------
test_header "2) HTTPS / TLS Tests (curl)"

# Test: deb.nodesource.com HTTPS
CURL_OUTPUT=$(curl -sS -I https://deb.nodesource.com 2>&1)
if echo "$CURL_OUTPUT" | grep -q "HTTP.*200\|HTTP.*301\|HTTP.*302"; then
  test_pass "deb.nodesource.com HTTPS Verbindung"
else
  CURL_VERBOSE=$(curl -Iv https://deb.nodesource.com 2>&1)
  if echo "$CURL_VERBOSE" | grep -q "self-signed certificate"; then
    test_fail "deb.nodesource.com HTTPS fehlgeschlagen: Root CA Problem (selbst-signiertes Zertifikat)"
    show_debug "$CURL_VERBOSE\n\nHinweis: Führen Sie './inspect-ca.sh deb.nodesource.com nodesource-root-ca.crt' aus, um das Root-Zertifikat zu analysieren und zu installieren."
  elif echo "$CURL_VERBOSE" | grep -qi "certificate.*name\|hostname.*mismatch\|subject alternative name"; then
    test_fail "deb.nodesource.com HTTPS fehlgeschlagen: Hostname-Mismatch im Zertifikat"
    show_debug "$CURL_VERBOSE\n\nHinweis: Führen Sie './inspect-ca.sh deb.nodesource.com nodesource-root-ca.crt' aus, um das Zertifikat zu analysieren."
  else
    test_fail "deb.nodesource.com HTTPS fehlgeschlagen"
    show_debug "$CURL_VERBOSE\n\nHinweis: Führen Sie './inspect-ca.sh deb.nodesource.com nodesource-root-ca.crt' aus, um das Zertifikat zu analysieren."
  fi
fi

# Test: GitHub HTTPS
CURL_OUTPUT=$(curl -sS -I https://github.com 2>&1)
if echo "$CURL_OUTPUT" | grep -q "HTTP.*200\|HTTP.*301\|HTTP.*302"; then
  test_pass "GitHub HTTPS Verbindung"
else
  CURL_VERBOSE=$(curl -Iv https://github.com 2>&1)
  if echo "$CURL_VERBOSE" | grep -q "self-signed certificate"; then
    test_fail "GitHub HTTPS fehlgeschlagen: Root CA Problem (selbst-signiertes Zertifikat)"
    show_debug "$CURL_VERBOSE\n\nHinweis: Führen Sie './inspect-ca.sh github.com github-root-ca.crt' aus, um das Root-Zertifikat zu analysieren und zu installieren."
  elif echo "$CURL_VERBOSE" | grep -qi "certificate.*name\|hostname.*mismatch\|subject alternative name"; then
    test_fail "GitHub HTTPS fehlgeschlagen: Hostname-Mismatch im Zertifikat"
    show_debug "$CURL_VERBOSE\n\nHinweis: Führen Sie './inspect-ca.sh github.com github-root-ca.crt' aus, um das Zertifikat zu analysieren."
  else
    test_fail "GitHub HTTPS Verbindung fehlgeschlagen"
    show_debug "$CURL_VERBOSE\n\nHinweis: Führen Sie './inspect-ca.sh github.com github-root-ca.crt' aus, um das Zertifikat zu analysieren."
  fi
fi

# Test: Server HTTPS
CURL_OUTPUT=$(curl -sS -I "https://$SERVER_HOST" 2>&1)
if echo "$CURL_OUTPUT" | grep -q "HTTP.*200\|HTTP.*301\|HTTP.*302"; then
  test_pass "$SERVER_HOST HTTPS Verbindung"
else
  CURL_VERBOSE=$(curl -Iv "https://$SERVER_HOST" 2>&1)
  if echo "$CURL_VERBOSE" | grep -q "self-signed certificate"; then
    test_fail "$SERVER_HOST HTTPS fehlgeschlagen: Root CA Problem (selbst-signiertes Zertifikat)"
    show_debug "$CURL_VERBOSE\n\nHinweis: Führen Sie './inspect-ca.sh $SERVER_HOST ${SERVER_NAME}-root-ca.crt' aus, um das Root-Zertifikat zu analysieren und zu installieren."
  elif echo "$CURL_VERBOSE" | grep -qi "certificate.*name\|hostname.*mismatch\|subject alternative name"; then
    test_fail "$SERVER_HOST HTTPS fehlgeschlagen: Hostname-Mismatch im Zertifikat"
    show_debug "$CURL_VERBOSE\n\nHinweis: Führen Sie './inspect-ca.sh $SERVER_HOST ${SERVER_NAME}-root-ca.crt' aus, um das Zertifikat zu analysieren."
  else
    test_fail "$SERVER_HOST HTTPS fehlgeschlagen"
    show_debug "$CURL_VERBOSE\n\nHinweis: Führen Sie './inspect-ca.sh $SERVER_HOST ${SERVER_NAME}-root-ca.crt' aus, um das Zertifikat zu analysieren."
  fi
fi

# Test: Google Fonts domains (fonts.googleapis.com)
CURL_OUTPUT=$(curl -sS -I https://fonts.googleapis.com 2>&1)
if echo "$CURL_OUTPUT" | grep -q "HTTP.*200\|HTTP.*301\|HTTP.*302\|HTTP.*404"; then
  test_pass "fonts.googleapis.com HTTPS Verbindung"
else
  CURL_VERBOSE=$(curl -Iv https://fonts.googleapis.com 2>&1)
  if echo "$CURL_VERBOSE" | grep -q "self-signed certificate"; then
    test_fail "fonts.googleapis.com HTTPS fehlgeschlagen: Root CA Problem (selbst-signiertes Zertifikat)"
    show_debug "$CURL_VERBOSE\n\nHinweis: Führen Sie './inspect-ca.sh fonts.googleapis.com google-fonts-ca.crt' aus, um das Root-Zertifikat zu analysieren und zu installieren."
  elif echo "$CURL_VERBOSE" | grep -qi "Connection reset by peer"; then
    test_fail "fonts.googleapis.com HTTPS fehlgeschlagen: Connection reset by peer (Firewall/Proxy?)"
    show_debug "$CURL_VERBOSE"
  else
    test_fail "fonts.googleapis.com HTTPS Verbindung fehlgeschlagen"
    show_debug "$CURL_VERBOSE\n\nHinweis: Führen Sie './inspect-ca.sh fonts.googleapis.com google-fonts-ca.crt' aus, um das Zertifikat zu analysieren."
  fi
fi

# Test: Google Fonts static domain (fonts.gstatic.com)
CURL_OUTPUT=$(curl -sS -I https://fonts.gstatic.com 2>&1)
if echo "$CURL_OUTPUT" | grep -q "HTTP.*200\|HTTP.*301\|HTTP.*302\|HTTP.*404"; then
  test_pass "fonts.gstatic.com HTTPS Verbindung"
else
  CURL_VERBOSE=$(curl -Iv https://fonts.gstatic.com 2>&1)
  if echo "$CURL_VERBOSE" | grep -q "self-signed certificate"; then
    test_fail "fonts.gstatic.com HTTPS fehlgeschlagen: Root CA Problem (selbst-signiertes Zertifikat)"
    show_debug "$CURL_VERBOSE\n\nHinweis: Führen Sie './inspect-ca.sh fonts.gstatic.com google-gstatic-ca.crt' aus, um das Root-Zertifikat zu analysieren und zu installieren."
  elif echo "$CURL_VERBOSE" | grep -qi "Connection reset by peer"; then
    test_fail "fonts.gstatic.com HTTPS fehlgeschlagen: Connection reset by peer (Firewall/Proxy?)"
    show_debug "$CURL_VERBOSE"
  else
    test_fail "fonts.gstatic.com HTTPS Verbindung fehlgeschlagen"
    show_debug "$CURL_VERBOSE\n\nHinweis: Führen Sie './inspect-ca.sh fonts.gstatic.com google-gstatic-ca.crt' aus, um das Zertifikat zu analysieren."
  fi
fi

# Test: Google Main domain (www.google.com) - Vergleichstest
CURL_OUTPUT=$(curl -sS -I https://www.google.com 2>&1)
if echo "$CURL_OUTPUT" | grep -q "HTTP.*200\|HTTP.*301\|HTTP.*302"; then
  test_pass "www.google.com HTTPS Verbindung (Vergleichstest)"
else
  CURL_VERBOSE=$(curl -Iv https://www.google.com 2>&1)
  test_fail "www.google.com HTTPS Verbindung fehlgeschlagen"
  show_debug "$CURL_VERBOSE"
fi

# Info: Aktive Python-CA-Bundles anzeigen
PYTHON_CA_INFO=$(cd /home/frappe-user/frappe-bench && ./env/bin/python -c "
import certifi
import os
import ssl
print('certifi: ' + certifi.where())
print('REQUESTS_CA_BUNDLE: ' + os.environ.get('REQUESTS_CA_BUNDLE', '(nicht gesetzt)'))
print('SSL_CERT_FILE: ' + os.environ.get('SSL_CERT_FILE', '(nicht gesetzt)'))
print('OpenSSL: ' + ssl.OPENSSL_VERSION)
" 2>&1)
test_pass "Python CA-Bundle Info ermittelt"
show_debug "$PYTHON_CA_INFO"

# Test: Python requests für GitHub API (default certifi = realer install-app Pfad)
PYTHON_REQUESTS_OUTPUT=$(cd /home/frappe-user/frappe-bench && ./env/bin/python -c "
import requests
import sys
try:
    requests.head('https://api.github.com', timeout=5)
    sys.exit(0)
except requests.exceptions.SSLError as e:
    print('SSL Error: ' + str(e), file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print('Error: ' + str(e), file=sys.stderr)
    sys.exit(2)
" 2>&1)
PYTHON_REQUESTS_EXIT=$?

if [ $PYTHON_REQUESTS_EXIT -eq 0 ]; then
  test_pass "Python requests GitHub HTTPS (Default certifi, für Frappe)"
else
  if echo "$PYTHON_REQUESTS_OUTPUT" | grep -qi "SSL\|CERTIFICATE_VERIFY_FAILED"; then
    test_fail "Python requests GitHub HTTPS SSL-Fehler (Default certifi)"
    show_debug "$PYTHON_REQUESTS_OUTPUT\n\nAktiver certifi-Pfad:\n$PYTHON_CA_INFO\n\nHinweis: Vergleich mit System-CA siehe nächsten Test."
  else
    test_fail "Python requests GitHub HTTPS fehlgeschlagen (Default certifi)"
    show_debug "$PYTHON_REQUESTS_OUTPUT"
  fi
fi

# Vergleichstest: Python requests für GitHub API mit System-CA-Bundle
PYTHON_REQUESTS_SYSTEM_CA=$(cd /home/frappe-user/frappe-bench && REQUESTS_CA_BUNDLE="$SYSTEM_CA_BUNDLE" ./env/bin/python -c "
import requests
import sys
try:
    requests.head('https://api.github.com', timeout=5)
    sys.exit(0)
except requests.exceptions.SSLError as e:
    print('SSL Error: ' + str(e), file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print('Error: ' + str(e), file=sys.stderr)
    sys.exit(2)
" 2>&1)
PYTHON_REQUESTS_SYSTEM_CA_EXIT=$?

if [ $PYTHON_REQUESTS_SYSTEM_CA_EXIT -eq 0 ]; then
  test_pass "Python requests GitHub HTTPS (System-CA Vergleich)"
else
  if echo "$PYTHON_REQUESTS_SYSTEM_CA" | grep -qi "SSL\|CERTIFICATE_VERIFY_FAILED"; then
    test_fail "Python requests GitHub HTTPS SSL-Fehler (System-CA Vergleich)"
    show_debug "$PYTHON_REQUESTS_SYSTEM_CA\n\nVerwendetes CA-Bundle: $SYSTEM_CA_BUNDLE"
  else
    test_fail "Python requests GitHub HTTPS fehlgeschlagen (System-CA Vergleich)"
    show_debug "$PYTHON_REQUESTS_SYSTEM_CA"
  fi
fi

# Test: Python requests für api.github.com/repos/frappe/helpdesk (default certifi)
PYTHON_REQUESTS_FRAPPE=$(cd /home/frappe-user/frappe-bench && ./env/bin/python -c "
import requests
import sys
try:
    requests.head('https://api.github.com/repos/frappe/helpdesk', timeout=5)
    sys.exit(0)
except requests.exceptions.SSLError as e:
    print('SSL Error: ' + str(e), file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print('Error: ' + str(e), file=sys.stderr)
    sys.exit(2)
" 2>&1)
PYTHON_REQUESTS_FRAPPE_EXIT=$?

if [ $PYTHON_REQUESTS_FRAPPE_EXIT -eq 0 ]; then
  test_pass "Python requests Frappe-Repos-API (Default certifi, bench install-app Test)"
else
  if echo "$PYTHON_REQUESTS_FRAPPE" | grep -qi "SSL\|CERTIFICATE_VERIFY_FAILED"; then
    test_fail "Python requests Frappe-Repos-API SSL-Fehler (Default certifi)"
    show_debug "$PYTHON_REQUESTS_FRAPPE\n\n⚠️ Das ist der install-app-relevante Pfad (certifi).\nAktiver certifi-Pfad:\n$PYTHON_CA_INFO"
  else
    test_fail "Python requests Frappe-Repos-API fehlgeschlagen (Default certifi)"
    show_debug "$PYTHON_REQUESTS_FRAPPE"
  fi
fi

# Vergleichstest: Python requests für Frappe-Repos-API mit System-CA-Bundle
PYTHON_REQUESTS_FRAPPE_SYSTEM_CA=$(cd /home/frappe-user/frappe-bench && REQUESTS_CA_BUNDLE="$SYSTEM_CA_BUNDLE" ./env/bin/python -c "
import requests
import sys
try:
    requests.head('https://api.github.com/repos/frappe/helpdesk', timeout=5)
    sys.exit(0)
except requests.exceptions.SSLError as e:
    print('SSL Error: ' + str(e), file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print('Error: ' + str(e), file=sys.stderr)
    sys.exit(2)
" 2>&1)
PYTHON_REQUESTS_FRAPPE_SYSTEM_CA_EXIT=$?

if [ $PYTHON_REQUESTS_FRAPPE_SYSTEM_CA_EXIT -eq 0 ]; then
  test_pass "Python requests Frappe-Repos-API (System-CA Vergleich)"
else
  if echo "$PYTHON_REQUESTS_FRAPPE_SYSTEM_CA" | grep -qi "SSL\|CERTIFICATE_VERIFY_FAILED"; then
    test_fail "Python requests Frappe-Repos-API SSL-Fehler (System-CA Vergleich)"
    show_debug "$PYTHON_REQUESTS_FRAPPE_SYSTEM_CA\n\nVerwendetes CA-Bundle: $SYSTEM_CA_BUNDLE"
  else
    test_fail "Python requests Frappe-Repos-API fehlgeschlagen (System-CA Vergleich)"
    show_debug "$PYTHON_REQUESTS_FRAPPE_SYSTEM_CA"
  fi
fi

# ------------------------------------------------------------
# 3. HTTPS / TLS – OpenSSL (SAN / Zertifikat)
# ------------------------------------------------------------
test_header "3) Zertifikat Details"

# Test: SSL-Zertifikat mit korrektem SAN
OPENSSL_OUTPUT=$(echo | openssl s_client -connect "$SERVER_HOST":443 -servername "$SERVER_HOST" 2>&1)
if echo "$OPENSSL_OUTPUT" | grep -q "*.az-it.systems"; then
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
if [ $SUDO_TEST -eq 1 ]; then
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
else
  echo
  echo -e "${YELLOW}Node.js sudo-Tests übersprungen. Verwenden Sie -s oder --sudo zum Aktivieren.${NC}"
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
WKHTML_OUTPUT=$(wkhtmltopdf "https://$SERVER_HOST" "$WKHTML_TEST" 2>&1)
if [ -f "$WKHTML_TEST" ] && [ -s "$WKHTML_TEST" ]; then
  test_pass "wkhtmltopdf kann HTTPS-Seite zu PDF konvertieren"
  rm -f "$WKHTML_TEST"
else
  test_fail "wkhtmltopdf HTTPS-zu-PDF Konvertierung fehlgeschlagen"
  show_debug "$WKHTML_OUTPUT"
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

