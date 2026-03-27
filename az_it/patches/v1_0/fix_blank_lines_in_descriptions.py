"""
Patch: Replace <p></p> with <p><br></p> in item and sales document descriptions.

Quill editor requires <p><br></p> (not <p></p>) to represent a visible blank line.
Empty <p></p> tags are silently stripped by Quill on save/submit and are also
invisible in print preview.
"""

import frappe


TABLES = [
    ("tabItem", "name"),
    ("tabQuotation Item", "parent"),
    ("tabSales Order Item", "parent"),
    ("tabDelivery Note Item", "parent"),
    ("tabSales Invoice Item", "parent"),
]


def execute():
    for table, id_field in TABLES:
        rows = frappe.db.sql(
            f"SELECT `name`, `description` FROM `{table}` WHERE `description` LIKE '%<p></p>%'",
            as_dict=True,
        )

        for row in rows:
            fixed = row["description"].replace("<p></p>", "<p><br></p>")
            frappe.db.sql(
                f"UPDATE `{table}` SET `description` = %s WHERE `name` = %s",
                (fixed, row["name"]),
            )

    frappe.db.commit()
