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

// Custom Discount Logic for Sales Invoice Items
frappe.ui.form.on('Sales Invoice Item', {
    rate: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        // Only update ausgangspreis if discount is 0 or empty
        if (!row.custom_rabatt_in_prozent || row.custom_rabatt_in_prozent === 0) {
            frappe.model.set_value(cdt, cdn, 'custom_ausgangspreis', row.rate);
        }
    },

    custom_rabatt_in_prozent: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        // Validate: must be between 0-100
        if (row.custom_rabatt_in_prozent < 0 || row.custom_rabatt_in_prozent > 100) {
            frappe.msgprint(__('Rabatt muss zwischen 0 und 100% liegen'));
            frappe.model.set_value(cdt, cdn, 'custom_rabatt_in_prozent', 0);
            return;
        }

        // If ausgangspreis is not set, set it to current rate
        if (!row.custom_ausgangspreis) {
            frappe.model.set_value(cdt, cdn, 'custom_ausgangspreis', row.rate);
        }

        // Calculate new rate from ausgangspreis
        let ausgangspreis = flt(row.custom_ausgangspreis);
        let discount = flt(row.custom_rabatt_in_prozent);
        let new_rate = ausgangspreis * (1 - discount / 100);

        // Update rate
        frappe.model.set_value(cdt, cdn, 'rate', new_rate);

        // Update description
        update_discount_description_sales_invoice(frm, cdt, cdn, discount);
    },

    custom_ausgangspreis: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        // If discount exists, recalculate rate
        if (row.custom_rabatt_in_prozent && row.custom_rabatt_in_prozent > 0) {
            let ausgangspreis = flt(row.custom_ausgangspreis);
            let discount = flt(row.custom_rabatt_in_prozent);
            let new_rate = ausgangspreis * (1 - discount / 100);

            frappe.model.set_value(cdt, cdn, 'rate', new_rate);
        }
    }
});

// Helper function to update description with discount text
function update_discount_description_sales_invoice(frm, cdt, cdn, discount_percent) {
    let row = locals[cdt][cdn];
    let description = row.description || '';

    // Remove any existing discount line
    description = remove_discount_line_sales_invoice(description);

    // Add new discount line if discount > 0
    if (discount_percent > 0) {
        let discount_html = `<p style="color: red; font-weight: bold;">inklusive ${discount_percent}% Rabatt</p>`;
        description = description + '\n' + discount_html;
    }

    frappe.model.set_value(cdt, cdn, 'description', description);
}

// Helper function to remove existing discount line from description
function remove_discount_line_sales_invoice(description) {
    if (!description) return '';

    // Remove HTML discount line (red text pattern)
    let cleaned = description.replace(
        /<p[^>]*style="[^"]*color:\s*red[^"]*"[^>]*>inklusive\s+\d+%\s+Rabatt<\/p>/gi,
        ''
    );

    // Also remove plain text pattern as fallback
    cleaned = cleaned.replace(
        /inklusive\s+\d+%\s+Rabatt/gi,
        ''
    );

    // Clean up extra newlines
    cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();

    return cleaned;
}
