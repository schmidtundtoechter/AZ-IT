# -*- coding: utf-8 -*-
import os
import re
import socket
import ssl
import subprocess
from urllib.parse import urlparse

import certifi


SYSTEM_CA_BUNDLE = "/etc/ssl/certs/ca-certificates.crt"
DEFAULT_BENCH_DIR = "/home/frappe-user/frappe-bench"
ERPTEST_HOST = "erptest.az-it.systems"  # Fallback wenn kein Site-Kontext vorhanden


def run_command(cmd, timeout=10, shell=True):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def get_system_info():
    """Get hostname and current username."""
    returncode, username, _stderr = run_command("whoami")
    if returncode != 0 or not username.strip():
        username = "unknown"
    else:
        username = username.strip()

    return {
        "hostname": socket.gethostname(),
        "username": username,
    }


def resolve_site_host(frappe_site=None, bench_dir=DEFAULT_BENCH_DIR):
    """Resolve site host directly from bench site name."""
    def _clean(value):
        return (value or "").strip()

    # 1. Direkt aus Frappe-Kontext (frappe.local.site)
    if _clean(frappe_site):
        return _clean(frappe_site)

    # 2. Umgebungsvariable
    env_site = _clean(os.environ.get("FRAPPE_SITE"))
    if env_site:
        return env_site

    # 3. currentsite.txt
    current_site_file = os.path.join(bench_dir, "sites", "currentsite.txt")
    if os.path.exists(current_site_file):
        try:
            with open(current_site_file, "r", encoding="utf-8") as f:
                for line in f:
                    site = _clean(line)
                    if site:
                        return site
        except OSError:
            pass

    # 4. Einziger Site-Ordner im Bench
    sites_dir = os.path.join(bench_dir, "sites")
    if os.path.isdir(sites_dir):
        try:
            ignored = {"assets", "common_site_config.json", "apps.txt", "apps.json", "currentsite.txt"}
            candidates = [
                entry for entry in os.listdir(sites_dir)
                if entry not in ignored
                and os.path.isdir(os.path.join(sites_dir, entry))
                and "." in entry
            ]
            if len(candidates) == 1:
                return candidates[0]
        except OSError:
            pass

    return ERPTEST_HOST


def _is_local_host(host):
    return host.endswith(".localhost") or host == "localhost"


def _get_own_ip():
    own_ip = ""

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        own_ip = s.getsockname()[0]
        s.close()
    except Exception:
        returncode, stdout, _stderr = run_command("hostname -I")
        if returncode == 0 and stdout.strip():
            own_ip = stdout.strip().split()[0]

    if own_ip:
        return own_ip

    returncode, stdout, _stderr = run_command("ip addr show")
    if returncode == 0:
        ips = re.findall(r"inet (\d+\.\d+\.\d+\.\d+)", stdout)
        for ip in ips:
            if ip != "127.0.0.1":
                return ip

    return ""


def test_ping(name, host):
    if _is_local_host(host):
        return {"name": f"{name} -> 127.0.0.1 (lokal)", "passed": True, "debug": ""}

    returncode, stdout, stderr = run_command(f"ping -c 1 -W 2 {host}")
    passed = returncode == 0
    debug = stdout + stderr if not passed else ""
    return {"name": name, "passed": passed, "debug": debug}


def test_dns(name, host):
    own_ip = _get_own_ip()

    if _is_local_host(host):
        return {"name": f"{name} -> 127.0.0.1 (lokal)", "passed": True, "debug": ""}

    returncode, stdout, stderr = run_command(f"getent hosts {host}")
    if returncode != 0 or not stdout.strip():
        debug = (
            f"Erwartete IP (eigene): {own_ip}\n"
            f"DNS-Ausgabe: {stdout + stderr}\n\n"
            f"Fehler: {host} konnte nicht aufgeloest werden"
        )
        return {"name": name, "passed": False, "debug": debug}

    resolved_ip = stdout.strip().split()[0]
    if own_ip and resolved_ip == own_ip:
        return {"name": f"{name} -> {own_ip}", "passed": True, "debug": ""}

    debug = (
        f"Erwartete IP (eigene): {own_ip}\n"
        f"Aufgeloeste IP: {resolved_ip}\n\n"
        f"Vollstaendige DNS-Ausgabe:\n{stdout}"
    )
    return {"name": name, "passed": False, "debug": debug}


def test_https(name, url):
    host = urlparse(url).hostname or ""
    if _is_local_host(host):
        return {"name": f"{name} (uebersprungen - lokale Dev-Domain)", "passed": True, "debug": ""}

    returncode, stdout, _stderr = run_command(f"curl -sS -I {url}")
    passed = returncode == 0 and (
        "200" in stdout or "301" in stdout or "302" in stdout or "404" in stdout
    )
    if passed:
        return {"name": name, "passed": True, "debug": ""}

    _returncode_v, stdout_v, stderr_v = run_command(f"curl -Iv {url}")
    debug = stdout_v + stderr_v
    if "self-signed certificate" in debug:
        debug += f"\n\nHinweis: Fuehren Sie './inspect-ca.sh {host} root-ca.crt' aus."

    return {"name": name, "passed": False, "debug": debug}


