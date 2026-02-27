frappe.ui.form.on("Auto Repeat", {
	reference_document: function (frm) {
		az_it_maybe_fill_recipients(frm);
	},
	notify_by_email: function (frm) {
		if (frm.doc.notify_by_email) {
			az_it_maybe_fill_recipients(frm);
		}
	},
});

function az_it_maybe_fill_recipients(frm) {
	if (
		frm.doc.reference_doctype !== "Sales Invoice" ||
		!frm.doc.reference_document ||
		!frm.doc.notify_by_email
	) {
		return;
	}

	// Do not overwrite if recipients already has content
	if (frm.doc.recipients && frm.doc.recipients.trim()) {
		return;
	}

	frappe.call({
		method: "az_it.az_it.python_scripts.overrides.sales_invoice.get_billing_email_for_invoice",
		args: { invoice_name: frm.doc.reference_document },
		callback: function (r) {
			if (r.message) {
				frm.set_value("recipients", r.message);
			}
		},
	});
}
