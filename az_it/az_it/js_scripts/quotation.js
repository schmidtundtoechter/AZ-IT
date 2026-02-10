// Custom script for Quotation DocType - Price Adjustment Validation
// Copyright (c) 2025, ahmad mohammad and contributors

frappe.ui.form.on('Quotation', {
    before_save: function(frm) {
        // Validate price adjustment checkbox before saving
        if (frm.doc.preisanpassung_erfolgt_qu !== 1) {
            frappe.msgprint({
                title: __('Preisanpassung erforderlich'),
                indicator: 'red',
                message: __('Bitte bestätigen Sie, dass die Preisanpassung erfolgt ist, indem Sie das Kontrollkästchen "Preisanpassung erfolgt" aktivieren.')
            });
            frappe.validated = false;
            return false;
        }
    },

    refresh: function(frm) {
        // Add visual indicator when checkbox is not checked
        if (!frm.doc.preisanpassung_erfolgt_qu && frm.doc.items && frm.doc.items.length > 0) {
            frm.dashboard.add_comment(
                __('Vergessen Sie nicht, die Preise zu überprüfen und das Kontrollkästchen "Preisanpassung erfolgt" zu aktivieren.'),
                'yellow',
                true
            );
        }
    }
});
