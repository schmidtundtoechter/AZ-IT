// Client Script for Lead DocType
// Purpose: Cancel all associated ToDos when Lead status changes to "Lost Quotation" or "Do Not Contact"
// Event: after_save

frappe.ui.form.on('Lead', {
    after_save: function(frm) {
        // Check if status is one of the target statuses that should close ToDos
        if (frm.doc.status === 'Lost Quotation' || frm.doc.status === 'Do Not Contact') {
            
            // Call server method to cancel all associated ToDos
            frappe.call({
                method: 'az_it.az_it.python_scripts.lead.cancel_todos_for_lead',
                args: {
                    lead_id: frm.doc.name,
                    lead_status: frm.doc.status
                },
                callback: function(response) {
                    if (response.message && response.message.cancelled_count > 0) {
                        frappe.show_alert({
                            message: __('Cancelled {0} ToDo(s) associated with this Lead', [response.message.cancelled_count]),
                            indicator: 'green'
                        }, 5);
                    }
                },
                error: function(err) {
                    console.error('Error cancelling ToDos:', err);
                }
            });
        }
    }
});