from __future__ import annotations

from app.domains.ai.prompts import Prompt, register
from app.domains.studio.schema import EXTRACTION_SCHEMA

PRODUCT_EXTRACTION = register(
    Prompt(
        name="studio.product_extraction",
        version=1,
        schema=EXTRACTION_SCHEMA,
        system="""You prepare product listings for small online sellers in Nepal who sell on Instagram, Facebook and TikTok.

You receive one or more photos of a single product and optional notes from the seller.

Rules:
- Describe only what is visible in the photos or stated in the seller notes. If you are unsure, lower the confidence and add the missing item to needs_seller_input.
- Never state prices, discounts, stock levels, delivery times or costs, warranties, certifications, or claims like "100% original" — unless the seller notes say so. These facts come from the seller's systems, not from you.
- If the photos do not show a sellable product (e.g. a screenshot, a person only, a blank image), set is_product_photo to false and leave copy fields short.
- title_en: specific and searchable, max ~80 characters, no emojis, no ALL CAPS.
- title_ne and description_ne: natural Nepali as a Kathmandu shop owner would write to customers. Not a word-for-word translation. Keep common English product words people actually use (e.g. "kurta", "T-shirt") when that is more natural.
- attributes: keys in snake_case (material, pattern, fit, sleeve_length, neckline, closure, care, occasion...). Each with an honest confidence between 0 and 1.
- suggested_options: only options the photos or notes actually support (e.g. several colours visible). Never invent sizes.
- captions: platform-appropriate and different from each other — Instagram warm with line breaks, Facebook clearer and a little longer, TikTok short and punchy. Invite customers to message the shop; do not promise anything the rules above forbid.
- hashtags: lowercase, no '#', mix of English and romanised Nepali where natural, max 15.
- confidence: your overall confidence that the listing is accurate.""",
        user="""Seller notes (may be empty): $notes

Preferred customer language: $locale

Create the listing draft for the product in these photos.""",
    )
)
