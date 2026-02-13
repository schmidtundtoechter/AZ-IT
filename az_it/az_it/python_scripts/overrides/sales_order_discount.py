# Custom Discount Validation for Sales Order
# Copyright (c) 2026, ahmad mohammad and contributors

import frappe
from frappe import _
import re


def validate_custom_discount(doc, method=None):
    """
    Validate custom discount fields in Sales Order items.

    - Ensures discount percentage is between 0-100
    - Validates that rate matches calculation: ausgangspreis * (1 - discount/100)
    - Ensures description contains discount line when discount > 0

    Args:
        doc: Sales Order document
        method: Hook method name
    """

    for item in doc.items:
        # Skip if custom fields don't exist
        if not hasattr(item, 'custom_rabatt_in_prozent'):
            continue

        discount = float(item.custom_rabatt_in_prozent or 0)
        ausgangspreis = float(item.custom_ausgangspreis or 0)

        # Validate discount range
        if discount < 0 or discount > 100:
            frappe.throw(
                _("Row {0}: Rabatt muss zwischen 0 und 100% liegen").format(item.idx),
                title=_("Ungültiger Rabatt")
            )

        # Validate calculation if discount is applied
        if discount > 0:
            if not ausgangspreis:
                # Auto-set ausgangspreis if missing
                item.custom_ausgangspreis = item.rate
                ausgangspreis = item.rate

            expected_rate = ausgangspreis * (1 - discount / 100)
            actual_rate = float(item.rate)

            # Allow small rounding differences (0.01)
            if abs(expected_rate - actual_rate) > 0.01:
                # Auto-correct rate
                item.rate = expected_rate

            # Ensure description contains discount text
            if not has_discount_in_description(item.description, discount):
                item.description = add_discount_to_description(
                    item.description, discount
                )
        else:
            # If discount is 0, remove any discount text from description
            if item.description:
                item.description = remove_discount_from_description(item.description)


def has_discount_in_description(description, discount_percent):
    """Check if description contains the discount line."""
    if not description:
        return False

    pattern = rf'inklusive\s+{int(discount_percent)}%\s+Rabatt'
    return bool(re.search(pattern, description, re.IGNORECASE))


def add_discount_to_description(description, discount_percent):
    """Add discount line to description."""
    if not description:
        description = ''

    # Remove existing discount lines first
    description = remove_discount_from_description(description)

    # Add new discount line
    discount_html = f'<p style="color: red; font-weight: bold;">inklusive {int(discount_percent)}% Rabatt</p>'

    return description + '\n' + discount_html


def remove_discount_from_description(description):
    """Remove discount line from description."""
    if not description:
        return ''

    # Remove HTML pattern
    cleaned = re.sub(
        r'<p[^>]*style="[^"]*color:\s*red[^"]*"[^>]*>inklusive\s+\d+%\s+Rabatt</p>',
        '',
        description,
        flags=re.IGNORECASE
    )

    # Remove plain text pattern
    cleaned = re.sub(
        r'inklusive\s+\d+%\s+Rabatt',
        '',
        cleaned,
        flags=re.IGNORECASE
    )

    # Clean up extra whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()

    return cleaned
