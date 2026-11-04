"""Customer shipping messages (FUL-007/008), English and Nepali.

Sent only into a conversation the customer started with the shop (that's the permission), only when
the merchant has customer notifications on, and at most once per parcel and kind. Fixed templates:
no AI wording, so they're predictable and never promise anything the data doesn't support.
"""

from __future__ import annotations

from app.domains.inbox.agent import money

T: dict[str, dict[str, str]] = {
    "shipped": {
        "en": "Good news! Your order #{number} is on its way with {courier}.{tracking}{cod}",
        "ne": "खुसीको खबर! तपाईंको अर्डर #{number} {courier} मार्फत पठाइयो।{tracking}{cod}",
    },
    "tracking": {"en": " Tracking number: {tracking}.", "ne": " ट्र्याकिङ नम्बर: {tracking}।"},
    "cod_ready": {
        "en": " Please keep {amount} ready for the rider.",
        "ne": " कृपया राइडरलाई दिन {amount} तयार राख्नुहोस्।",
    },
    "out_for_delivery": {
        "en": "Your order #{number} is out for delivery today. Please keep your phone on.{cod}",
        "ne": "तपाईंको अर्डर #{number} आज डेलिभरीमा निस्केको छ। कृपया फोन खुला राख्नुहोस्।{cod}",
    },
    "delivered": {
        "en": "Your order #{number} has been delivered. Thank you for shopping with {shop}!",
        "ne": "तपाईंको अर्डर #{number} डेलिभर भयो। {shop} बाट किनमेल गर्नुभएकोमा धन्यवाद!",
    },
    "delivery_failed": {
        "en": "We couldn't deliver your order #{number} ({reason}). Please reply with a good time to deliver, or a corrected address or landmark, and we'll arrange another attempt.",
        "ne": "तपाईंको अर्डर #{number} डेलिभर हुन सकेन ({reason})। कृपया डेलिभरीको लागि उपयुक्त समय, वा सही ठेगाना/चिनारी लेखेर पठाउनुहोस्, हामी फेरि पठाउने व्यवस्था गर्छौं।",
    },
    "reattempt_requested": {
        "en": "Thank you! We've asked the courier to deliver order #{number} again.",
        "ne": "धन्यवाद! अर्डर #{number} फेरि डेलिभर गर्न कुरियरलाई भनेका छौं।",
    },
    "reply_noted": {
        "en": "Thank you! The shop will arrange another delivery of order #{number} and confirm with you.",
        "ne": "धन्यवाद! पसलले अर्डर #{number} फेरि डेलिभर गर्ने व्यवस्था गरी जानकारी दिनेछ।",
    },
}

REASONS: dict[str, dict[str, str]] = {
    "en": {
        "customer_unreachable": "the rider couldn't reach your phone",
        "customer_unavailable": "nobody was available to receive it",
        "customer_refused": "the parcel was refused",
        "address_incorrect": "the rider couldn't find the address",
        "cod_not_ready": "the cash payment wasn't ready",
        "rescheduled_by_customer": "you asked for another time",
        "other": "the courier reported a problem",
    },
    "ne": {
        "customer_unreachable": "राइडरले फोनमा सम्पर्क गर्न सकेनन्",
        "customer_unavailable": "बुझ्ने कोही हुनुहुन्नथ्यो",
        "customer_refused": "पार्सल अस्वीकार गरियो",
        "address_incorrect": "राइडरले ठेगाना भेट्टाउन सकेनन्",
        "cod_not_ready": "नगद भुक्तानी तयार थिएन",
        "rescheduled_by_customer": "तपाईंले अर्को समय माग्नुभयो",
        "other": "कुरियरले समस्या जनायो",
    },
}


def text(kind: str, locale: str, **kw: object) -> str:
    loc = locale if locale in ("en", "ne") else "en"
    return T[kind][loc].format(**kw)


def shipped(locale: str, number: int, courier: str, tracking: str | None, cod_minor: int) -> str:
    return text(
        "shipped",
        locale,
        number=number,
        courier=courier,
        tracking=text("tracking", locale, tracking=tracking) if tracking else "",
        cod=text("cod_ready", locale, amount=money(cod_minor, locale)) if cod_minor else "",
    )


def out_for_delivery(locale: str, number: int, cod_minor: int) -> str:
    return text(
        "out_for_delivery",
        locale,
        number=number,
        cod=text("cod_ready", locale, amount=money(cod_minor, locale)) if cod_minor else "",
    )


def delivery_failed(locale: str, number: int, reason: str) -> str:
    loc = locale if locale in ("en", "ne") else "en"
    return text("delivery_failed", loc, number=number, reason=REASONS[loc].get(reason, REASONS[loc]["other"]))
