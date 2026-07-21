import frappe
from az_it.az_it.api.telephony import push_contact_to_3cx, _get_company_for_contact


def sync_contacts_to_3cx():
	"""Hourly: push all unsynced contacts to the 3CX phonebook.

	Only contacts where custom_3cx_synced=0 are pushed, so existing 3CX phonebook
	data added manually is never overwritten by this bulk job.
	Already-synced contacts are kept up-to-date by the on_update hook instead.
	"""
	if not frappe.conf.get("3cx_url"):
		return

	unsynced = frappe.get_all(
		"Contact",
		filters={"custom_3cx_synced": 0},
		fields=["name", "first_name", "last_name", "company_name"],
	)

	for row in unsynced:
		try:
			contact_id = row["name"]

			email = (
				frappe.db.get_value(
					"Contact Email", {"parent": contact_id, "is_primary": 1}, "email_id"
				)
				or frappe.db.get_value("Contact Email", {"parent": contact_id}, "email_id")
				or ""
			)

			phones = frappe.db.get_all(
				"Contact Phone",
				filters={"parent": contact_id},
				fields=["phone", "is_primary_mobile_no"],
				order_by="is_primary_mobile_no desc",
			)

			company = row.get("company_name") or _get_company_for_contact(contact_id)
			first_name = (row.get("first_name") or "").strip()

			success = push_contact_to_3cx({
				"first_name": first_name or company or "",
				"last_name": (row.get("last_name") or "").strip(),
				"company_name": company,
				"email": email,
				"phone_business": phones[0]["phone"] if phones else "",
				"phone_mobile": phones[1]["phone"] if len(phones) > 1 else "",
			})

			if success:
				frappe.db.set_value("Contact", contact_id, "custom_3cx_synced", 1)

		except Exception:
			frappe.log_error(
				title=f"3CX sync failed: {row.get('name', '')}"[:140],
				message=frappe.get_traceback(),
			)