def test_ssl_cert(name, host):
    if _is_local_host(host):
        return {"name": f"{name} (uebersprungen - lokale Dev-Domain)", "passed": True, "debug": ""}

    cmd = f"echo | openssl s_client -connect {host}:443 -servername {host} 2>&1"
    _returncode, stdout, _stderr = run_command(cmd)
    passed = "*.az-it.systems" in stdout
    return {"name": name, "passed": passed, "debug": "" if passed else stdout}


def test_ssl_validation(name, host):
    if _is_local_host(host):
        return {"name": f"{name} (uebersprungen - lokale Dev-Domain)", "passed": True, "debug": ""}

    cmd = f"echo | openssl s_client -connect {host}:443 -servername {host} 2>&1"
    _returncode, stdout, _stderr = run_command(cmd)
    passed = "Verify return code: 0 (ok)" in stdout
    return {"name": name, "passed": passed, "debug": "" if passed else stdout}


def test_node_version(name):
    returncode, stdout, stderr = run_command("node -v")
    passed = returncode == 0 and stdout.strip().startswith("v")
    if passed:
        name = f"{name}: {stdout.strip()}"
    return {"name": name, "passed": passed, "debug": "" if passed else stderr}


def test_node_sudo_version(name):
    user_rc, user_out, user_err = run_command("node -v")
    if user_rc != 0 or not user_out.strip().startswith("v"):
        return {
            "name": name,
            "passed": False,
            "debug": f"User Node.js nicht verfuegbar\n{user_err}",
        }

    sudo_rc, sudo_out, sudo_err = run_command("sudo node -v")
    if sudo_rc != 0 or not sudo_out.strip().startswith("v"):
        return {
            "name": name,
            "passed": False,
            "debug": f"sudo Node.js nicht verfuegbar\n{sudo_err}",
        }

    user_major = re.sub(r"^v(\d+).*$", r"\1", user_out.strip())
    sudo_major = re.sub(r"^v(\d+).*$", r"\1", sudo_out.strip())
    if user_major == sudo_major:
        return {
            "name": f"{name}: {sudo_out.strip()}",
            "passed": True,
            "debug": "",
        }

    return {
        "name": name,
        "passed": False,
        "debug": f"Version unterschiedlich: User={user_out.strip()} sudo={sudo_out.strip()}",
    }


def test_wkhtmltopdf_version(name):
    returncode, stdout, stderr = run_command("wkhtmltopdf --version")
    passed = returncode == 0 and "wkhtmltopdf" in (stdout + stderr)

    required_version = "0.12.6.1 (with patched qt)"
    if passed:
        passed = required_version in (stdout + stderr)
        if passed:
            name = f"{name}: Version {required_version} (empfohlen)"
        else:
            version_match = re.search(r"(\d+\.\d+[\d.]*(?: \(with patched qt\))?)", stdout + stderr)
            if version_match:
                name = f"{name}: {version_match.group(1)} (nicht empfohlen, erwartet: {required_version})"

    return {"name": name, "passed": passed, "debug": "" if passed else stderr}


def test_wkhtmltopdf_https(name, host):
    test_file = "/tmp/wkhtml_test.pdf"
    is_local = _is_local_host(host)
    scheme = "http" if is_local else "https"
    name = name.replace("HTTPS", scheme.upper())

    if os.path.exists(test_file):
        os.remove(test_file)

    _returncode, stdout, stderr = run_command(f"wkhtmltopdf {scheme}://{host} {test_file}")
    passed = os.path.exists(test_file) and os.path.getsize(test_file) > 0
    debug = "" if passed else stdout + stderr

    if os.path.exists(test_file):
        os.remove(test_file)

    return {"name": name, "passed": passed, "debug": debug}


def _requests_head(url, verify=None):
    import requests

    kwargs = {"timeout": 5}
    if verify is not None:
        kwargs["verify"] = verify
    requests.head(url, **kwargs)


def test_python_ca_bundle_info(name):
    debug = (
        f"certifi: {certifi.where()}\n"
        f"REQUESTS_CA_BUNDLE: {os.environ.get('REQUESTS_CA_BUNDLE', '(nicht gesetzt)')}\n"
        f"SSL_CERT_FILE: {os.environ.get('SSL_CERT_FILE', '(nicht gesetzt)')}\n"
        f"OpenSSL: {ssl.OPENSSL_VERSION}"
    )
    return {"name": name, "passed": True, "debug": debug}


