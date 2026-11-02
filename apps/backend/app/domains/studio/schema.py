"""Structured output contract for product extraction. Deliberately has NO price, stock, delivery or
discount fields: commercial facts come from the seller and internal services, never from the model."""

from __future__ import annotations

from typing import Any

_str: dict[str, Any] = {"type": "string"}
_num: dict[str, Any] = {"type": "number", "minimum": 0, "maximum": 1}
_strs: dict[str, Any] = {"type": "array", "items": _str}

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "is_product_photo",
        "category",
        "title_en",
        "title_ne",
        "description_en",
        "description_ne",
        "bullets_en",
        "attributes",
        "colors",
        "suggested_options",
        "seo",
        "hashtags",
        "captions",
        "needs_seller_input",
        "confidence",
    ],
    "properties": {
        "is_product_photo": {"type": "boolean"},
        "category": {
            "type": "object",
            "additionalProperties": False,
            "required": ["path", "confidence"],
            "properties": {"path": _strs, "confidence": _num},
        },
        "title_en": _str,
        "title_ne": _str,
        "description_en": _str,
        "description_ne": _str,
        "bullets_en": _strs,
        "attributes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["key", "value", "confidence"],
                "properties": {"key": _str, "value": _str, "confidence": _num},
            },
        },
        "colors": _strs,
        "suggested_options": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "values"],
                "properties": {"name": _str, "values": _strs},
            },
        },
        "seo": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "description"],
            "properties": {"title": _str, "description": _str},
        },
        "hashtags": _strs,
        "captions": {
            "type": "object",
            "additionalProperties": False,
            "required": ["instagram", "facebook", "tiktok"],
            "properties": {"instagram": _str, "facebook": _str, "tiktok": _str},
        },
        "needs_seller_input": _strs,
        "confidence": _num,
    },
}

# Post-validation limits (kept out of the provider schema because providers support different keywords).
LIMITS = {
    "title_en": 120,
    "title_ne": 120,
    "description_en": 2000,
    "description_ne": 2000,
    "seo.title": 70,
    "seo.description": 320,
    "bullets_en": 6,
    "hashtags": 15,
    "attributes": 20,
    "caption": 2200,
}
