# File: az_it/az_it/python_scripts/overrides/sales_invoice.py
"""
Sales Invoice: Set billing contact instead of primary contact

When a Sales Invoice is created, the contact_person field is automatically filled
with the primary contact for the customer by core ERPNext logic.

This module provides an API that the client-side JS calls to fetch the billing
contact for a customer, which then replaces the primary contact.

Requirement: When sending an email from Sales Invoice to the customer,
the customer's invoice/billing email address should be used, not the primary contact.
"""
import frappe



@frappe.whitelist()
def get_party_details_with_billing(
    party=None,
    party_type="Customer",
    doctype=None,
    **kwargs
):
    """
    Override of erpnext.accounts.party.get_party_details

    Replaces primary contact with billing contact for selling documents
    (Sales Invoice, Sales Order, Quotation, Delivery Note).

    For all other cases, uses standard ERPNext behavior.

    Args:
        party: Customer/Supplier name
        party_type: "Customer" or "Supplier"
        doctype: Document type (e.g., "Sales Invoice")
        **kwargs: All other parameters passed to original function

    Returns:
        Dictionary with party details including contact information
    """
    # Import and call original ERPNext function
    from erpnext.accounts.party import get_party_details as original_get_party_details

    # Remove 'cmd' from kwargs as it's added by Frappe's whitelist decorator
    # but the original function doesn't accept it
    kwargs.pop('cmd', None)

    # Call original function with all parameters
    party_details = original_get_party_details(
        party=party,
        party_type=party_type,
        doctype=doctype,
        **kwargs
    )

    # Only modify for Customer selling documents
    if party_type == "Customer" and doctype in ["Sales Invoice", "Sales Order", "Quotation", "Delivery Note"]:
        # Get billing contact for this customer
        billing_contact_name = get_billing_contact_for_customer(party)

        if billing_contact_name:
            # Fetch billing contact details
            billing_details = get_contact_details(billing_contact_name)

            if billing_details:
                # Replace contact fields in party_details
                party_details.update({
                    "contact_person": billing_details.get("contact_person"),
                    "contact_display": billing_details.get("contact_display"),
                    "contact_email": billing_details.get("contact_email"),
                    "contact_mobile": billing_details.get("contact_mobile"),
                })

    return party_details


@frappe.whitelist()
def get_billing_contact(customer):
    """
    API method to get the billing contact for a customer.
    Called from client-side JS when customer is selected on Sales Invoice.

    Args:
        customer: Name of the Customer doctype

    Returns:
        Dictionary with billing contact details or None
    """
    if not customer:
        return None

    billing_contact = get_billing_contact_for_customer(customer)

    if billing_contact:
        return get_contact_details(billing_contact)

    return None


def get_billing_contact_for_customer(customer_name):
    """
    Get the primary billing contact for a customer.

    Searches for contacts linked to the customer where is_billing_contact = 1.

    Args:
        customer_name: Name of the Customer doctype

    Returns:
        Contact name (str) or None if no billing contact found
    """
    if not customer_name:
        return None

    billing_contacts = frappe.get_all(
        "Contact",
        filters=[
            ["Dynamic Link", "link_doctype", "=", "Customer"],
            ["Dynamic Link", "link_name", "=", customer_name],
            ["is_billing_contact", "=", 1],
        ],
        pluck="name",
        order_by="`tabContact`.creation DESC",
        limit=1,
    )

    if billing_contacts:
        return billing_contacts[0]

    return None


def get_contact_details(contact_name):
    """
    Get contact details for populating Sales Invoice fields.

    Only fetches fields that exist in Sales Invoice:
    - contact_person (Link)
    - contact_display (from full_name)
    - contact_email (from email_id)
    - contact_mobile (from mobile_no)

    Args:
        contact_name: Name of the Contact doctype

    Returns:
        Dictionary with contact details or None
    """
    if not contact_name:
        return None

    contact = frappe.db.get_value(
        "Contact",
        contact_name,
        [
            "name as contact_person",
            "full_name as contact_display",
            "email_id as contact_email",
            "mobile_no as contact_mobile",
        ],
        as_dict=True,
    )

    return contact


@frappe.whitelist()
def get_billing_email_for_invoice(invoice_name):
    """
    Return the best billing email address for a given Sales Invoice.

    Priority:
    1. contact_person already on the invoice (set by billing contact override)
    2. Any contact for the customer with is_billing_contact=1

    Email selection within a contact:
    - Prefer the email marked is_primary
    - If none is_primary but only one email exists, use it
    - If multiple emails without is_primary, use the first one

    Args:
        invoice_name: Name of the Sales Invoice doctype

    Returns:
        Email address string or None
    """
    contact_person, customer = frappe.db.get_value(
        "Sales Invoice", invoice_name, ["contact_person", "customer"]
    )

    if not customer:
        return None

    # Step 1: try contact already linked on the invoice
    if contact_person:
        email = _get_best_email_from_contact(contact_person)
        if email:
            return email

    # Step 2: fall back to searching for billing contact by customer
    billing_contact = get_billing_contact_for_customer(customer)
    if billing_contact:
        return _get_best_email_from_contact(billing_contact)

    return None


def _get_best_email_from_contact(contact_name):
    """
    Return the best email from a contact's email_ids child table.

    Prefers is_primary; falls back to first available.

    Args:
        contact_name: Name of the Contact doctype

    Returns:
        Email address string or None
    """
    try:
        contact = frappe.get_doc("Contact", contact_name)
    except frappe.DoesNotExistError:
        return None

    emails = contact.email_ids or []
    if not emails:
        return None

    for e in emails:
        if e.is_primary:
            return e.email_id

    return emails[0].email_id
