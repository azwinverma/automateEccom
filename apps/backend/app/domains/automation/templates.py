"""Ready-made commerce workflows (AUT-013). Text is English + Nepali; the seller can edit any of it."""

from __future__ import annotations

from typing import Any

TEMPLATES: list[dict[str, Any]] = [
    {
        "code": "book_courier_when_packed",
        "definition": {
            "trigger": {"event": "order.status_changed", "filter": ["ready_to_ship"]},
            "steps": [
                {
                    "id": "complete",
                    "type": "condition",
                    "when": {"field": "order.address_complete", "op": "is_true"},
                    "else": "stop",
                },
                {"id": "book", "type": "action", "action": "book_courier"},
                {"id": "pickup", "type": "action", "action": "request_pickup"},
            ],
        },
    },
    {
        "code": "review_request_after_delivery",
        "definition": {
            "trigger": {"event": "order.status_changed", "filter": ["delivered"]},
            "steps": [
                {"id": "wait", "type": "wait", "hours": 72},
                {
                    "id": "still_delivered",
                    "type": "condition",
                    "when": {"field": "order.status", "op": "in", "value": ["delivered", "completed"]},
                    "else": "stop",
                },
                {"id": "ask", "type": "action", "action": "send_review_request"},
            ],
        },
    },
    {
        "code": "thank_first_order",
        "definition": {
            "trigger": {"event": "order.created"},
            "steps": [
                {
                    "id": "first",
                    "type": "condition",
                    "when": {"field": "customer.first_order", "op": "is_true"},
                    "else": "stop",
                },
                {
                    "id": "thanks",
                    "type": "action",
                    "action": "send_customer_message",
                    "params": {
                        "text_en": "Welcome to {shop}, {name}! Thank you for your first order {number}. We'll message you when it ships.",
                        "text_ne": "{shop} मा स्वागत छ, {name}! पहिलो अर्डर {number} को लागि धन्यवाद। पठाएपछि खबर गर्छौं।",
                    },
                },
            ],
        },
    },
    {
        "code": "low_stock_alert",
        "definition": {
            "trigger": {"event": "inventory.low_stock"},
            "steps": [
                {
                    "id": "tell",
                    "type": "action",
                    "action": "notify_seller",
                    "params": {"message": "Stock is running low. Check your inventory."},
                }
            ],
        },
    },
    {
        "code": "failed_delivery_followup",
        "definition": {
            "trigger": {"event": "shipment.status_changed", "filter": ["delivery_failed"]},
            "steps": [
                {"id": "wait", "type": "wait", "hours": 24},
                {
                    "id": "still_failed",
                    "type": "condition",
                    "when": {"field": "shipment.status", "op": "eq", "value": "delivery_failed"},
                    "else": "stop",
                },
                {
                    "id": "few",
                    "type": "branch",
                    "when": {"field": "shipment.attempt_count", "op": "lt", "value": 3},
                    "then": "retry",
                    "else": "tell",
                },
                {
                    "id": "retry",
                    "type": "action",
                    "action": "request_reattempt",
                    "params": {"note": "Please try again; the customer was informed."},
                    "next": "stop",
                },
                {
                    "id": "tell",
                    "type": "action",
                    "action": "notify_seller",
                    "params": {
                        "message": "Order {number} failed delivery several times. Call the customer or bring it back."
                    },
                },
            ],
        },
    },
    {
        "code": "approve_small_returns",
        "definition": {
            "trigger": {"event": "return.status_changed", "filter": ["requested"]},
            "steps": [{"id": "approve", "type": "action", "action": "approve_return"}],
        },
    },
]
BY_CODE = {t["code"]: t for t in TEMPLATES}
