# File: az_it/az_it/python_scripts/overrides/sales_invoice_auftrag.py
"""
Sales Invoice: Auto-fill custom_auftrag from first item's sales_order

When creating a Sales Invoice from a Sales Order, the items table contains
a reference to the source sales_order. This module auto-fills the custom_auftrag
field from the first item if it's empty.

This avoids manual data entry and maintains the link between Invoice and Order.
"""

import frappe


def auto_fill_auftrag_from_items(doc, method=None):
    """
    Auto-fill custom_auftrag field from first item's sales_order reference.

    Only runs when:
    - custom_auftrag field is empty
    - Document has items
    - First item has a sales_order reference

    Args:
        doc: Sales Invoice document
        method: Hook method (not used)
    """
    # Skip if custom_auftrag field doesn't exist
    if not hasattr(doc, 'custom_auftrag'):
        return

    # Skip if custom_auftrag is already filled
    if doc.custom_auftrag:
        return

    # Skip if no items in document
    if not doc.items or len(doc.items) == 0:
        return

    # Get sales_order from first item
    first_item = doc.items[0]
    sales_order = first_item.get("sales_order") or ""

    # Only set if we found a sales_order reference
    if sales_order:
        doc.custom_auftrag = sales_order
        frappe.logger().info(f"Sales Invoice {doc.name}: Auto-filled custom_auftrag with {sales_order}")
