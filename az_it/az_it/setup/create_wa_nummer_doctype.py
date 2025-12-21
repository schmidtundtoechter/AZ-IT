import frappe

def create_wa_nummer_doctype():
    """
    Create WA Nummer DocType with all required fields
    """

    # Check if DocType already exists
    if frappe.db.exists("DocType", "WA Nummer"):
        print("WA Nummer DocType already exists")
        return

    # Create the DocType
    doctype = frappe.get_doc({
        "doctype": "DocType",
        "name": "WA Nummer",
        "module": "Az It",
        "custom": 0,
        "istable": 0,
        "is_submittable": 0,
        "is_tree": 0,
        "editable_grid": 1,
        "track_changes": 1,
        "autoname": "field:wa_nummer",
        "naming_rule": "By fieldname",
        "title_field": "wa_nummer",
        "fields": [
            {
                "fieldname": "wa_nummer",
                "label": "WA Nummer",
                "fieldtype": "Data",
                "reqd": 1,
                "unique": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "read_only": 1,
                "description": "Support Contract Number - automatically generated"
            },
            {
                "fieldname": "kunde",
                "label": "Kunde",
                "fieldtype": "Link",
                "options": "Customer",
                "reqd": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "description": "Customer with support contract"
            },
            {
                "fieldname": "zugehoeriger_artikel",
                "label": "Zugehöriger Artikel",
                "fieldtype": "Link",
                "options": "Item",
                "reqd": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "description": "Linked item (type of maintenance contract)"
            },
            {
                "fieldname": "column_break_1",
                "fieldtype": "Column Break"
            },
            {
                "fieldname": "vertragsabschluss",
                "label": "Vertragsabschluss",
                "fieldtype": "Date",
                "reqd": 1,
                "description": "Contract conclusion date"
            },
            {
                "fieldname": "auftrag",
                "label": "Auftrag",
                "fieldtype": "Link",
                "options": "Sales Order",
                "reqd": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "description": "Sales Order that generated this WA number"
            },
            {
                "fieldname": "section_break_2",
                "fieldtype": "Section Break",
                "label": "Pricing"
            },
            {
                "fieldname": "aktueller_preis",
                "label": "Aktueller Preis",
                "fieldtype": "Currency",
                "description": "Current price - maintained manually"
            },
            {
                "fieldname": "alter_preis",
                "label": "Alter Preis",
                "fieldtype": "Currency",
                "description": "Old price - maintained manually"
            },
            {
                "fieldname": "section_break_3",
                "fieldtype": "Section Break",
                "label": "Notes"
            },
            {
                "fieldname": "kommentar",
                "label": "Kommentar",
                "fieldtype": "Small Text",
                "description": "Comment field"
            }
        ],
        "permissions": [
            {
                "role": "System Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 1,
                "submit": 0,
                "cancel": 0,
                "amend": 0
            },
            {
                "role": "Sales User",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 0,
                "submit": 0,
                "cancel": 0,
                "amend": 0
            },
            {
                "role": "Sales Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 1,
                "submit": 0,
                "cancel": 0,
                "amend": 0
            }
        ]
    })

    doctype.insert()
    frappe.db.commit()
    print("WA Nummer DocType created successfully")

if __name__ == "__main__":
    create_wa_nummer_doctype()
