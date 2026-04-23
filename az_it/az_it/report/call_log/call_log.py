import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": _("Date"), "fieldname": "communication_date", "fieldtype": "Datetime", "width": 160},
        {"label": _("Call Type"), "fieldname": "custom_call_type", "fieldtype": "Data", "width": 110},
        {"label": _("Number"), "fieldname": "phone_no", "fieldtype": "Data", "width": 140},
        {"label": _("Contact / Lead"), "fieldname": "reference_name", "fieldtype": "Dynamic Link", "options": "reference_doctype", "width": 160},
        {"label": _("Entity Type"), "fieldname": "reference_doctype", "fieldtype": "Data", "width": 90},
        {"label": _("Company"), "fieldname": "company_name", "fieldtype": "Data", "width": 160},
        {"label": _("Agent"), "fieldname": "sender", "fieldtype": "Data", "width": 180},
        {"label": _("Duration"), "fieldname": "duration_display", "fieldtype": "Data", "width": 80},
        {"label": _("Duration (s)"), "fieldname": "custom_duration_seconds", "fieldtype": "Int", "width": 90},
    ]


def get_data(filters):
    conditions = ["c.communication_medium = 'Phone'"]
    values = {}

    if filters.get("from_date"):
        conditions.append("c.communication_date >= %(from_date)s")
        values["from_date"] = filters["from_date"] + " 00:00:00"

    if filters.get("to_date"):
        conditions.append("c.communication_date <= %(to_date)s")
        values["to_date"] = filters["to_date"] + " 23:59:59"

    if filters.get("call_type"):
        conditions.append("c.custom_call_type = %(call_type)s")
        values["call_type"] = filters["call_type"]

    if filters.get("agent_email"):
        conditions.append("c.sender = %(agent_email)s")
        values["agent_email"] = filters["agent_email"]

    where = " AND ".join(conditions)

    rows = frappe.db.sql(
        f"""
        SELECT
            c.communication_date,
            c.custom_call_type,
            c.phone_no,
            c.reference_name,
            c.reference_doctype,
            c.sender,
            c.custom_duration_seconds,
            CASE
                WHEN c.reference_doctype = 'Contact' THEN con.company_name
                WHEN c.reference_doctype = 'Lead'    THEN lead.company_name
                ELSE NULL
            END AS company_name
        FROM `tabCommunication` c
        LEFT JOIN `tabContact` con
            ON c.reference_doctype = 'Contact' AND c.reference_name = con.name
        LEFT JOIN `tabLead` lead
            ON c.reference_doctype = 'Lead' AND c.reference_name = lead.name
        WHERE {where}
        ORDER BY c.communication_date DESC
        """,
        values,
        as_dict=True,
    )

    for row in rows:
        secs = row.get("custom_duration_seconds") or 0
        m, s = divmod(int(secs), 60)
        row["duration_display"] = f"{m}m {s}s" if m else f"{s}s"

    return rows


def get_filters():
    return [
        {
            "fieldname": "from_date",
            "label": _("From Date"),
            "fieldtype": "Date",
            "default": frappe.utils.add_months(frappe.utils.today(), -1),
        },
        {
            "fieldname": "to_date",
            "label": _("To Date"),
            "fieldtype": "Date",
            "default": frappe.utils.today(),
        },
        {
            "fieldname": "call_type",
            "label": _("Call Type"),
            "fieldtype": "Select",
            "options": "\nInbound\nOutbound\nMissed\nNotanswered",
        },
        {
            "fieldname": "agent_email",
            "label": _("Agent Email"),
            "fieldtype": "Data",
        },
    ]
