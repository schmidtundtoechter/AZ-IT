import frappe


def run_diagnostics():
	results = {}

	# 1. Custom fields exist?
	custom_fields = frappe.db.sql(
		"SELECT fieldname FROM `tabCustom Field` WHERE dt='Dunning Type' AND fieldname IN ('custom_dunning_level', 'custom_days_trigger')",
		as_dict=True,
	)
	results["custom_fields_in_db"] = [f.fieldname for f in custom_fields]

	# 2. Dunning Types with levels configured?
	dunning_types = frappe.db.sql(
		"SELECT name, custom_dunning_level, custom_days_trigger FROM `tabDunning Type` ORDER BY custom_dunning_level",
		as_dict=True,
	)
	results["dunning_types"] = dunning_types

	# 3. Overdue Sales Invoices?
	overdue = frappe.db.sql(
		"SELECT COUNT(*) as cnt FROM `tabSales Invoice` WHERE docstatus=1 AND outstanding_amount > 0 AND is_return=0",
		as_dict=True,
	)
	results["overdue_invoices_count"] = overdue[0].cnt if overdue else 0

	# 4. Any existing Dunning documents?
	dunnings = frappe.db.sql(
		"SELECT name, dunning_type, docstatus, posting_date FROM `tabDunning` ORDER BY creation DESC LIMIT 5",
		as_dict=True,
	)
	results["recent_dunnings"] = dunnings

	# 5. Recent error logs related to dunning?
	errors = frappe.db.sql(
		"SELECT title, error, creation FROM `tabError Log` WHERE title LIKE '%Dunning%' ORDER BY creation DESC LIMIT 5",
		as_dict=True,
	)
	results["recent_errors"] = errors

	for key, val in results.items():
		print(f"\n--- {key} ---")
		print(val)

	return results
