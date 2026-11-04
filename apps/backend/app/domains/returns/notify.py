"""Customer messages about a return (en/ne), into the customer's own chat only. Fixed templates."""

from __future__ import annotations

from typing import Any

from app.domains.inbox.agent import money

T: dict[str, dict[str, str]] = {
    "approved_refund": {
        "en": "Your return {number} for order #{order} is approved. We'll arrange the pickup and refund you once the item is back with us.",
        "ne": "अर्डर #{order} को फिर्ता {number} स्वीकृत भयो। सामान लिन व्यवस्था गर्छौं, सामान आइपुगेपछि रकम फिर्ता गर्छौं।",
    },
    "approved_exchange": {
        "en": "Your exchange {number} for order #{order} is approved. We've kept the replacement aside and will send it once the item is back with us.",
        "ne": "अर्डर #{order} को साट्ने अनुरोध {number} स्वीकृत भयो। नयाँ सामान छुट्याएर राखेका छौं, पुरानो सामान आइपुगेपछि पठाउँछौं।",
    },
    "rejected": {
        "en": "Sorry, we can't accept return {number} for order #{order}: {reason}",
        "ne": "माफ गर्नुहोस्, अर्डर #{order} को फिर्ता {number} स्वीकार गर्न सकिएन: {reason}",
    },
    "received": {
        "en": "We've received your return {number}. We'll check it and update you shortly.",
        "ne": "तपाईंको फिर्ता {number} हामीलाई आइपुग्यो। जाँचेर छिट्टै जानकारी दिन्छौं।",
    },
    "refunded": {
        "en": "Your refund for return {number} has been sent.",
        "ne": "फिर्ता {number} को रकम पठाइयो।",
    },
    "exchanged": {
        "en": "Your replacement for return {number} is on its way soon: new order #{exchange}.",
        "ne": "फिर्ता {number} को सट्टा नयाँ सामान छिट्टै पठाउँछौं: नयाँ अर्डर #{exchange}।",
    },
}


def message(r: Any, o: Any, locale: str) -> str | None:
    loc = locale if locale in ("en", "ne") else "en"
    kw: dict[str, Any] = {"number": r.number, "order": o.number}
    if r.status == "approved":
        key = "approved_exchange" if r.resolution == "exchange" else "approved_refund"
    elif r.status == "rejected":
        key, kw["reason"] = "rejected", r.rejection_reason or ""
    elif r.status in ("received", "refunded"):
        key = r.status
    elif r.status == "exchanged" and r.exchange_order_id:
        from sqlalchemy.orm import object_session

        from app.domains.orders.models import Order

        db = object_session(r)
        ex = db.get(Order, r.exchange_order_id) if db else None
        key, kw["exchange"] = "exchanged", ex.number if ex else ""
    else:
        return None
    _ = money  # amounts aren't quoted: the refund method/timing is the shop's
    return T[key][loc].format(**kw)
