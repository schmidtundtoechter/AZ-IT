import frappe
from frappe.utils import today, add_days, getdate


def auto_create_dunnings():
	"""
	Daily scheduled task.
	Scans all overdue submitted Sales Invoices and creates draft Dunning
	documents at the appropriate escalation level (1, 2, or 3).
	Employees review and submit the drafts manually.
	"""
	dunning_types_by_level = _get_dunning_types_by_level()
	if not dunning_types_by_level:
		return  # No dunning types configured with custom_dunning_level — skip silently

	overdue_invoices = _get_overdue_invoices()

	for invoice in overdue_invoices:
		try:
			_process_invoice(invoice, dunning_types_by_level)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"Auto Dunning: Error processing invoice {invoice.name}",
			)


def _get_dunning_types_by_level():
	"""
	Returns a dict keyed by dunning level: {1: config_dict, 2: config_dict, 3: config_dict}.
	Only returns Dunning Types that have custom_dunning_level set.
	"""
	dunning_types = frappe.get_all(
		"Dunning Type",
		filters=[["custom_dunning_level", ">", 0]],
		fields=[
			"name",
			"custom_dunning_level",
			"custom_days_trigger",
			"company",
			"dunning_fee",
			"rate_of_interest",
			"income_account",
			"cost_center",
		],
	)
	result = {}
	for dt in dunning_types:
		level = dt.custom_dunning_level
		if level not in result:
			result[level] = dt
	return result


def _get_overdue_invoices():
	"""Returns all submitted, non-return Sales Invoices with outstanding_amount > 0."""
	return frappe.get_all(
		"Sales Invoice",
		filters={
			"docstatus": 1,
			"outstanding_amount": [">", 0],
			"is_return": 0,
		},
		fields=["name", "customer", "company", "due_date", "outstanding_amount", "currency", "language"],
	)


def _process_invoice(invoice, dunning_types_by_level):
	"""
	Determines the correct dunning level for a single invoice and creates a
	draft Dunning document if the timing conditions are met and no duplicate exists.

	Level 1: triggered N days after invoice due_date.
	Level 2: triggered N days after the submitted Level 1 dunning's posting_date.
	Level 3: triggered N days after the submitted Level 2 dunning's posting_date.
	"""
	today_date = getdate(today())

	# --- Level 1 ---
	l1 = dunning_types_by_level.get(1)
	if l1:
		trigger_date = getdate(add_days(invoice.due_date, l1.custom_days_trigger or 30))
		if today_date >= trigger_date:
			if not _get_existing_dunning(invoice.name, 1):
				_create_dunning_draft(invoice, l1)
				return  # One level per run

	# --- Level 2 (only if Level 1 has been submitted/sent) ---
	l2 = dunning_types_by_level.get(2)
	if l2:
		submitted_l1 = _get_submitted_dunning(invoice.name, 1)
		if submitted_l1:
			trigger_date = getdate(add_days(submitted_l1.posting_date, l2.custom_days_trigger or 10))
			if today_date >= trigger_date:
				if not _get_existing_dunning(invoice.name, 2):
					_create_dunning_draft(invoice, l2)
					return

	# --- Level 3 (only if Level 2 has been submitted/sent) ---
	l3 = dunning_types_by_level.get(3)
	if l3:
		submitted_l2 = _get_submitted_dunning(invoice.name, 2)
		if submitted_l2:
			trigger_date = getdate(add_days(submitted_l2.posting_date, l3.custom_days_trigger or 10))
			if today_date >= trigger_date:
				if not _get_existing_dunning(invoice.name, 3):
					_create_dunning_draft(invoice, l3)


def _get_existing_dunning(sales_invoice_name, level):
	"""
	Returns a dunning record if any non-cancelled Dunning at the given level
	exists for the invoice (draft or submitted both count as existing).
	Uses a 3-table join: Dunning → Overdue Payment → Dunning Type.
	"""
	dunning = frappe.qb.DocType("Dunning")
	op = frappe.qb.DocType("Overdue Payment")
	dt = frappe.qb.DocType("Dunning Type")

	result = (
		frappe.qb.from_(dunning)
		.join(op)
		.on(op.parent == dunning.name)
		.join(dt)
		.on(dt.name == dunning.dunning_type)
		.select(dunning.name, dunning.posting_date)
		.where(op.sales_invoice == sales_invoice_name)
		.where(dt.custom_dunning_level == level)
		.where(dunning.docstatus != 2)  # exclude cancelled
		.limit(1)
	).run(as_dict=True)

	return result[0] if result else None


def _get_submitted_dunning(sales_invoice_name, level):
	"""
	Returns the submitted (docstatus=1) Dunning at the given level for the invoice.
	Used to check whether the prior level has been sent before escalating.
	"""
	dunning = frappe.qb.DocType("Dunning")
	op = frappe.qb.DocType("Overdue Payment")
	dt = frappe.qb.DocType("Dunning Type")

	result = (
		frappe.qb.from_(dunning)
		.join(op)
		.on(op.parent == dunning.name)
		.join(dt)
		.on(dt.name == dunning.dunning_type)
		.select(dunning.name, dunning.posting_date)
		.where(op.sales_invoice == sales_invoice_name)
		.where(dt.custom_dunning_level == level)
		.where(dunning.docstatus == 1)  # only submitted
		.limit(1)
	).run(as_dict=True)

	return result[0] if result else None


def _create_dunning_draft(invoice, dunning_type_config):
	"""
	Creates and saves (docstatus=0) a draft Dunning document for the given
	Sales Invoice using the specified Dunning Type configuration.

	Reuses ERPNext's get_mapped_doc pattern from sales_invoice.create_dunning()
	but selects the dunning type by custom_dunning_level instead of is_default.
	"""
	from frappe.model.mapper import get_mapped_doc
	from erpnext.accounts.doctype.dunning.dunning import get_dunning_letter_text

	dunning_type_doc = frappe.get_doc("Dunning Type", dunning_type_config.name)

	def postprocess(source, target):
		target.dunning_type = dunning_type_doc.name
		target.rate_of_interest = dunning_type_doc.rate_of_interest
		target.dunning_fee = dunning_type_doc.dunning_fee
		target.income_account = dunning_type_doc.income_account
		target.cost_center = dunning_type_doc.cost_center

		letter_text = get_dunning_letter_text(
			dunning_type=dunning_type_doc.name,
			doc=target.as_dict(),
			language=source.language,
		)
		if letter_text:
			target.body_text = letter_text.get("body_text")
			target.closing_text = letter_text.get("closing_text")
			target.language = letter_text.get("language")

		# Adjust outstanding for invoices with a single payment schedule row
		if source.payment_schedule and len(source.payment_schedule) == 1:
			if target.overdue_payments:
				target.overdue_payments[0].outstanding = source.get("outstanding_amount")

		target.validate()

	dunning = get_mapped_doc(
		from_doctype="Sales Invoice",
		from_docname=invoice.name,
		table_maps={
			"Sales Invoice": {
				"doctype": "Dunning",
				"field_map": {"customer_address": "customer_address", "parent": "sales_invoice"},
			},
			"Payment Schedule": {
				"doctype": "Overdue Payment",
				"field_map": {"name": "payment_schedule", "parent": "sales_invoice"},
				"condition": lambda doc: doc.outstanding > 0 and getdate(doc.due_date) < getdate(),
			},
		},
		postprocess=postprocess,
		ignore_permissions=True,
	)

	if not dunning.overdue_payments:
		return  # No overdue payment schedule rows — nothing to dun

	dunning.insert(ignore_permissions=True)
	frappe.db.commit()
