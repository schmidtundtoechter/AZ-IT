#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backup-Sync-Script: Remote → Lokal
Löst auf einem Remote-Frappe-System ein Backup aus, überträgt die
Backup-Dateien auf die lokale Maschine und spielt sie in die lokale Site ein.

Verwendung:
    python3 backup_sync.py [--system live|test]

Voraussetzungen:
    - SSH-Zugriff auf das Remote-System (Key-basiert empfohlen)
    - Schreibrecht auf dem lokalen Download-Verzeichnis
"""

import argparse
import json
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
        "local_site": "erp.az-it.localhost",
    },
    "test": {
        "host": "erptest.az-it.systems",
        "ssh_user": "frappe-user",
        "local_site": "erptest.az-it.localhost",
    },
}

# Lokale Bench-Konfiguration
LOCAL_BENCH_DIR = Path("/workspace/development/frappe-bench")

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
        "-o", "BatchMode=yes",
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
    print(f"\n[1/5] Prüfe SSH-Verbindung zu {user}@{host} ...")
    result = ssh_run(host, user, "echo OK", check=False)
    if result.returncode == 0 and "OK" in result.stdout:
        print("      ✓ SSH-Verbindung erfolgreich")
        return True
    else:
        print("      ✗ SSH-Verbindung fehlgeschlagen:")
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
    print(f"\n[2/5] Ermittle Bench-Verzeichnis auf {host} ...")

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
            for part in line.split():
                if "frappe-bench" in part or part.endswith("/bench"):
                    bench_dir = str(Path(part).parent)
                    print(f"      ✓ Bench-Verzeichnis aus Prozess ermittelt: {bench_dir}")
                    return bench_dir

    # Methode 3: 'which bench' und symlink auflösen
    result = ssh_run(host, user, "which bench 2>/dev/null && readlink -f $(which bench)", check=False)
    if result.returncode == 0 and result.stdout.strip():
        bench_bin = result.stdout.strip().splitlines()[-1]
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

def trigger_backup(host: str, user: str, bench_dir: str) -> tuple[bool, list[str]]:
    """
    Löst auf dem Remote-System ein vollständiges Frappe-Backup inkl. Files aus.
    Gibt (erfolg, liste_der_backup_pfade) zurück.
    """
    print(f"\n[3/5] Löse Backup auf {host} aus ...")

    # Aktive Site ermitteln
    result = ssh_run(
        host, user,
        f"cat {bench_dir}/sites/currentsite.txt 2>/dev/null || "
        f"ls {bench_dir}/sites/ | grep -v assets | grep -v apps.txt | grep -v apps.json | grep -v common_site_config.json | head -1",
        check=False,
    )
    site = result.stdout.strip().splitlines()[0] if result.returncode == 0 and result.stdout.strip() else None

    if not site:
        print("      ✗ Konnte aktive Site nicht ermitteln.")
        return False, []

    print(f"      Site: {site}")

    # bench-Binary ermitteln
    bench_bin_result = ssh_run(host, user, f"which bench 2>/dev/null || echo {bench_dir}/env/bin/bench", check=False)
    bench_bin = bench_bin_result.stdout.strip().splitlines()[0] if bench_bin_result.returncode == 0 and bench_bin_result.stdout.strip() else "bench"

    # Backup auslösen (DB + public Files + private Files)
    backup_cmd = f"cd {bench_dir} && {bench_bin} --site {site} backup --with-files 2>&1"
    result = ssh_run(host, user, backup_cmd, check=False)

    if result.returncode != 0:
        print("      ✗ Backup fehlgeschlagen:")
        print(f"        {result.stdout.strip()}")
        print(f"        {result.stderr.strip()}")
        return False, []

    print("      ✓ Backup erfolgreich ausgelöst")
    print(f"      Ausgabe:\n{result.stdout.strip()}")

    # Backup-Dateipfade aus der Ausgabe extrahieren
    backup_files = []
    for line in result.stdout.splitlines():
        if ":" in line and "/backups/" in line:
            raw_path = line.split(":", 1)[1].strip().split()[0]
            if raw_path.startswith("./"):
                raw_path = f"{bench_dir}/sites/{raw_path[2:]}"
            backup_files.append(raw_path)

    print(f"      {len(backup_files)} Backup-Datei(en) erkannt:")
    for f in backup_files:
        print(f"        {f}")

    return True, backup_files


# ---------------------------------------------------------------------------
# Schritt 4: Backup-Dateien herunterladen
# ---------------------------------------------------------------------------

def download_backup_files(host: str, user: str, remote_files: list[str], local_dir: Path) -> list[Path]:
    """
    Überträgt die Backup-Dateien per rsync vom Remote-System auf die lokale Maschine.
    Gibt eine Liste der lokal gespeicherten Dateipfade zurück.
    """
    print(f"\n[4/5] Lade Backup-Dateien nach {local_dir} herunter ...")
    local_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[Path] = []
    for remote_path in remote_files:
        filename = Path(remote_path).name
        local_path = local_dir / filename
        print(f"      → {filename}")

        cmd = [
            "rsync",
            "--progress",
            "-e", "ssh -o BatchMode=yes -o ConnectTimeout=30",
            f"{user}@{host}:{remote_path}",
            str(local_path),
        ]
        result = run_local(cmd, check=False)
        if result.returncode == 0:
            size_mb = local_path.stat().st_size / (1024 * 1024)
            print(f"        ✓ {filename} ({size_mb:.1f} MiB)")
            downloaded.append(local_path)
        else:
            print(f"        ✗ Fehler beim Herunterladen von {filename}:")
            print(f"          {result.stderr.strip()}")

    print(f"\n      {len(downloaded)}/{len(remote_files)} Dateien erfolgreich heruntergeladen.")
    return downloaded


# ---------------------------------------------------------------------------
# Schritt 5: Backup lokal einspielen
# ---------------------------------------------------------------------------

def restore_backup_locally(downloaded: list[Path], bench_dir: Path, site: str) -> bool:
    """
    Spielt das heruntergeladene Backup in die lokale Frappe-Site ein.
    """
    print(f"\n[5/5] Spiele Backup in lokale Site '{site}' ein ...")

    # Dateien nach Typ sortieren
    db_file = next((f for f in downloaded if "database" in f.name and f.suffix == ".gz"), None)
    config_file = next((f for f in downloaded if "site_config_backup" in f.name), None)
    public_files = next((f for f in downloaded if f.name.endswith("-files.tar") and "private" not in f.name), None)
    private_files = next((f for f in downloaded if "private-files" in f.name), None)

    if not db_file:
        print("      ✗ Keine Datenbank-Backup-Datei (.sql.gz) gefunden.")
        return False

    # bench-Binary lokal vorab ermitteln (wird auch für new-site benötigt)
    bench_bin_result = run_local(["which", "bench"], check=False)
    bench_bin = bench_bin_result.stdout.strip() if bench_bin_result.returncode == 0 else str(bench_dir / "env" / "bin" / "bench")

    # Lokale Site anlegen falls nicht vorhanden
    site_dir = bench_dir / "sites" / site
    if not site_dir.exists():
        print(f"      Site '{site}' existiert nicht – lege sie an ...")
        new_site_result = run_local(
            [bench_bin, "new-site", site, "--no-mariadb-socket", "--admin-password", "admin"],
            check=False,
        )
        if new_site_result.returncode != 0:
            print(f"      ✗ Site '{site}' konnte nicht angelegt werden:")
            print(f"        {new_site_result.stdout.strip()}")
            print(f"        {new_site_result.stderr.strip()}")
            return False
        print(f"      ✓ Site '{site}' erfolgreich angelegt")

    # Datenbank + Files einspielen
    print(f"      → Datenbank: {db_file.name}")
    restore_cmd = [bench_bin, "--site", site, "restore", str(db_file)]
    if public_files:
        restore_cmd += ["--with-public-files", str(public_files)]
    if private_files:
        restore_cmd += ["--with-private-files", str(private_files)]

    result = run_local(restore_cmd, check=False)
    if result.returncode != 0:
        print("      ✗ Restore fehlgeschlagen:")
        print(f"        {result.stdout.strip()}")
        print(f"        {result.stderr.strip()}")
        return False

    print("      ✓ Datenbank erfolgreich eingespielt")

    # Site-Konfiguration: nur sichere Keys aus Remote-Config übernehmen
    if config_file:
        local_config = bench_dir / "sites" / site / "site_config.json"
        try:
            with open(config_file) as f:
                remote_cfg = json.load(f)
            safe_keys = {"maintenance_mode", "pause_scheduler", "limits"}
            if local_config.exists():
                with open(local_config) as f:
                    local_cfg = json.load(f)
                for key in safe_keys:
                    if key in remote_cfg:
                        local_cfg[key] = remote_cfg[key]
                with open(local_config, "w") as f:
                    json.dump(local_cfg, f, indent=1)
                print("      ✓ Site-Konfiguration (sichere Keys) übernommen")
        except Exception as e:
            print(f"      ⚠ Site-Konfiguration konnte nicht übernommen werden: {e}")

    # Migrate ausführen
    print("      → Führe bench migrate aus ...")
    migrate_result = run_local([bench_bin, "--site", site, "migrate"], check=False)
    if migrate_result.returncode == 0:
        print("      ✓ Migration erfolgreich")
    else:
        print("      ⚠ Migration mit Warnungen abgeschlossen:")
        print(f"        {migrate_result.stdout[-500:].strip()}")

    return True


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
    local_site = system["local_site"]

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
    success, backup_files = trigger_backup(host, user, bench_dir)
    if not success:
        print("\nAbbruch: Backup konnte nicht ausgelöst werden.")
        sys.exit(1)

    # Schritt 4: Backup-Dateien herunterladen
    local_dir = LOCAL_BACKUP_DIR / host
    downloaded = download_backup_files(host, user, backup_files, local_dir)
    if not downloaded:
        print("\nAbbruch: Keine Backup-Dateien heruntergeladen.")
        sys.exit(1)

    # Schritt 5: Backup lokal einspielen
    if not restore_backup_locally(downloaded, LOCAL_BENCH_DIR, local_site):
        print("\nAbbruch: Restore fehlgeschlagen.")
        sys.exit(1)

    print("\n✓ Backup-Sync vollständig abgeschlossen.")
    print(f"  Lokale Site '{local_site}' wurde aktualisiert.")
    print("  Nächster Schritt: App-Versionen vergleichen (noch nicht implementiert).")


if __name__ == "__main__":
    main()