def test_python_requests_default(name, url):
    try:
        _requests_head(url)
        return {"name": name, "passed": True, "debug": ""}
    except Exception as e:
        debug = (
            f"Python requests Error: {str(e)}\n\n"
            f"certifi: {certifi.where()}\n"
            f"REQUESTS_CA_BUNDLE: {os.environ.get('REQUESTS_CA_BUNDLE', '(nicht gesetzt)')}\n"
            f"SSL_CERT_FILE: {os.environ.get('SSL_CERT_FILE', '(nicht gesetzt)')}\n\n"
            "Hinweis: Das ist der Default-certifi Pfad."
        )
        return {"name": name, "passed": False, "debug": debug}


def test_python_requests_system_ca(name, url, system_ca_bundle=SYSTEM_CA_BUNDLE):
    try:
        _requests_head(url, verify=system_ca_bundle)
        return {
            "name": name,
            "passed": True,
            "debug": f"Verwendetes CA-Bundle: {system_ca_bundle}",
        }
    except Exception as e:
        debug = (
            f"Python requests Error: {str(e)}\n\n"
            f"Verwendetes CA-Bundle: {system_ca_bundle}\n"
            "System-CA-Vergleich fehlgeschlagen."
        )
        return {"name": name, "passed": False, "debug": debug}


def run_diagnostics(
    site_host,
    run_network_tests=True,
    run_https_tests=True,
    run_cert_tests=True,
    run_node_tests=True,
    run_wkhtml_tests=True,
    run_sudo_node_test=False,
    system_ca_bundle=SYSTEM_CA_BUNDLE,
):
    results = {
        "tests_passed": 0,
        "tests_failed": 0,
        "categories": {},
    }

    if run_network_tests:
        network_tests = [
            test_ping("GitHub erreichbar", "github.com"),
            test_ping(f"{site_host} erreichbar", site_host),
            test_ping("deb.nodesource.com erreichbar", "deb.nodesource.com"),
            test_dns(f"DNS-Aufloesung fuer {site_host}", site_host),
        ]
        results["categories"]["1) Netzwerk & DNS Tests"] = {"tests": network_tests}

    if run_https_tests:
        https_tests = [
            test_https("deb.nodesource.com HTTPS Verbindung", "https://deb.nodesource.com"),
            test_https("GitHub HTTPS Verbindung", "https://github.com"),
            test_https(f"{site_host} HTTPS Verbindung", f"https://{site_host}"),
            test_https("fonts.googleapis.com HTTPS Verbindung", "https://fonts.googleapis.com"),
            test_https("fonts.gstatic.com HTTPS Verbindung", "https://fonts.gstatic.com"),
            test_https("www.google.com HTTPS Verbindung (Vergleichstest)", "https://www.google.com"),
            test_python_ca_bundle_info("Python CA-Bundle Info (certifi vs Umgebungsvariablen)"),
            test_python_requests_default(
                "Python requests GitHub HTTPS (Default certifi, fuer Frappe)",
                "https://api.github.com",
            ),
            test_python_requests_system_ca(
                "Python requests GitHub HTTPS (System-CA Vergleich)",
                "https://api.github.com",
                system_ca_bundle=system_ca_bundle,
            ),
            test_python_requests_default(
                "Python requests Frappe-Repos-API (Default certifi, bench install-app Test)",
                "https://api.github.com/repos/frappe/helpdesk",
            ),
            test_python_requests_system_ca(
                "Python requests Frappe-Repos-API (System-CA Vergleich)",
                "https://api.github.com/repos/frappe/helpdesk",
                system_ca_bundle=system_ca_bundle,
            ),
        ]
        results["categories"]["2) HTTPS / TLS Tests"] = {"tests": https_tests}

    if run_cert_tests:
        cert_tests = [
            test_ssl_cert("SSL-Zertifikat mit korrektem SAN", site_host),
            test_ssl_validation("SSL-Zertifikat Validierung erfolgreich", site_host),
        ]
        results["categories"]["3) Zertifikat Details"] = {"tests": cert_tests}

    if run_node_tests:
        node_tests = [test_node_version("Node.js verfuegbar")]
        if run_sudo_node_test:
            node_tests.append(test_node_sudo_version("sudo Node.js Version stimmt ueberein"))
        results["categories"]["4) Node.js Umgebung"] = {"tests": node_tests}

    if run_wkhtml_tests:
        wkhtml_tests = [
            test_wkhtmltopdf_version("wkhtmltopdf verfuegbar"),
            test_wkhtmltopdf_https("wkhtmltopdf kann HTTPS-Seite zu PDF konvertieren", site_host),
        ]
        results["categories"]["5) wkhtmltopdf"] = {"tests": wkhtml_tests}

    for category in results["categories"].values():
        for test in category["tests"]:
            if test["passed"]:
                results["tests_passed"] += 1
            else:
                results["tests_failed"] += 1

    return results
