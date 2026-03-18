#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backup-Sync-Script: Remote → Lokal
Löst auf einem Remote-Frappe-System ein Backup aus und überträgt die
Backup-Dateien anschließend auf die lokale Maschine.

Verwendung:
    python3 backup_sync.py [--system live|test]

Voraussetzungen:
    - SSH-Zugriff auf das Remote-System (Key-basiert empfohlen)
    - Schreibrecht auf dem lokalen Download-Verzeichnis
"""

import argparse
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

SYSTEMS = {
    "live": {
        "host": "erp.az-it.systems",
        "ssh_user": "frappe-user",
    },
    "test": {
        "host": "erptest.az-it.systems",
        "ssh_user": "frappe-user",
    },
}

# Lokales Zielverzeichnis für Backup-Dateien
LOCAL_BACKUP_DIR = Path("~/frappe-backups").expanduser()

# SSH-Timeout in Sekunden
SSH_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def run_local(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Führt einen lokalen Befehl aus und gibt das Ergebnis zurück."""
    print(f"  [lokal] {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def ssh_run(host: str, user: str, remote_cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Führt einen Befehl per SSH auf dem Remote-System aus."""
    cmd = [
        "ssh",
        "-o", "ConnectTimeout=30",
        "-o", "BatchMode=yes",          # kein interaktiver Passwort-Prompt
        f"{user}@{host}",
        remote_cmd,
    ]
    print(f"  [ssh {host}] {remote_cmd}")
    return subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=SSH_TIMEOUT)


# ---------------------------------------------------------------------------
# Schritt 1: SSH-Verbindung prüfen
# ---------------------------------------------------------------------------

def check_ssh_connection(host: str, user: str) -> bool:
    """Prüft, ob eine SSH-Verbindung zum Remote-System möglich ist."""
    print(f"\n[1/1] Prüfe SSH-Verbindung zu {user}@{host} ...")
    result = ssh_run(host, user, "echo OK", check=False)
    if result.returncode == 0 and "OK" in result.stdout:
        print("      ✓ SSH-Verbindung erfolgreich")
        return True
    else:
        print(f"      ✗ SSH-Verbindung fehlgeschlagen:")
        print(f"        stdout: {result.stdout.strip()}")
        print(f"        stderr: {result.stderr.strip()}")
        return False


# ---------------------------------------------------------------------------
# Schritt 2: Frappe-Bench-Verzeichnis ermitteln
# ---------------------------------------------------------------------------

def find_bench_dir(host: str, user: str) -> str | None:
    """
    Ermittelt das Bench-Verzeichnis auf dem Remote-System automatisch.
    Sucht nacheinander nach typischen Pfaden und nach dem 'bench'-Prozess.
    """
    print(f"\n[2/2] Ermittle Bench-Verzeichnis auf {host} ...")

    # Methode 1: Typische Standardpfade prüfen
    candidates = [
        "~/frappe-bench",
        "~/bench",
        "/home/frappe/frappe-bench",
        "/opt/frappe-bench",
    ]
    for path in candidates:
        check_cmd = f"test -f {path}/Procfile && echo {path}"
        result = ssh_run(host, user, check_cmd, check=False)
        if result.returncode == 0 and result.stdout.strip():
            bench_dir = result.stdout.strip()
            print(f"      ✓ Bench-Verzeichnis gefunden: {bench_dir}")
            return bench_dir

    # Methode 2: Laufenden bench-Prozess auswerten
    result = ssh_run(host, user, "ps aux | grep '[b]ench start'", check=False)
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            parts = line.split()
            # Der Prozess wird typischerweise aus dem Bench-Verzeichnis gestartet
            for part in parts:
                if "frappe-bench" in part or part.endswith("/bench"):
                    bench_dir = str(Path(part).parent)
                    print(f"      ✓ Bench-Verzeichnis aus Prozess ermittelt: {bench_dir}")
                    return bench_dir

    # Methode 3: 'which bench' und symlink auflösen
    result = ssh_run(host, user, "which bench 2>/dev/null && readlink -f $(which bench)", check=False)
    if result.returncode == 0 and result.stdout.strip():
        bench_bin = result.stdout.strip().splitlines()[-1]
        # bench liegt typischerweise unter <bench-dir>/env/bin/bench
        bench_dir = str(Path(bench_bin).parents[2])
        check_result = ssh_run(host, user, f"test -f {bench_dir}/Procfile && echo {bench_dir}", check=False)
        if check_result.returncode == 0 and check_result.stdout.strip():
            bench_dir = check_result.stdout.strip()
            print(f"      ✓ Bench-Verzeichnis über 'which bench' gefunden: {bench_dir}")
            return bench_dir

    print("      ✗ Bench-Verzeichnis konnte nicht automatisch ermittelt werden.")
    return None


