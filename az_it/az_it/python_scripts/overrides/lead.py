# File: your_custom_app/overrides/lead.py
import frappe
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def make_opportunity(source_name, target_doc=None):
    """
    Custom override to fetch contact details from linked Contact's primary email and mobile
    instead of Lead's direct fields
    """
    def set_missing_values(source, target):
        # Get the linked contact for this lead
        contact_name = get_primary_contact_for_lead(source.name)
        
        if contact_name:
            # Fetch primary email and mobile from Contact
            primary_email = get_primary_email_from_contact(contact_name)
            primary_mobile = get_primary_mobile_from_contact(contact_name)
            
            # Set the contact details from Contact doctype
            target.contact_email = primary_email or source.email_id
            target.contact_mobile = primary_mobile or source.mobile_no
        else:
            # Fallback to Lead's direct fields if no contact linked
            target.contact_email = source.email_id
            target.contact_mobile = source.mobile_no
        
        # Set other required fields
        target.contact_display = source.lead_name
        target.customer_name = source.company_name
        
        # Set address and contact person details (same as original)
        _set_missing_values_for_opportunity(source, target)

    # Create the mapped document (same mapping as original, but WITHOUT direct email/mobile mapping)
    target_doc = get_mapped_doc(
        "Lead",
        source_name,
        {
            "Lead": {
                "doctype": "Opportunity",
                "field_map": {
                    "campaign_name": "campaign",
                    "doctype": "opportunity_from", 
                    "name": "party_name",
                    "lead_name": "contact_display",
                    "company_name": "customer_name",
                    "lead_owner": "opportunity_owner",
                    "notes": "notes",
                    # NOTE: We removed these two mappings:
                    # "email_id": "contact_email",  # We'll set this in set_missing_values
                    # "mobile_no": "contact_mobile", # We'll set this in set_missing_values
                },
            }
        },
        target_doc,
        set_missing_values,
    )

    return target_doc


def get_primary_contact_for_lead(lead_name):
    """
    Get the primary contact linked to the lead
    """
    contact = frappe.db.sql("""
        SELECT parent 
        FROM `tabDynamic Link` 
        WHERE link_doctype = 'Lead' 
        AND link_name = %s 
        AND parenttype = 'Contact'
        LIMIT 1
    """, lead_name)
    
    return contact[0][0] if contact else None


def get_primary_email_from_contact(contact_name):
    """
    Get primary email from Contact's email_ids child table
    """
    # First try to get the primary email
    primary_email = frappe.db.sql("""
        SELECT email_id 
        FROM `tabContact Email` 
        WHERE parent = %s 
        AND is_primary = 1
        LIMIT 1
    """, contact_name)
    
    if primary_email:
        return primary_email[0][0]
    
    # Fallback to first email if no primary is set
    first_email = frappe.db.sql("""
        SELECT email_id 
        FROM `tabContact Email` 
        WHERE parent = %s 
        AND email_id IS NOT NULL
        AND email_id != ''
        ORDER BY idx
        LIMIT 1
    """, contact_name)
    
    return first_email[0][0] if first_email else None


def get_primary_mobile_from_contact(contact_name):
    """
    Get primary mobile from Contact's phone_nos child table
    """
    # First try to get the primary mobile
    primary_mobile = frappe.db.sql("""
        SELECT phone 
        FROM `tabContact Phone` 
        WHERE parent = %s 
        AND is_primary_mobile_no = 1
        LIMIT 1
    """, contact_name)
    
    if primary_mobile:
        return primary_mobile[0][0]
    
    # Fallback to first mobile/phone if no primary mobile is set
    first_mobile = frappe.db.sql("""
        SELECT phone 
        FROM `tabContact Phone` 
        WHERE parent = %s 
        AND phone IS NOT NULL 
        AND phone != ''
        ORDER BY idx
        LIMIT 1
    """, contact_name)
    
    return first_mobile[0][0] if first_mobile else None


def _set_missing_values_for_opportunity(source, target):
    """
    Set address and contact person details (copied from original ERPNext function)
    """
    address = frappe.get_all(
        "Dynamic Link",
        {
            "link_doctype": source.doctype,
            "link_name": source.name,
            "parenttype": "Address",
        },
        ["parent"],
        limit=1,
    )

    contact = frappe.get_all(
        "Dynamic Link",
        {
            "link_doctype": source.doctype,
            "link_name": source.name,
            "parenttype": "Contact",
        },
        ["parent"],
        limit=1,
    )

    if address:
        target.customer_address = address[0].parent

    if contact:
        target.contact_person = contact[0].parent