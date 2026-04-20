# -*- coding: utf-8 -*-
import frappe

from . import diagnostics_core as core


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


@frappe.whitelist(allow_guest=True)
def get_system_info():
    """Get basic system information."""
    return core.get_system_info()


@frappe.whitelist(allow_guest=True)
def run_diagnostics(
    run_network_tests=True,
    run_https_tests=True,
    run_cert_tests=True,
    run_node_tests=True,
    run_wkhtml_tests=True,
):
    """Run system diagnostics tests using shared diagnostics core."""
    try:
        frappe_site = frappe.local.site
    except AttributeError:
        frappe_site = None

    site_host = core.resolve_site_host(frappe_site=frappe_site)

    return core.run_diagnostics(
        site_host=site_host,
        run_network_tests=_as_bool(run_network_tests),
        run_https_tests=_as_bool(run_https_tests),
        run_cert_tests=_as_bool(run_cert_tests),
        run_node_tests=_as_bool(run_node_tests),
        run_wkhtml_tests=_as_bool(run_wkhtml_tests),
        run_sudo_node_test=False,
    )
