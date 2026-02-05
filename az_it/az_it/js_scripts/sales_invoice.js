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

        // Set billing contact instead of primary contact
        if (frm.doc.customer) {
            frappe.call({
                method: 'az_it.az_it.python_scripts.overrides.sales_invoice.get_billing_contact',
                args: {
                    customer: frm.doc.customer
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('contact_person', r.message.contact_person);
                        frm.set_value('contact_display', r.message.contact_display);
                        frm.set_value('contact_email', r.message.contact_email);
                        frm.set_value('contact_mobile', r.message.contact_mobile);
                    }
                }
            });
        }
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
