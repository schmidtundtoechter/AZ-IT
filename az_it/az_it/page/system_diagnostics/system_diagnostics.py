# -*- coding: utf-8 -*-
import frappe
import subprocess
import socket
import os
from frappe import _


@frappe.whitelist(allow_guest=True)
def get_system_info():
    """Get basic system information"""
    return {
        'hostname': socket.gethostname(),
        'username': os.getenv('USER', 'unknown')
    }


@frappe.whitelist(allow_guest=True)
def run_diagnostics(run_network_tests=True, run_https_tests=True, run_cert_tests=True, 
                    run_node_tests=True, run_wkhtml_tests=True):
    """Run system diagnostics tests"""
    
    results = {
        'tests_passed': 0,
        'tests_failed': 0,
        'categories': {}
    }
    
    # Kategorie 1: Netzwerk & DNS
    if run_network_tests:
        network_tests = []
        network_tests.append(test_ping('GitHub erreichbar', 'github.com'))
        network_tests.append(test_ping('erptest.az-it.systems erreichbar', 'erptest.az-it.systems'))
        network_tests.append(test_ping('deb.nodesource.com erreichbar', 'deb.nodesource.com'))
        network_tests.append(test_https('deb.nodesource.com HTTPS Verbindung', 'https://deb.nodesource.com'))
        network_tests.append(test_dns('DNS-Auflösung für erptest.az-it.systems', 'erptest.az-it.systems', '10.0.2.126'))
        
        results['categories']['1) Netzwerk & DNS Tests'] = {'tests': network_tests}
    
    # Kategorie 2: HTTPS / TLS
    if run_https_tests:
        https_tests = []
        https_tests.append(test_https('GitHub HTTPS Verbindung', 'https://github.com'))
        https_tests.append(test_https('erptest.az-it.systems HTTPS Verbindung', 'https://erptest.az-it.systems'))
        https_tests.append(test_https('fonts.googleapis.com HTTPS Verbindung', 'https://fonts.googleapis.com'))
        https_tests.append(test_https('fonts.gstatic.com HTTPS Verbindung', 'https://fonts.gstatic.com'))
        https_tests.append(test_https('www.google.com HTTPS Verbindung (Vergleichstest)', 'https://www.google.com'))
        
        results['categories']['2) HTTPS / TLS Tests'] = {'tests': https_tests}
    
    # Kategorie 3: Zertifikat Details
    if run_cert_tests:
        cert_tests = []
        cert_tests.append(test_ssl_cert('SSL-Zertifikat mit korrektem SAN', 'erptest.az-it.systems'))
        
        results['categories']['3) Zertifikat Details'] = {'tests': cert_tests}
    
    # Kategorie 4: Node.js (optional)
    if run_node_tests:
        node_tests = []
        node_tests.append(test_node_version('Node.js verfügbar'))
        
        results['categories']['4) Node.js Umgebung'] = {'tests': node_tests}
    
    # Kategorie 5: wkhtmltopdf
    if run_wkhtml_tests:
        wkhtml_tests = []
        wkhtml_tests.append(test_wkhtmltopdf_version('wkhtmltopdf verfügbar'))
        wkhtml_tests.append(test_wkhtmltopdf_https('wkhtmltopdf kann HTTPS-Seite zu PDF konvertieren'))
    
        results['categories']['5) wkhtmltopdf'] = {'tests': wkhtml_tests}
    
    # Zusammenfassung berechnen
    for category in results['categories'].values():
        for test in category['tests']:
            if test['passed']:
                results['tests_passed'] += 1
            else:
                results['tests_failed'] += 1
    
    return results


def run_command(cmd, shell=True):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, '', 'Command timed out'
    except Exception as e:
        return -1, '', str(e)


def test_ping(name, host):
    """Test if a host is reachable via ping"""
    returncode, stdout, stderr = run_command(f'ping -c 1 -W 2 {host}')
    passed = returncode == 0
    debug = stdout + stderr if not passed else ''
    return {'name': name, 'passed': passed, 'debug': debug}


def test_https(name, url):
    """Test HTTPS connection to a URL"""
    returncode, stdout, stderr = run_command(f'curl -sS -I {url}')
    passed = returncode == 0 and ('200' in stdout or '301' in stdout or '302' in stdout or '404' in stdout)
    
    debug = ''
    if not passed:
        # Verbose output for debugging
        returncode_v, stdout_v, stderr_v = run_command(f'curl -Iv {url}')
        debug = stdout_v + stderr_v
        
        if 'self-signed certificate' in debug:
            debug += f"\n\nHinweis: Führen Sie './inspect-ca.sh {url.replace('https://', '')} root-ca.crt' aus."
    
    return {'name': name, 'passed': passed, 'debug': debug}


def test_dns(name, host, expected_ip):
    """Test DNS resolution"""
    returncode, stdout, stderr = run_command(f'getent hosts {host}')
    passed = returncode == 0 and expected_ip in stdout
    debug = stdout + stderr if not passed else ''
    return {'name': name, 'passed': passed, 'debug': debug}


def test_ssl_cert(name, host):
    """Test SSL certificate"""
    cmd = f'echo | openssl s_client -connect {host}:443 -servername {host} 2>&1'
    returncode, stdout, stderr = run_command(cmd)
    
    passed = '*.az-it.systems' in stdout and 'Verify return code: 0 (ok)' in stdout
    debug = stdout if not passed else ''
    
    return {'name': name, 'passed': passed, 'debug': debug}


def test_node_version(name):
    """Test Node.js version"""
    returncode, stdout, stderr = run_command('node -v')
    passed = returncode == 0 and stdout.strip().startswith('v')
    debug = stderr if not passed else ''
    
    if passed:
        name += f': {stdout.strip()}'
    
    return {'name': name, 'passed': passed, 'debug': debug}


def test_wkhtmltopdf_version(name):
    """Test wkhtmltopdf version"""
    returncode, stdout, stderr = run_command('wkhtmltopdf --version')
    passed = returncode == 0 and 'wkhtmltopdf' in (stdout + stderr)
    
    if passed:
        if '0.12.6' in (stdout + stderr):
            name += ': Version 0.12.6 (empfohlen)'
        else:
            # Extract version
            import re
            version_match = re.search(r'(\d+\.\d+\.\d+)', stdout + stderr)
            if version_match:
                name += f': {version_match.group(1)}'
    
    debug = stderr if not passed else ''
    return {'name': name, 'passed': passed, 'debug': debug}


def test_wkhtmltopdf_https(name):
    """Test wkhtmltopdf HTTPS conversion"""
    test_file = '/tmp/wkhtml_test.pdf'
    
    # Clean up old test file
    if os.path.exists(test_file):
        os.remove(test_file)
    
    returncode, stdout, stderr = run_command(f'wkhtmltopdf https://erptest.az-it.systems {test_file}')
    
    passed = os.path.exists(test_file) and os.path.getsize(test_file) > 0
    debug = stdout + stderr if not passed else ''
    
    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)
    
    return {'name': name, 'passed': passed, 'debug': debug}