# ---------------------------------------------------------------------------
# Schritt 3: Backup auf Remote-System auslösen
# ---------------------------------------------------------------------------

def trigger_backup(host: str, user: str, bench_dir: str) -> bool:
    """
    Löst auf dem Remote-System ein vollständiges Frappe-Backup inkl. Files aus.
    """
    print(f"\n[3/3] Löse Backup auf {host} aus ...")

    # Aktive Site ermitteln (erste Site in sites/currentsite.txt oder sites-Verzeichnis)
    result = ssh_run(
        host, user,
        f"cat {bench_dir}/sites/currentsite.txt 2>/dev/null || "
        f"ls {bench_dir}/sites/ | grep -v assets | grep -v apps.txt | grep -v apps.json | grep -v common_site_config.json | head -1",
        check=False,
    )
    site = result.stdout.strip().splitlines()[0] if result.returncode == 0 and result.stdout.strip() else None

    if not site:
        print("      ✗ Konnte aktive Site nicht ermitteln.")
        return False

    print(f"      Site: {site}")

    # bench-Binary ermitteln (kann im PATH oder unter env/bin liegen)
    bench_bin_result = ssh_run(host, user, f"which bench 2>/dev/null || echo {bench_dir}/env/bin/bench", check=False)
    bench_bin = bench_bin_result.stdout.strip().splitlines()[0] if bench_bin_result.returncode == 0 and bench_bin_result.stdout.strip() else "bench"

    # Backup auslösen (mit --with-files = DB + private Files + public Files)
    backup_cmd = f"cd {bench_dir} && {bench_bin} --site {site} backup --with-files 2>&1"
    result = ssh_run(host, user, backup_cmd, check=False)

    if result.returncode == 0:
        print("      ✓ Backup erfolgreich ausgelöst")
        print(f"      Ausgabe:\n{result.stdout.strip()}")
        return True
    else:
        print("      ✗ Backup fehlgeschlagen:")
        print(f"        {result.stdout.strip()}")
        print(f"        {result.stderr.strip()}")
        return False


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def select_system() -> dict:
    """Fragt den Benutzer interaktiv nach dem Zielsystem."""
    print("Welches System soll gesichert werden?")
    print("  [1] Live-System  (erp.az-it.systems)")
    print("  [2] Test-System  (erptest.az-it.systems)")
    choice = input("Auswahl [1/2]: ").strip()
    if choice == "2":
        return SYSTEMS["test"]
    return SYSTEMS["live"]


def main():
    parser = argparse.ArgumentParser(description="Frappe Backup-Sync: Remote → Lokal")
    parser.add_argument(
        "--system",
        choices=["live", "test"],
        help="Zielsystem (live oder test). Ohne Angabe: interaktive Auswahl.",
    )
    args = parser.parse_args()

    system = SYSTEMS[args.system] if args.system else select_system()
    host = system["host"]
    user = system["ssh_user"]

    print(f"\n=== Backup-Sync für {host} ===")

    # Schritt 1: SSH-Verbindung prüfen
    if not check_ssh_connection(host, user):
        print("\nAbbruch: Keine SSH-Verbindung möglich.")
        sys.exit(1)

    # Schritt 2: Bench-Verzeichnis ermitteln
    bench_dir = find_bench_dir(host, user)
    if not bench_dir:
        bench_dir = input("\nBitte Bench-Verzeichnis manuell eingeben: ").strip()
        if not bench_dir:
            print("Abbruch.")
            sys.exit(1)

    # Schritt 3: Backup auslösen
    if not trigger_backup(host, user, bench_dir):
        print("\nAbbruch: Backup konnte nicht ausgelöst werden.")
        sys.exit(1)

    print("\n✓ Backup erfolgreich abgeschlossen.")
    print("  Nächster Schritt: Backup-Dateien herunterladen (noch nicht implementiert).")


if __name__ == "__main__":
    main()
