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

// Custom Discount Logic for Quotation Items
frappe.ui.form.on('Quotation Item', {
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
        update_discount_description_quotation(frm, cdt, cdn, discount);
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
function update_discount_description_quotation(frm, cdt, cdn, discount_percent) {
    let row = locals[cdt][cdn];
    let description = row.description || '';

    // Remove any existing discount line
    description = remove_discount_line_quotation(description);

    // Add new discount line if discount > 0
    if (discount_percent > 0) {
        let discount_html = `<p style="color: red; font-weight: bold;">inklusive ${discount_percent}% Rabatt</p>`;

        // Insert after first line/paragraph instead of appending at end
        let insertPosition = -1;

        // Pattern 1: Look for first </strong> or </b> tag (bold item name)
        let strongMatch = description.match(/(<\/strong>|<\/b>)/i);
        if (strongMatch) {
            insertPosition = strongMatch.index + strongMatch[0].length;
        }

        // Pattern 2: Look for first </p> tag
        if (insertPosition === -1) {
            let pMatch = description.match(/<\/p>/i);
            if (pMatch) {
                insertPosition = pMatch.index + pMatch[0].length;
            }
        }

        // Pattern 3: Look for first newline
        if (insertPosition === -1) {
            let newlineMatch = description.match(/\n/);
            if (newlineMatch) {
                insertPosition = newlineMatch.index + 1;
            }
        }

        // If we found a position, insert there; otherwise append at end (fallback)
        if (insertPosition > 0) {
            description = description.substring(0, insertPosition) +
                         '\n' + discount_html + '\n' +
                         description.substring(insertPosition);
        } else {
            // Fallback: append at end
            description = description + '\n' + discount_html;
        }
    }

    frappe.model.set_value(cdt, cdn, 'description', description);
}

// Helper function to remove existing discount line from description
function remove_discount_line_quotation(description) {
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
