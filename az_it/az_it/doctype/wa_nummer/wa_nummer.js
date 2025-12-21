// Copyright (c) 2025, ahmad mohammad and contributors
// For license information, please see license.txt

frappe.ui.form.on("WA Nummer", {
	refresh(frm) {
		// Add helpful message for new records
		if (frm.is_new()) {
			frm.set_intro(__('WA Nummer will be automatically generated when you save this record.'), 'blue');
		}

		// Add link to view all WA Numbers for this customer
		if (!frm.is_new() && frm.doc.kunde) {
			frm.add_custom_button(__('View Customer'), function() {
				frappe.set_route('Form', 'Customer', frm.doc.kunde);
			});

			frm.add_custom_button(__('View Sales Order'), function() {
				if (frm.doc.auftrag) {
					frappe.set_route('Form', 'Sales Order', frm.doc.auftrag);
				}
			});
		}
	},

	kunde(frm) {
		// When customer is selected, show info message
		if (frm.doc.kunde) {
			frappe.call({
				method: 'frappe.client.get_count',
				args: {
					doctype: 'WA Nummer',
					filters: {
						kunde: frm.doc.kunde
					}
				},
				callback: function(r) {
					if (r.message) {
						frm.set_df_property('kunde', 'description',
							__('This customer has {0} existing WA Number(s)', [r.message]));
					}
				}
			});
		}
	}
});
