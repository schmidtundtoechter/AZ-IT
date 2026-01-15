#!/usr/bin/env bash
set -euo pipefail

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

HOST="${1:-}"
OUTFILE="${2:-}"

if [[ -z "$HOST" || -z "$OUTFILE" ]]; then
  echo -e "${YELLOW}Usage: $0 <hostname> <output-ca-file.crt>${NC}"
  exit 1
fi

TMPDIR="$(mktemp -d)"
CHAIN_FILE="$TMPDIR/chain.pem"

echo -e "${BLUE}▶ Inspecting TLS certificate chain for: ${BOLD}$HOST${NC}"
echo

# Zertifikatskette abrufen
echo -e "${BLUE}▶ Fetching certificate chain...${NC}"
openssl s_client \
  -connect "$HOST:443" \
  -servername "$HOST" \
  -showcerts </dev/null 2>/dev/null \
  | sed -n '/BEGIN CERTIFICATE/,/END CERTIFICATE/p' \
  > "$CHAIN_FILE"

if [[ ! -s "$CHAIN_FILE" ]]; then
  echo -e "${RED}${BOLD}❌ No certificates retrieved.${NC}"
  echo -e "${YELLOW}Possible causes:${NC}"
  echo -e "  ${YELLOW}• Host unreachable or port 443 closed${NC}"
  echo -e "  ${YELLOW}• Invalid hostname${NC}"
  echo -e "  ${YELLOW}• Firewall blocking connection${NC}"
  exit 2
fi

CERT_COUNT=$(grep -c "BEGIN CERTIFICATE" "$CHAIN_FILE")
echo -e "${GREEN}✔ Retrieved $CERT_COUNT certificate(s)${NC}"
echo

# Root-Zertifikat = letztes Zertifikat in der Kette
echo -e "${BLUE}▶ Extracting root certificate...${NC}"
awk '
  /BEGIN CERTIFICATE/ {c++}
  {print > (c ".pem")}
' "$CHAIN_FILE"

ROOT_CERT="${CERT_COUNT}.pem"
cp "$ROOT_CERT" "$OUTFILE"

echo -e "${GREEN}✔ Root CA written to: ${BOLD}$OUTFILE${NC}"
echo

# Informationen zur Root-CA
echo -e "${BLUE}▶ Root CA details:${NC}"
openssl x509 -in "$OUTFILE" -noout -subject -issuer -dates -fingerprint
echo

# Prüfen, ob CA bereits bekannt ist
echo -e "${BLUE}▶ Checking if Root CA is already trusted...${NC}"
if grep -q "$(openssl x509 -in "$OUTFILE" -noout -fingerprint | cut -d= -f2)" /etc/ssl/certs/ca-certificates.crt; then
  echo -e "${GREEN}✔ Root CA is already trusted by the system.${NC}"
else
  echo -e "${RED}⚠ Root CA is NOT trusted by the system.${NC}"
  echo
  echo -e "${CYAN}${BOLD}To install it system-wide:${NC}"
  echo -e "  ${CYAN}sudo cp $OUTFILE /usr/local/share/ca-certificates/${NC}"
  echo -e "  ${CYAN}sudo update-ca-certificates${NC}"
fi

echo
echo -e "${BLUE}▶ Certificate chain interpretation:${NC}"
for i in $(seq 1 "$CERT_COUNT"); do
  echo -e "${BOLD}---- Certificate $i ----${NC}"
  openssl x509 -in "$i.pem" -noout -subject -issuer
done

rm -rf "$TMPDIR"
