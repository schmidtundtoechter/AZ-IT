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
