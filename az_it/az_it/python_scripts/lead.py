
import frappe

@frappe.whitelist()
def cancel_todos_for_lead(lead_id, lead_status):

    # Verify that the status is one we should act on
    if lead_status not in ['Lost Quotation', 'Do Not Contact']:
        return {'cancelled_count': 0, 'message': 'No action needed for this status'}
    
    try:
        # Get all open ToDos for this Lead
        todos = frappe.db.get_all(
            'ToDo',
            filters={
                'reference_type': 'Lead',
                'reference_name': lead_id,
                'status': 'Open'
            },
            fields=['name', 'description']
        )
        
        cancelled_count = 0
        
        # Cancel each ToDo
        for todo in todos:
            todo_doc = frappe.get_doc('ToDo', todo.name)
            todo_doc.status = 'Cancelled'
            
            # Add a note about why it was cancelled
            if todo_doc.description:
                todo_doc.description += f"\n\n[Auto-cancelled: Lead status changed to '{lead_status}']"
            else:
                todo_doc.description = f"[Auto-cancelled: Lead status changed to '{lead_status}']"
            
            todo_doc.save()
            cancelled_count += 1
        
        # Commit the changes
        frappe.db.commit()
        
        
        return {
            'cancelled_count': cancelled_count,
            'message': f'Successfully cancelled {cancelled_count} ToDo(s)'
        }
        
    except Exception as e:
        frappe.throw(f"Error cancelling ToDos: {str(e)}")

