import frappe


def execute():
    frappe.db.set_single_value("Stock Settings", "clean_description_html", 0)
