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

def run_local(cmd: list[str], check: bool = True, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Führt einen lokalen Befehl aus und gibt das Ergebnis zurück."""
    print(f"  [lokal] {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, check=check, cwd=cwd)


def run_local_stream(cmd: list[str], cwd: Path | None = None) -> int:
    """Führt einen lokalen Befehl aus und streamt die Ausgabe live (für lange Prozesse)."""
    print(f"  [lokal] {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd)
    for line in proc.stdout:
        print(f"        {line}", end="")
    proc.wait()
    return proc.returncode


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
        result = run_local_stream(cmd)
        if result == 0:
            size_mb = local_path.stat().st_size / (1024 * 1024)
            print(f"        ✓ {filename} ({size_mb:.1f} MiB)")
            downloaded.append(local_path)
        else:
            print(f"        ✗ Fehler beim Herunterladen von {filename}")

    print(f"\n      {len(downloaded)}/{len(remote_files)} Dateien erfolgreich heruntergeladen.")
    return downloaded


# ---------------------------------------------------------------------------
# Backup-Rotation: alte Sets löschen
# ---------------------------------------------------------------------------

def cleanup_old_backups(local_dir: Path, keep: int = 3) -> None:
    """
    Löscht alte Backup-Sets in local_dir und behält nur die neuesten `keep` Sets.
    Ein Set = alle Dateien mit gleichem Zeitstempel-Prefix (erste 15 Zeichen).
    """
    if not local_dir.exists():
        return

    # Alle Zeitstempel-Prefixes ermitteln (z.B. "20260318_160131")
    timestamps: set[str] = set()
    for f in local_dir.iterdir():
        if f.is_file() and len(f.name) >= 15:
            timestamps.add(f.name[:15])

    sorted_ts = sorted(timestamps)
    to_delete = sorted_ts[:-keep] if len(sorted_ts) > keep else []

    if not to_delete:
        return

    print(f"\n      Bereinige alte Backups (behalte {keep} neueste Sets) ...")
    for ts in to_delete:
        for f in local_dir.glob(f"{ts}*"):
            f.unlink()
            print(f"      🗑  {f.name} gelöscht")


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

    # Lokale Site droppen und neu anlegen, damit keine veralteten Datensätze im Restore verbleiben
    site_dir = bench_dir / "sites" / site
    if site_dir.exists():
        print(f"      Site '{site}' existiert – wird vor dem Restore gelöscht (sauberer Ausgangszustand) ...")
        drop_result = run_local(
            [bench_bin, "drop-site", site, "--no-backup", "--force", "--mariadb-root-password", "123"],
            check=False,
        )
        if drop_result.returncode != 0:
            print(f"      ⚠ Site konnte nicht gedroppt werden (wird trotzdem fortgefahren):")
            print(f"        {drop_result.stdout.strip()}")
            print(f"        {drop_result.stderr.strip()}")
        else:
            print(f"      ✓ Alte Site gelöscht")

    print(f"      Lege Site '{site}' neu an ...")
    new_site_result = run_local(
        [bench_bin, "new-site", site, "--no-mariadb-socket", "--admin-password", "admin", "--mariadb-root-password", "123"],
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
    restore_cmd = [bench_bin, "--site", site, "restore", str(db_file), "--force", "--mariadb-root-password", "123"]
    if public_files:
        restore_cmd += ["--with-public-files", str(public_files)]
    if private_files:
        restore_cmd += ["--with-private-files", str(private_files)]

    rc = run_local_stream(restore_cmd)
    if rc != 0:
        print("      \u2717 Restore fehlgeschlagen (siehe Ausgabe oben).")
        return False

    print("      ✓ Datenbank erfolgreich eingespielt")

    # /etc/hosts-Einträge sicherstellen (wkhtmltopdf braucht DNS-Auflösung für lokale Sites)
    _ensure_hosts_entry(site)

    # Migrate ausführen
    print("      → Führe bench migrate aus ...")
    rc = run_local_stream([bench_bin, "--site", site, "migrate"])
    if rc == 0:
        print("      \u2713 Migration erfolgreich")
    else:
        print("      \u26a0 Migration mit Fehlern abgeschlossen (siehe Ausgabe oben).")

    # Scheduler explizit aktivieren – bench restore setzt pause_scheduler:1 automatisch
    print("      → Aktiviere Scheduler ...")
    rc_sched = run_local_stream([bench_bin, "--site", site, "scheduler", "enable"])
    if rc_sched == 0:
        print("      ✓ Scheduler aktiviert")
    else:
        print("      ⚠ Scheduler konnte nicht aktiviert werden")

    # Site-Konfiguration NACH migrate setzen – migrate überschreibt die Config sonst
    local_config = bench_dir / "sites" / site / "site_config.json"
    try:
        if local_config.exists():
            with open(local_config) as f:
                local_cfg = json.load(f)
        else:
            local_cfg = {}

        # Lokalen host_name immer setzen (wird durch restore/migrate überschrieben)
        local_cfg["host_name"] = f"http://{site}:8000"
        # Sicherstellen dass Scheduler und Wartungsmodus lokal deaktiviert sind
        local_cfg["pause_scheduler"] = 0
        local_cfg["maintenance_mode"] = 0

        # Nur unkritische Keys aus Remote-Config übernehmen (niemals Scheduler/Wartung)
        if config_file:
            try:
                with open(config_file) as f:
                    remote_cfg = json.load(f)
                for key in {"limits"}:
                    if key in remote_cfg:
                        local_cfg[key] = remote_cfg[key]
            except Exception as e:
                print(f"      ⚠ Remote-Konfiguration konnte nicht gelesen werden: {e}")

        with open(local_config, "w") as f:
            json.dump(local_cfg, f, indent=1)
        print(f"      ✓ Site-Konfiguration gesetzt (host_name: http://{site}:8000)")
    except Exception as e:
        print(f"      ⚠ Site-Konfiguration konnte nicht gesetzt werden: {e}")

    return True


def _ensure_hosts_entry(site: str) -> None:
    """Stellt sicher, dass der lokale Site-Hostname in /etc/hosts eingetragen ist.
    wkhtmltopdf benötigt DNS-Auflösung für *.az-it.localhost zum Laden von Bildern."""
    etc_hosts = Path("/etc/hosts")
    try:
        content = etc_hosts.read_text()
        if site not in content:
            entry = f"127.0.0.1 {site}\n"
            result = subprocess.run(
                ["sudo", "tee", "-a", str(etc_hosts)],
                input=entry, capture_output=True, text=True, check=False,
            )
            if result.returncode == 0:
                print(f"      ✓ /etc/hosts: {site} → 127.0.0.1 eingetragen")
            else:
                print(f"      ⚠ /etc/hosts konnte nicht geschrieben werden: {result.stderr.strip()}")
        # else: Eintrag bereits vorhanden
    except Exception as e:
        print(f"      ⚠ /etc/hosts-Prüfung fehlgeschlagen: {e}")


# ---------------------------------------------------------------------------
# Schritt 0: App-Versionen vergleichen und fehlende Apps installieren
# ---------------------------------------------------------------------------

APP_SOURCES: dict[str, str] = {
    # App-Name → git-URL (direkt vom Remote-System ermittelt)
    "az_it":                     "https://github.com/schmidtundtoechter/AZ-IT.git",
    "banking":                   "https://github.com/alyf-de/banking.git",
    "csv_import_hornetsecurity": "https://github.com/schmidtundtoechter/csv_import_hornetsecurity",
    "csv_import_wortmann":       "https://github.com/schmidtundtoechter/csv_import_wortmann",
    "egis_integration":          "https://github.com/schmidtundtoechter/EGIS_app.git",
    "erpnext_datev":             "https://github.com/alyf-de/erpnext_datev.git",
    "eu_einvoice":               "https://github.com/alyf-de/eu_einvoice",
    "helpdesk":                  "https://github.com/frappe/helpdesk",
    "hrms":                      "https://github.com/frappe/hrms",
    "kefiya":                    "https://github.com/jHetzer/kefiya",
    "payments":                  "https://github.com/frappe/payments",
    "pdf_a_3":                   "https://github.com/schmidtundtoechter/pdf_a_3.git",
    "print_designer":            "https://github.com/frappe/frappe_print_designer",
    "serial_number_manager":     "https://github.com/schmidtundtoechter/serial_number_manager.git",
    "studio":                    "https://github.com/frappe/studio",
    "telephony":                 "https://github.com/frappe/telephony.git",
    "wiki":                      "https://github.com/frappe/wiki.git",
}


def compare_and_sync_apps(host: str, user: str, remote_bench_dir: str, local_bench_dir: Path, local_site: str) -> bool:
    """
    Vergleicht installierte Apps auf Remote vs. Lokal.
    Fehlende Apps werden lokal installiert und der Site hinzugefügt.
    ACHTUNG: Auf dem Remote-System wird NICHTS verändert.
    """
    print(f"\n[0/6] Vergleiche App-Versionen (Remote vs. Lokal) ...")

    # Remote-Apps abrufen
    result = ssh_run(
        host, user,
        f"cd {remote_bench_dir} && bench version --format json 2>/dev/null",
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        print("      ✗ Konnte Remote-Apps nicht abrufen.")
        return False

    import json as _json
    try:
        remote_apps = {a["app"]: a for a in _json.loads(result.stdout)}
    except Exception as e:
        print(f"      ✗ Fehler beim Parsen der Remote-App-Liste: {e}")
        return False

    # Lokale Apps abrufen – direkt aus dem Dateisystem (robust gegen Import-Fehler)
    bench_bin_result = run_local(["which", "bench"], check=False)
    bench_bin = bench_bin_result.stdout.strip() if bench_bin_result.returncode == 0 else str(local_bench_dir / "env" / "bin" / "bench")

    local_apps: dict = {}
    apps_dir = local_bench_dir / "apps"
    for app_dir in sorted(apps_dir.iterdir()):
        if not app_dir.is_dir() or app_dir.name.startswith("."):
            continue

        # App-Namen aus dem Verzeichnis ableiten: Unterordner mit __init__.py
        app_name = None
        for sub in app_dir.iterdir():
            if sub.is_dir() and (sub / "__init__.py").exists() and not sub.name.startswith("."):
                # Erster Python-Package-Ordner ist der App-Name
                app_name = sub.name
                break
        if not app_name:
            app_name = app_dir.name  # Fallback: Verzeichnisname

        # Version aus <app>/__init__.py lesen (Frappe-Standard: __version__ = "x.y.z")
        version = "?"
        for version_candidate in [
            app_dir / app_name / "__version__.py",
            app_dir / app_name / "__init__.py",
        ]:
            if version_candidate.exists():
                try:
                    content = version_candidate.read_text()
                    import re as _re
                    m = _re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
                    if m:
                        version = m.group(1)
                        break
                except Exception:
                    pass

        # Branch aus .git/HEAD lesen
        branch = "?"
        git_head = app_dir / ".git" / "HEAD"
        if git_head.exists():
            try:
                head = git_head.read_text().strip()
                if head.startswith("ref: refs/heads/"):
                    branch = head.replace("ref: refs/heads/", "")
                else:
                    branch = head[:7]  # detached HEAD: kurzer commit hash
            except Exception:
                pass

        local_apps[app_name] = {"app": app_name, "version": version, "branch": branch}

    # Tabelle ausgeben
    all_apps = sorted(set(list(remote_apps.keys()) + list(local_apps.keys())))
    print(f"\n      {'App':<30} {'Remote':^20} {'Lokal':^20} Status")
    print(f"      {'-'*30} {'-'*20} {'-'*20} ------")

    missing: list[str] = []
    outdated: list[tuple[str, str, str]] = []

    for app in all_apps:
        r = remote_apps.get(app)
        l = local_apps.get(app)
        r_ver = f"{r['version']} ({r['branch']})" if r else "–"
        l_ver = f"{l['version']} ({l['branch']})" if l else "–"

        if r and not l:
            status = "❌ fehlt lokal"
            missing.append(app)
        elif l and not r:
            status = "⚠ nur lokal"
        elif r and l and r["version"] != l["version"]:
            status = "⚠ Versionsunterschied"
            outdated.append((app, r["branch"], r["version"]))
        else:
            status = "✓ ok"

        print(f"      {app:<30} {r_ver:^20} {l_ver:^20} {status}")

    # Fehlende Apps installieren
    if missing:
        print(f"\n      {len(missing)} App(s) fehlen lokal – werden installiert ...")
        for app in missing:
            url = APP_SOURCES.get(app)
            if not url:
                print(f"      ⚠ Keine bekannte Quelle für '{app}' – bitte manuell installieren.")
                continue

            branch = remote_apps[app].get("branch", "main")
            print(f"\n      → Installiere {app} von {url} (Branch: {branch}) ...")
            rc = run_local_stream([
                bench_bin, "get-app", "--branch", branch, url,
            ])
            if rc != 0:
                print(f"      ✗ Installation von '{app}' fehlgeschlagen.")
                continue

            # App der lokalen Site hinzufügen
            rc2 = run_local_stream([bench_bin, "--site", local_site, "install-app", app])
            if rc2 == 0:
                print(f"      ✓ '{app}' erfolgreich installiert und Site hinzugefügt.")
            else:
                print(f"      ✗ '{app}' installiert, aber Site-Installation fehlgeschlagen.")

    # Veraltete Apps melden (lokales Update obliegt dem Entwickler)
    if outdated:
        print(f"\n      ⚠ {len(outdated)} App(s) mit Versionsunterschied (lokal veraltet):")
        for app, branch, ver in outdated:
            print(f"        - {app}: Remote {ver} ({branch}) – lokal updaten mit: bench update --apps {app}")

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
    parser = argparse.ArgumentParser(
        description="Frappe Backup-Sync: Remote → Lokal",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--system",
        choices=["live", "test"],
        help="Zielsystem (live oder test). Ohne Angabe: interaktive Auswahl.",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Kein neues Backup auslösen – neuestes vorhandenes lokales Backup verwenden.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Kein Download – setzt --skip-backup voraus.",
    )
    parser.add_argument(
        "--skip-restore",
        action="store_true",
        help="Restore und Migrate überspringen.",
    )
    parser.add_argument(
        "--only-apps",
        action="store_true",
        help="Nur App-Versionen vergleichen und fehlende Apps installieren, dann beenden.",
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

    # Schritt 3: App-Versionen vergleichen und fehlende Apps installieren
    compare_and_sync_apps(host, user, bench_dir, LOCAL_BENCH_DIR, local_site)
    if args.only_apps:
        print("\n✓ App-Vergleich abgeschlossen.")
        return

    # Schritt 4: Backup auslösen (optional überspringen)
    local_dir = LOCAL_BACKUP_DIR / host
    if args.skip_backup or args.skip_download:
        # Neuestes vorhandenes Backup verwenden
        existing = sorted(local_dir.glob("*-database.sql.gz")) if local_dir.exists() else []
        if not existing:
            print(f"\nAbbruch: Kein vorhandenes Backup in {local_dir} gefunden.")
            sys.exit(1)
        # Alle 4 Dateien zum gleichen Zeitstempel laden
        latest_ts = existing[-1].name[:15]  # z.B. "20260318_160131"
        downloaded = sorted(local_dir.glob(f"{latest_ts}*"))
        print(f"\n[übersprungen] Verwende vorhandenes Backup vom {latest_ts[:8]} {latest_ts[9:].replace('_', ':')}:")
        for f in downloaded:
            print(f"  {f.name}")
    else:
        backup_files_result = trigger_backup(host, user, bench_dir)
        if not backup_files_result[0]:
            print("\nAbbruch: Backup konnte nicht ausgelöst werden.")
            sys.exit(1)
        _, backup_files = backup_files_result

        # Schritt 5: Backup-Dateien herunterladen
        downloaded = download_backup_files(host, user, backup_files, local_dir)
        if not downloaded:
            print("\nAbbruch: Keine Backup-Dateien heruntergeladen.")
            sys.exit(1)

        # Alte Backup-Sets bereinigen (die letzten 3 behalten)
        cleanup_old_backups(local_dir, keep=3)

    # Schritt 6: Backup lokal einspielen (optional überspringen)
    if not args.skip_restore:
        if not restore_backup_locally(downloaded, LOCAL_BENCH_DIR, local_site):
            print("\nAbbruch: Restore fehlgeschlagen.")
            sys.exit(1)

    print("\n✓ Backup-Sync vollständig abgeschlossen.")
    print(f"  Lokale Site '{local_site}' wurde aktualisiert.")


if __name__ == "__main__":
    main()
