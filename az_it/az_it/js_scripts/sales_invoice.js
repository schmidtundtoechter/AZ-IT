// Custom script for Sales Invoice DocType - WA Nummer integration
// Copyright (c) 2025, ahmad mohammad and contributors

frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        // Set query filter for WA Nummer based on customer
        frm.set_query('custom_wa_nummer', function() {
            if (frm.doc.customer) {
                return {
                    filters: {
                        'kunde': frm.doc.customer
                    }
                };
            } else {
                frappe.msgprint(__('Please select a customer first'));
                return {
                    filters: {
                        'kunde': ['=', '']
                    }
                };
            }
        });
    },

    
    customer: function(frm) {
        // Clear WA Nummer when customer changes
        if (frm.doc.custom_wa_nummer) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'WA Nummer',
                    filters: {
                        name: frm.doc.custom_wa_nummer
                    },
                    fieldname: 'kunde'
                },
                callback: function(r) {
                    if (r.message && r.message.kunde !== frm.doc.customer) {
                        frm.set_value('custom_wa_nummer', '');
                        frappe.show_alert({
                            message: __('WA Nummer cleared as customer changed'),
                            indicator: 'orange'
                        });
                    }
                }
            });
        }

        // Set query filter again when customer changes
        frm.set_query('custom_wa_nummer', function() {
            if (frm.doc.customer) {
                return {
                    filters: {
                        'kunde': frm.doc.customer
                    }
                };
            }
        });
    },

    custom_wa_nummer: function(frm) {
        // Show info when WA Nummer is selected
        if (frm.doc.custom_wa_nummer) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'WA Nummer',
                    name: frm.doc.custom_wa_nummer
                },
                callback: function(r) {
                    if (r.message) {
                        let msg = __('WA Nummer: {0}<br>Article: {1}<br>Current Price: {2}',
                            [r.message.wa_nummer,
                             r.message.zugehoeriger_artikel || '-',
                             r.message.aktueller_preis ? format_currency(r.message.aktueller_preis) : '-']);
                        frappe.show_alert({
                            message: msg,
                            indicator: 'green'
                        }, 5);
                    }
                }
            });
        }
    }
});
