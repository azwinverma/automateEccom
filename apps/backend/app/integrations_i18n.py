"""Transactional email copy (en/ne). Plain, short, signed by Nivaro (specs/19, specs/26 voice)."""

from __future__ import annotations

_COPY: dict[str, dict[str, tuple[str, str]]] = {
    "verify_email": {
        "en": (
            "Confirm your email for Nivaro",
            "Hi {name},\n\nConfirm your email to finish setting up your shop:\n{link}\n\n"
            "This link expires in 24 hours. If you didn't sign up, ignore this email.\n\n— Nivaro",
        ),
        "ne": (
            "आफ्नो इमेल पुष्टि गर्नुहोस्",
            "नमस्ते {name},\n\nपसल सेटअप पूरा गर्न इमेल पुष्टि गर्नुहोस्:\n{link}\n\n"
            "यो लिंक २४ घण्टापछि काम गर्दैन। तपाईंले साइन अप गर्नुभएको होइन भने यो इमेल बेवास्ता गर्नुहोस्।\n\n— Nivaro",
        ),
    },
    "password_reset": {
        "en": (
            "Reset your Nivaro password",
            "Hi {name},\n\nReset your password here:\n{link}\n\n"
            "This link works once and expires in 30 minutes. If you didn't ask for this, ignore this "
            "email: your password stays the same.\n\n— Nivaro",
        ),
        "ne": (
            "Nivaro पासवर्ड रिसेट गर्नुहोस्",
            "नमस्ते {name},\n\nयहाँबाट पासवर्ड रिसेट गर्नुहोस्:\n{link}\n\n"
            "यो लिंक एक पटक मात्र र ३० मिनेटसम्म चल्छ। तपाईंले माग्नुभएको होइन भने यो इमेल बेवास्ता गर्नुहोस्: "
            "तपाईंको पासवर्ड परिवर्तन हुँदैन।\n\n— Nivaro",
        ),
    },
    "password_changed": {
        "en": (
            "Your Nivaro password was changed",
            "Hi {name},\n\nYour password was just changed and every device was signed out. "
            "Sign in again here: {link}\n\nIf this wasn't you, reset your password straight away and "
            "contact support.\n\n— Nivaro",
        ),
        "ne": (
            "तपाईंको Nivaro पासवर्ड परिवर्तन भयो",
            "नमस्ते {name},\n\nतपाईंको पासवर्ड भर्खरै परिवर्तन भयो र सबै डिभाइसबाट साइन आउट गरियो। "
            "फेरि साइन इन: {link}\n\nयो तपाईं होइन भने तुरुन्तै पासवर्ड रिसेट गर्नुहोस् र सपोर्टलाई "
            "सम्पर्क गर्नुहोस्।\n\n— Nivaro",
        ),
    },
    "team_invite": {
        "en": (
            "You're invited to {shop}",
            "You've been invited to help run {shop} as {role}.\n\n"
            "Accept the invitation:\n{link}\n\nThis invitation expires in 7 days.\n\n— Nivaro",
        ),
        "ne": (
            "{shop} मा तपाईंलाई निम्तो",
            "{shop} चलाउन {role} को रूपमा सहयोग गर्न तपाईंलाई निम्तो पठाइएको छ।\n\n"
            "निम्तो स्वीकार गर्नुहोस्:\n{link}\n\nयो निम्तो ७ दिनपछि सकिन्छ।\n\n— Nivaro",
        ),
    },
    "usage_warning": {
        "en": (
            "{shop}: {threshold}% of your {resource} used this month",
            "Hi {name},\n\n{shop} has used {used} of {limit} {resource} this month ({threshold}%).\n\n"
            "When you reach the limit, new ones pause until next month unless you add credits or change "
            "plan. See your usage:\n{link}\n\n— Nivaro",
        ),
        "ne": (
            "{shop}: यो महिनाको {resource} {threshold}% प्रयोग भयो",
            "नमस्ते {name},\n\n{shop} ले यो महिना {limit} मध्ये {used} {resource} प्रयोग गरिसक्यो "
            "({threshold}%)।\n\nसीमा पुगेपछि क्रेडिट थप्नुभएन वा प्लान बदल्नुभएन भने अर्को महिनासम्म नयाँ रोकिन्छ। "
            "प्रयोग हेर्नुहोस्:\n{link}\n\n— Nivaro",
        ),
    },
    "usage_limit_reached": {
        "en": (
            "{shop}: monthly {resource} limit reached",
            "Hi {name},\n\n{shop} has used all {limit} {resource} included this month. New ones are "
            "paused until the month resets, unless you add credits or change plan:\n{link}\n\n"
            "Everything already made keeps working.\n\n— Nivaro",
        ),
        "ne": (
            "{shop}: यो महिनाको {resource} सीमा पुग्यो",
            "नमस्ते {name},\n\n{shop} ले यो महिनामा समावेश भएका सबै {limit} {resource} प्रयोग गर्‍यो। "
            "क्रेडिट थप्नुभएन वा प्लान बदल्नुभएन भने महिना नफेरिउन्जेल नयाँ रोकिन्छ:\n{link}\n\n"
            "पहिले बनेका सबै चलिरहन्छन्।\n\n— Nivaro",
        ),
    },
}

# Seller-facing names for metered resources in emails (the web/mobile apps carry their own copies).
RESOURCE_NAMES: dict[str, dict[str, str]] = {
    "en": {
        "orders": "orders",
        "ai_text_generations": "AI writing credits",
        "ai_inbox_replies": "AI inbox replies",
        "ai_images": "AI images",
        "auto_reels": "Auto Reels",
        "premium_video_clips": "premium video clips",
        "automation_runs": "automation runs",
        "api_requests": "API requests",
    },
    "ne": {
        "orders": "अर्डर",
        "ai_text_generations": "AI लेखन",
        "ai_inbox_replies": "AI इनबक्स जवाफ",
        "ai_images": "AI तस्बिर",
        "auto_reels": "अटो रिल",
        "premium_video_clips": "प्रिमियम भिडियो क्लिप",
        "automation_runs": "अटोमेसन रन",
        "api_requests": "API अनुरोध",
    },
}


def resource_name(code: str, locale: str) -> str:
    return RESOURCE_NAMES.get(locale, RESOURCE_NAMES["en"]).get(code) or RESOURCE_NAMES["en"].get(code, code)


def email_copy(key: str, locale: str, **params: str) -> tuple[str, str]:
    variants = _COPY[key]
    subject, body = variants.get(locale, variants["en"])
    return subject.format(**params), body.format(**params)
