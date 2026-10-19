"""Read the actual site inventory through bench execute (no HTTP endpoint)."""


def get_script_inventory():
    import frappe
    from az_it import __version__

    return {
        "site": frappe.local.site,
        "az_it_version": __version__,
        "installed_apps": frappe.get_installed_apps(),
        "server_script_enabled_config": frappe.conf.get("server_script_enabled"),
        "note": "Record flags only; global server-script settings and scheduler health also affect execution.",
        "client_scripts": frappe.get_all(
            "Client Script", fields=["name", "dt", "enabled"], order_by="name"
        ),
        "server_scripts": frappe.get_all(
            "Server Script",
            fields=["name", "script_type", "reference_doctype", "doctype_event", "event_frequency", "disabled"],
            order_by="name",
        ),
    }
