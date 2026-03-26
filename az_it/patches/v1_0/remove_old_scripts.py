import frappe


def execute():
    """
    Remove old/replaced scripts that are no longer managed by the app.
    - Server Script: Customer Internal Number Auto Assignment (superseded by -Update version)
    - Server Script: Ersteingabe Lead AZ-IT - Erzeuge Lead, Adresse und Kontakt v2 (replaced by v3)
    - Server Script: Aufgabe (ToDo) automatische Wiedervorlage erzeugen (old V1, if exists)
    - Client Script: Chance - Nach Angebotsversand erzeugen einer WVL Aufgabe in 14d
    - Client Script: Lead - Nach Angebotsversand erzeugen einer WVL Aufgabe in 14d
    """
    server_scripts_to_delete = [
        "Customer Internal Number Auto Assignment",
        "Ersteingabe Lead AZ-IT - Erzeuge Lead, Adresse und Kontakt v2",
        "Aufgabe (ToDo) automatische Wiedervorlage erzeugen",
    ]

    client_scripts_to_delete = [
        "Chance - Nach Angebotsversand erzeugen einer WVL Aufgabe in 14d",
        "Lead - Nach Angebotsversand erzeugen einer WVL Aufgabe in 14d",
    ]

    for name in server_scripts_to_delete:
        if frappe.db.exists("Server Script", name):
            frappe.delete_doc("Server Script", name, ignore_permissions=True)
            print(f"Deleted Server Script: {name}")

    for name in client_scripts_to_delete:
        if frappe.db.exists("Client Script", name):
            frappe.delete_doc("Client Script", name, ignore_permissions=True)
            print(f"Deleted Client Script: {name}")
