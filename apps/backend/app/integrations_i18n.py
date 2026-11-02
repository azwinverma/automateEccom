"""Transactional email copy (en/ne). Kept short and plain; reviewed copy belongs in the UX writing
process (specs/19, missing — see KNOWN_GAPS)."""

from __future__ import annotations

_COPY: dict[str, dict[str, tuple[str, str]]] = {
    "verify_email": {
        "en": (
            "Confirm your email",
            "Hi {name},\n\nConfirm your email to finish setting up your shop:\n{link}\n\n"
            "This link expires in 24 hours. If you didn't sign up, ignore this email.",
        ),
        "ne": (
            "आफ्नो इमेल पुष्टि गर्नुहोस्",
            "नमस्ते {name},\n\nपसल सेटअप पूरा गर्न इमेल पुष्टि गर्नुहोस्:\n{link}\n\n"
            "यो लिंक २४ घण्टापछि काम गर्दैन। तपाईंले साइन अप गर्नुभएको होइन भने यो इमेल बेवास्ता गर्नुहोस्।",
        ),
    },
    "team_invite": {
        "en": (
            "You're invited to {shop}",
            "You've been invited to help run {shop} as {role}.\n\n"
            "Accept the invitation:\n{link}\n\nThis invitation expires in 7 days.",
        ),
        "ne": (
            "{shop} मा तपाईंलाई निम्तो",
            "{shop} चलाउन {role} को रूपमा सहयोग गर्न तपाईंलाई निम्तो पठाइएको छ।\n\n"
            "निम्तो स्वीकार गर्नुहोस्:\n{link}\n\nयो निम्तो ७ दिनपछि सकिन्छ।",
        ),
    },
}


def email_copy(key: str, locale: str, **params: str) -> tuple[str, str]:
    variants = _COPY[key]
    subject, body = variants.get(locale, variants["en"])
    return subject.format(**params), body.format(**params)
