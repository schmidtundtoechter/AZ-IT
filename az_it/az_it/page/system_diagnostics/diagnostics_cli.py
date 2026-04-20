# -*- coding: utf-8 -*-
import argparse
import sys
from datetime import datetime

from . import diagnostics_core as core


RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
BOLD = "\033[1m"
NC = "\033[0m"


def _print_header(site_host):
    print(f"{BOLD}============================================================{NC}")
    print(f"{BOLD} SYSTEMDIAGNOSE - PDF / TLS / WKHTMLTOPDF / NODE{NC}")
    print(f" Server: {site_host}")
    print(f" Datum: {datetime.now()}")
    print(f" Benutzer: {core.get_system_info()['username']}")
    print(f"{BOLD}============================================================{NC}")
    print()


def _print_results(results, verbose=False):
    for category, payload in results.get("categories", {}).items():
        print()
        print(f"{BLUE}{BOLD}{category}{NC}")
        for test in payload.get("tests", []):
            if test.get("passed"):
                print(f"{GREEN}✓{NC} {test.get('name', '')}")
            else:
                print(f"{RED}✗{NC} {test.get('name', '')}")

            if verbose and test.get("debug"):
                print(f"{YELLOW}Debug-Ausgabe:{NC}")
                print("----------------------------------------")
                print(test["debug"])
                print("----------------------------------------")

    print()
    print(f"{BOLD}============================================================{NC}")
    print(f"{BOLD} ZUSAMMENFASSUNG{NC}")
    print(f"{BOLD}============================================================{NC}")
    print(f"{GREEN}Tests bestanden:{NC} {results.get('tests_passed', 0)}")
    print(f"{RED}Tests fehlgeschlagen:{NC} {results.get('tests_failed', 0)}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Systemdiagnose")
    parser.add_argument(
        "server_name",
        nargs="?",
        help="Optional: Kurzname wie erptest oder voller Hostname",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Zeige Debug-Ausgaben")
    args = parser.parse_args(argv)

    if args.server_name:
        site_host = args.server_name
        if "." not in site_host:
            site_host = f"{site_host}.az-it.systems"
    else:
        site_host = core.resolve_site_host()

    _print_header(site_host)
    results = core.run_diagnostics(
        site_host=site_host,
        run_network_tests=True,
        run_https_tests=True,
        run_cert_tests=True,
        run_node_tests=True,
        run_wkhtml_tests=True,
        run_sudo_node_test=False,
    )
    _print_results(results, verbose=args.verbose)

    return 1 if results.get("tests_failed", 0) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
