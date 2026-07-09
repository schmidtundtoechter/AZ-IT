from az_it.az_it.api.telephony import push_contact_to_3cx


def push_if_synced(doc, method):
    """on_update hook: re-push to 3CX phonebook if this contact was already synced."""
    if not doc.custom_3cx_synced:
        return

    def primary(attr):
        return next((p.phone for p in (doc.phone_nos or []) if getattr(p, attr, False)), "")

    push_contact_to_3cx({
        "first_name": doc.first_name or "",
        "last_name": doc.last_name or "",
        "company_name": doc.company_name or "",
        "email": doc.email_id or "",
        "phone_business": primary("is_primary_phone"),
        "phone_mobile": primary("is_primary_mobile_no"),
    })
