# File: az_it/az_it/python_scripts/overrides/sales_invoice_email.py
"""
Override email sender for Sales Invoice communications.

When an email is sent from a Sales Invoice document, this hook
changes the sender to the billing email account instead of the
user's personal email.

Requirement: Invoice emails to customers should come from the dedicated
billing email (rechnung@az-it.systems) rather than the system default
or the user's personal email.
"""
import frappe

# Configuration for billing email
BILLING_EMAIL = "rechnung@az-it.systems"
BILLING_NAME = "AZ-IT Rechnungen"


def set_invoice_email_sender(doc, method):
    """
    Hook: Communication.validate

    Override the sender email for emails sent from Sales Invoice documents
    to use the dedicated billing email address.

    Args:
        doc: Communication document
        method: Hook method name (validate)
    """
    # Only process outgoing emails from Sales Invoice
    if not _is_sales_invoice_outgoing_email(doc):
        return

    # Get the billing email account
    email_account = _get_billing_email_account()
    if not email_account:
        return

    # Set the sender to the billing email
    doc.sender = f"{BILLING_NAME} <{BILLING_EMAIL}>"
    doc.sender_full_name = BILLING_NAME
    doc.email_account = email_account


def _is_sales_invoice_outgoing_email(doc):
    """
    Check if this Communication is an outgoing email from Sales Invoice.

    Args:
        doc: Communication document

    Returns:
        bool: True if this is an outgoing email from Sales Invoice
    """
    return (
        doc.reference_doctype == "Sales Invoice"
        and doc.communication_medium == "Email"
        and doc.sent_or_received == "Sent"
    )


def _get_billing_email_account():
    """
    Get the billing email account name if it exists and is enabled for outgoing.

    Returns:
        str: Email Account name or None if not found/enabled
    """
    email_account_name = frappe.db.get_value(
        "Email Account",
        {"email_id": BILLING_EMAIL, "enable_outgoing": 1},
        "name"
    )

    if not email_account_name:
        frappe.log_error(
            title="Sales Invoice Email Override",
            message=f"Billing email account '{BILLING_EMAIL}' not found or not enabled for outgoing. "
                    "Please ensure the Email Account exists and 'Enable Outgoing' is checked."
        )
        return None

    return email_account_name
