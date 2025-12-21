// Custom script for Customer DocType - WA Nummer integration
// Copyright (c) 2025, ahmad mohammad and contributors

frappe.ui.form.on('Customer', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            // Add custom button to view WA Nummer list
            frm.add_custom_button(__('View WA Numbers'), function() {
                frappe.route_options = {
                    "kunde": frm.doc.name
                };
                frappe.set_route("List", "WA Nummer");
            }, __("Actions"));

            // Add button to create new WA Nummer
            frm.add_custom_button(__('Create New WA Nummer'), function() {
                frappe.new_doc('WA Nummer', {
                    kunde: frm.doc.name
                });
            }, __("Create"));

            // Load and display WA Nummer list
            load_wa_nummer_list(frm);
        }
    }
});

function load_wa_nummer_list(frm) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'WA Nummer',
            filters: {
                kunde: frm.doc.name
            },
            fields: ['name', 'wa_nummer', 'zugehoeriger_artikel', 'vertragsabschluss', 'aktueller_preis', 'auftrag'],
            order_by: 'creation desc',
            limit: 100
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let html = '<div class="wa-nummer-list">';
                html += '<table class="table table-bordered">';
                html += '<thead><tr>';
                html += '<th>WA Nummer</th>';
                html += '<th>Article</th>';
                html += '<th>Contract Date</th>';
                html += '<th>Current Price</th>';
                html += '<th>Sales Order</th>';
                html += '</tr></thead><tbody>';

                r.message.forEach(function(wa) {
                    html += '<tr>';
                    html += '<td><a href="/app/wa-nummer/' + encodeURIComponent(wa.name) + '">' + wa.wa_nummer + '</a></td>';
                    html += '<td>' + (wa.zugehoeriger_artikel || '-') + '</td>';
                    html += '<td>' + (wa.vertragsabschluss || '-') + '</td>';
                    html += '<td>' + (wa.aktueller_preis ? format_currency(wa.aktueller_preis) : '-') + '</td>';
                    html += '<td>' + (wa.auftrag ? '<a href="/app/sales-order/' + encodeURIComponent(wa.auftrag) + '">' + wa.auftrag + '</a>' : '-') + '</td>';
                    html += '</tr>';
                });

                html += '</tbody></table></div>';

                // Display in the custom HTML field
                frm.fields_dict.custom_wa_nummer.$wrapper.html(html);
            } else {
                frm.fields_dict.custom_wa_nummer.$wrapper.html(
                    '<div class="text-muted">No WA Numbers found for this customer.</div>'
                );
            }
        }
    });
}
