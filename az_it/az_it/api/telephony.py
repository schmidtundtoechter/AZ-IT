import re
import frappe
import requests
from frappe.utils import now_datetime


def _get_3cx_config():
    return {
        "url": (frappe.conf.get("3cx_url") or "").rstrip("/"),
        "client_id": frappe.conf.get("3cx_client_id") or "",
        "client_secret": frappe.conf.get("3cx_client_secret") or "",
    }


def push_contact_to_3cx(contact_data):
    """
    Upsert a single contact into the 3CX phonebook.
    Silently skips if 3cx_url is not configured in site_config.json.
    Expected site_config keys: 3cx_url, 3cx_client_id, 3cx_client_secret.
    """
    cfg = _get_3cx_config()
    if not cfg["url"]:
        return

    try:
        tok_resp = requests.post(
            f"{cfg['url']}/connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
            },
            timeout=10,
            verify=False,
        )
        token = tok_resp.json().get("access_token", "")
        if not token:
            frappe.log_error("3CX token fetch returned no access_token", "3CX Phonebook Sync")
            return False

        # 3CX ImportContacts expects CSV with this exact column order:
        # Name, Last Name, Company, Mobile, Mobile2, Home, Home 2,
        # Business, Business2, e-mail, Other, Business Fax, Home Fax, Pager
        import csv, io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Name", "Last Name", "Company",
            "Mobile", "Mobile2", "Home", "Home 2",
            "Business", "Business2", "e-mail",
            "Other", "Business Fax", "Home Fax", "Pager",
        ])
        writer.writerow([
            contact_data.get("first_name", ""),
            contact_data.get("last_name", ""),
            contact_data.get("company_name", ""),
            contact_data.get("phone_mobile", ""),
            "", "", "",
            contact_data.get("phone_business", ""),
            "",
            contact_data.get("email", ""),
            "", "", "", "",
        ])

        resp = requests.post(
            f"{cfg['url']}/xapi/v1/Contacts/Pbx.ImportContacts",
            data=buf.getvalue().encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "text/csv",
            },
            timeout=15,
            verify=False,
        )
        if not resp.ok:
            frappe.log_error(
                title=f"3CX contact push failed: HTTP {resp.status_code}",
                message=resp.text[:2000],
            )
            return False

        result = resp.json()
        if not result.get("success") or not result.get("importCount"):
            frappe.log_error(
                title="3CX contact push: importCount=0",
                message=str(result)[:2000],
            )
            return False

        return True
    except Exception as e:
        frappe.log_error(str(e)[:140], "3CX Phonebook Sync")
        return False


def _normalize(number):
	"""Strip non-digits, return last 9 digits for fuzzy matching."""
	digits = re.sub(r"\D", "", number)
	return digits[-9:] if len(digits) >= 9 else digits


def _get_company_for_contact(contact_id):
	"""Return company name: Contact.company_name first, then first linked Customer (by idx)."""
	company = frappe.db.get_value("Contact", contact_id, "company_name") or ""
	if company:
		return company
	rows = frappe.db.get_all(
		"Dynamic Link",
		filters={"parent": contact_id, "parenttype": "Contact", "link_doctype": "Customer"},
		fields=["link_name"],
		order_by="idx asc",
		limit=1,
	)
	return rows[0]["link_name"] if rows else ""


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

	first_name_val = (row.get("first_name") or "").strip()
	last_name_val  = (row.get("last_name")  or "").strip()
	company = _get_company_for_contact(contact_id)

	return {
		"contact_id":  contact_id,
		"first_name":  first_name_val or company or "",
		"last_name":   last_name_val,
		"company_name": company,
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
	if result and result.get("entity_type") == "Contact":
		contact_id = result["contact_id"]
		if not frappe.db.get_value("Contact", contact_id, "custom_3cx_synced"):
			if push_contact_to_3cx(result):
				frappe.db.set_value("Contact", contact_id, "custom_3cx_synced", 1)
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

	company = ""
	if entity_id:
		if entity_type == "Contact":
			company = _get_company_for_contact(entity_id)
		elif entity_type == "Lead":
			company = frappe.db.get_value("Lead", entity_id, "company_name") or ""

	subject = f"{call_type} call {'from' if sent_or_received == 'Received' else 'to'} {number}"
	content_lines = [
		f"Duration: {duration_str}",
		f"Agent: {agent_email}",
		f"Number: {number}",
	]
	if company:
		content_lines.append(f"Company: {company}")
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
