#!/usr/bin/env bash

set -u
set -o pipefail

BENCH_DIR="/home/frappe-user/frappe-bench"
PYTHON_BIN="$BENCH_DIR/env/bin/python"
CLI_MODULE="az_it.az_it.page.system_diagnostics.diagnostics_cli"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Fehler: Python-Interpreter nicht gefunden: $PYTHON_BIN"
  exit 1
fi

cd "$BENCH_DIR" || exit 1
exec "$PYTHON_BIN" -m "$CLI_MODULE" "$@"
