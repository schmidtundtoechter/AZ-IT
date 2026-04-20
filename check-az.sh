#!/usr/bin/env bash
# Dieselbe Umgebung wie der Supervisor-Prozess (supervisor.conf: environment=...)
# damit das Script exakt das testet, was ERPNext tut.

set -u
set -o pipefail

BENCH_DIR="/home/frappe-user/frappe-bench"
PYTHON_BIN="$BENCH_DIR/env/bin/python"
CLI_MODULE="az_it.az_it.page.system_diagnostics.diagnostics_cli"

# Supervisor setzt diese Variablen für alle bench-Prozesse:
export REQUESTS_CA_BUNDLE="/etc/ssl/certs/ca-certificates.crt"
export SSL_CERT_FILE="/etc/ssl/certs/ca-certificates.crt"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Fehler: Python-Interpreter nicht gefunden: $PYTHON_BIN"
  exit 1
fi

cd "$BENCH_DIR" || exit 1
exec "$PYTHON_BIN" -m "$CLI_MODULE" "$@"
