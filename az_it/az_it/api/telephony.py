import re
import frappe
from frappe.utils import now_datetime


def _normalize(number):
	"""Strip non-digits, return last 9 digits for fuzzy matching."""
	digits = re.sub(r"\D", "", number)
	return digits[-9:] if len(digits) >= 9 else digits


def _lookup_contact(normalized):
	"""Search Contact Phone child table by normalized number."""
	result = frappe.db.sql(
		"""
		SELECT
			cp.parent AS contact_id,
			c.first_name,
			c.last_name,
			c.company_name,
			cp.phone AS matched_phone
		FROM `tabContact Phone` cp
		JOIN `tabContact` c ON c.name = cp.parent
		WHERE RIGHT(REGEXP_REPLACE(cp.phone, '[^0-9]', ''), 9) = %s
		LIMIT 1
		""",
		(normalized,),
		as_dict=True,
	)
	if not result:
		return None

	row = result[0]
	contact_id = row["contact_id"]

	# Get email
	email_row = frappe.db.get_value(
		"Contact Email", {"parent": contact_id, "is_primary": 1}, "email_id"
	) or frappe.db.get_value("Contact Email", {"parent": contact_id}, "email_id")

	# Get all phones for the contact
	phones = frappe.db.get_all(
		"Contact Phone",
		filters={"parent": contact_id},
		fields=["phone", "is_primary_mobile_no"],
		order_by="is_primary_mobile_no desc",
	)

	phone_business = phones[0]["phone"] if phones else ""
	phone_mobile = phones[1]["phone"] if len(phones) > 1 else ""

	full_name = " ".join(filter(None, [row.get("first_name"), row.get("last_name")]))

	return {
		"contact_id": contact_id,
		"first_name": full_name or row.get("company_name") or "",
		"company_name": row.get("company_name") or "",
		"email": email_row or "",
		"phone_business": phone_business or "",
		"phone_mobile": phone_mobile or "",
		"entity_type": "Contact",
	}


def _lookup_lead(normalized):
	"""Search Lead by phone/mobile/whatsapp fields."""
	result = frappe.db.sql(
		"""
		SELECT name, lead_name, company_name, email_id, phone, mobile_no
		FROM `tabLead`
		WHERE
			RIGHT(REGEXP_REPLACE(IFNULL(phone, ''), '[^0-9]', ''), 9) = %s
			OR RIGHT(REGEXP_REPLACE(IFNULL(mobile_no, ''), '[^0-9]', ''), 9) = %s
			OR RIGHT(REGEXP_REPLACE(IFNULL(whatsapp_no, ''), '[^0-9]', ''), 9) = %s
		LIMIT 1
		""",
		(normalized, normalized, normalized),
		as_dict=True,
	)
	if not result:
		return None

	row = result[0]
	return {
		"contact_id": row["name"],
		"first_name": row.get("lead_name") or "",
		"company_name": row.get("company_name") or "",
		"email": row.get("email_id") or "",
		"phone_business": row.get("phone") or "",
		"phone_mobile": row.get("mobile_no") or "",
		"entity_type": "Lead",
	}


@frappe.whitelist()
def lookup_contact_by_number(number):
	"""
	Called by 3CX when a call comes in.
	Returns contact info for the given phone number, or {} if not found.
	"""
	if not number:
		return {}

	normalized = _normalize(str(number))
	if not normalized:
		return {}

	result = _lookup_contact(normalized) or _lookup_lead(normalized)
	return result or {}


@frappe.whitelist()
def log_call(
	entity_id="",
	entity_type="Contact",
	call_type="Inbound",
	call_direction="",
	duration_seconds=0,
	agent_email="",
	number="",
):
	"""
	Called by 3CX after a call ends.
	Creates a Communication record linked to the Contact or Lead.
	"""
	sent_or_received = "Received" if call_type in ("Inbound", "Missed") else "Sent"

	try:
		duration_seconds = int(float(duration_seconds))
	except (ValueError, TypeError):
		duration_seconds = 0

	minutes, seconds = divmod(duration_seconds, 60)
	duration_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

	subject = f"{call_type} call {'from' if sent_or_received == 'Received' else 'to'} {number}"
	content_lines = [
		f"Duration: {duration_str}",
		f"Agent: {agent_email}",
		f"Number: {number}",
	]
	if call_direction:
		content_lines.append(f"Direction: {call_direction}")

	doc = frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": "Phone",
			"sent_or_received": sent_or_received,
			"subject": subject,
			"content": "\n".join(content_lines),
			"phone_no": number,
			"reference_doctype": entity_type if entity_id else None,
			"reference_name": entity_id if entity_id else None,
			"sender": agent_email,
			"communication_date": now_datetime(),
			"status": "Linked",
			"custom_call_type": call_type,
			"custom_duration_seconds": duration_seconds,
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"communication": doc.name}
