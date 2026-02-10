# -*- coding: utf-8 -*-
# Copyright (c) 2025, ahmad mohammad and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def validate_preisanpassung(doc, method=None):
    """
    Validate that the price adjustment checkbox is explicitly checked before saving.

    This ensures users confirm they have reviewed and adjusted all imported prices
    before saving or submitting a Sales Order.

    Args:
        doc: Sales Order document
        method: Hook method (not used but required by Frappe)

    Raises:
        frappe.ValidationError: If checkbox is not explicitly checked
    """
    # Check if the field exists (for backwards compatibility)
    if not hasattr(doc, 'preisanpassung_erfolgt_sa'):
        return

    # The field must be explicitly set to 1 (checked)
    # Using != 1 instead of == 0 to catch None, empty string, False, etc.
    if doc.preisanpassung_erfolgt_sa != 1:
        frappe.throw(
            _(
                "Bitte bestätigen Sie, dass die Preisanpassung erfolgt ist, "
                "indem Sie das Kontrollkästchen 'Preisanpassung erfolgt' aktivieren."
            ),
            title=_("Preisanpassung erforderlich")
        )
