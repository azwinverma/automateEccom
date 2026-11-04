"""AI Sales Agent (CRM-009…012, ORD-006): grounded answers and chat-to-order.

Rules (spec 11):
* Transactional facts (price, stock, order status, options) come from tools that read Commerce Core,
  never from a model. Replies are bilingual templates filled with those facts, so every number a
  customer sees was looked up. ``Message.grounding`` records what was looked up.
* The agent asks only for what's missing, one thing at a time, then shows a summary and waits for an
  explicit "yes". The order is created idempotently on (conversation, draft version).
* It escalates instead of guessing: complaints, returns/refunds/exchanges, cancellations, a request
  for a person, or a tool failure. It sends a short holding message and hands over.
* Decision Policy: an AI reply is sent automatically only in Smart/Autopilot mode, with
  ``inbox.ai_replies`` in the plan, enough AI-reply allowance and confidence ≥ 0.8. Otherwise it's a
  suggestion the seller approves. Assisted mode never auto-sends.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.context import Actor, TenantContext
from app.core.db import bind_tenant
from app.core.errors import AppError, UsageLimitReached
from app.domains.billing.service import entitlements
from app.domains.catalog.models import Product, ProductOption, ProductOptionValue, Variant, VariantOptionValue
from app.domains.customers import nepal
from app.domains.customers import service as customers
from app.domains.customers.models import Customer
from app.domains.inbox import service as inbox
from app.domains.inbox.extract import Extracted, option_match, understand
from app.domains.inbox.models import INTENTS, Conversation, Message, OrderDraft
from app.domains.inventory import service as inventory
from app.domains.merchants.models import Merchant
from app.domains.orders import service as orders
from app.domains.orders.models import Order
from app.domains.platform.models import OutboxEvent
from app.domains.platform.outbox import handler

log = structlog.get_logger(__name__)
AUTO_SEND_MIN_CONFIDENCE = 0.8
AI_FILL_MIN_CONFIDENCE = 0.7
ESCALATE = {"human", "complaint", "return", "exchange", "refund", "cancellation"}
SLOTS = (
    "product",
    "variant",
    "quantity",
    "name",
    "phone",
    "district",
    "municipality",
    "ward",
    "area",
    "payment",
)
SKIP = re.compile(r"^\s*(skip|no|none|chaina|छैन|पर्दैन|-)\s*$", re.I)

T: dict[str, dict[str, str]] = {
    "product": {
        "en": "{title}: {price}. {stock}",
        "ne": "{title}: {price}। {stock}",
    },
    "in_stock": {"en": "In stock ({n} available).", "ne": "स्टकमा छ ({n} वटा)।"},
    "low_stock": {"en": "Only {n} left.", "ne": "{n} वटा मात्र बाँकी।"},
    "out_of_stock": {"en": "Sorry, it's out of stock right now.", "ne": "माफ गर्नुहोस्, अहिले स्टकमा छैन।"},
    "stock_unknown": {"en": "The shop will confirm stock.", "ne": "स्टक पसलले पक्का गर्नेछ।"},
    "options": {"en": "Available options: {options}.", "ne": "उपलब्ध विकल्प: {options}।"},
    "want_order": {
        "en": "Would you like to order? Tell me the size/colour and quantity.",
        "ne": "अर्डर गर्न चाहनुहुन्छ? साइज/रङ र कति वटा भन्नुहोस्।",
    },
    "which_product": {
        "en": "Which product are you asking about? Please send its name or a screenshot.",
        "ne": "कुन सामानको बारेमा सोध्दै हुनुहुन्छ? नाम वा स्क्रिनसट पठाउनुहोस्।",
    },
    "pick_product": {"en": "Which one? {options}", "ne": "कुन चाहिँ? {options}"},
    "ask_variant": {"en": "Which {option}? {values}", "ne": "कुन {option}? {values}"},
    "ask_quantity": {"en": "How many would you like?", "ne": "कति वटा चाहियो?"},
    "ask_name": {"en": "What name should the delivery be under?", "ne": "डेलिभरी कसको नाममा गर्ने?"},
    "ask_phone": {"en": "Your mobile number for the delivery?", "ne": "डेलिभरीको लागि मोबाइल नम्बर?"},
    "bad_phone": {
        "en": "That doesn't look like a Nepal mobile number. Please send a 10-digit number starting with 98, 97 or 96.",
        "ne": "यो नेपाली मोबाइल नम्बर जस्तो लागेन। ९८, ९७ वा ९६ बाट सुरु हुने १० अंकको नम्बर पठाउनुहोस्।",
    },
    "ask_district": {"en": "Which district should we deliver to?", "ne": "कुन जिल्लामा डेलिभरी गर्ने?"},
    "ask_municipality": {
        "en": "Which municipality (city) and ward number?",
        "ne": "कुन नगरपालिका/गाउँपालिका र वडा नम्बर?",
    },
    "ask_ward": {"en": "Which ward number?", "ne": "वडा नम्बर कति?"},
    "ask_area": {
        "en": "Area/tole and a nearby landmark? (or say skip)",
        "ne": "टोल र नजिकको चिनारी? (नभए 'छैन' भन्नुहोस्)",
    },
    "ask_payment": {"en": "Cash on delivery or pay online?", "ne": "डेलिभरीमा नगद कि अनलाइन भुक्तानी?"},
    "summary": {
        "en": "Please confirm your order:\n{lines}\nTotal: {total} (+ delivery charge, confirmed by the shop)\nDeliver to: {name}, {phone}, {address}\nPayment: {payment}\nReply YES to confirm or NO to cancel.",
        "ne": "कृपया अर्डर पक्का गर्नुहोस्:\n{lines}\nजम्मा: {total} (+ डेलिभरी शुल्क, पसलले पक्का गर्नेछ)\nठेगाना: {name}, {phone}, {address}\nभुक्तानी: {payment}\nपक्का गर्न 'हो', रद्द गर्न 'होइन' लेख्नुहोस्।",
    },
    "summary_fee": {
        "en": "Please confirm your order:\n{lines}\nDelivery: {fee}\nTotal: {total}\nDeliver to: {name}, {phone}, {address}\nPayment: {payment}\nReply YES to confirm or NO to cancel.",
        "ne": "कृपया अर्डर पक्का गर्नुहोस्:\n{lines}\nडेलिभरी शुल्क: {fee}\nजम्मा: {total}\nठेगाना: {name}, {phone}, {address}\nभुक्तानी: {payment}\nपक्का गर्न 'हो', रद्द गर्न 'होइन' लेख्नुहोस्।",
    },
    "free_delivery": {"en": "Free", "ne": "निःशुल्क"},
    "confirmed": {
        "en": "Order #{number} confirmed. Total {total}. We'll let you know when it ships. Thank you!",
        "ne": "अर्डर #{number} पक्का भयो। जम्मा {total}। पठाएपछि खबर गर्छौं। धन्यवाद!",
    },
    "pay_link": {"en": "Pay here: {url}", "ne": "यहाँ भुक्तानी गर्नुहोस्: {url}"},
    "pay_later": {"en": "The shop will send you payment details.", "ne": "पसलले भुक्तानी विवरण पठाउनेछ।"},
    "draft_cancelled": {
        "en": "No problem, I've cancelled that order request.",
        "ne": "हुन्छ, अर्डर अनुरोध रद्द गरें।",
    },
    "sold_out_now": {
        "en": "Sorry, {title} just went out of stock ({n} left). Would you like a different quantity or option?",
        "ne": "माफ गर्नुहोस्, {title} अहिले सकियो ({n} वटा बाँकी)। अर्को संख्या वा विकल्प चाहिन्छ?",
    },
    "order_status": {"en": "Order #{number}: {status}.", "ne": "अर्डर #{number}: {status}।"},
    "no_order": {
        "en": "I couldn't find an order for you yet. A team member will check.",
        "ne": "तपाईंको अर्डर भेटिएन। हाम्रो टोलीले हेर्नेछ।",
    },
    "handoff": {
        "en": "Thanks for letting us know. A team member will reply shortly.",
        "ne": "जानकारीको लागि धन्यवाद। हाम्रो टोलीले छिट्टै जवाफ दिनेछ।",
    },
    "return_open": {
        "en": "Order #{number} can be returned or exchanged until {date}. A team member will arrange it with you shortly.",
        "ne": "अर्डर #{number} {date} सम्म फिर्ता वा साट्न मिल्छ। हाम्रो टोलीले छिट्टै व्यवस्था गर्नेछ।",
    },
    "return_closed": {
        "en": "The return period for order #{number} ended on {date}. A team member will check what we can do.",
        "ne": "अर्डर #{number} फिर्ता गर्ने समय {date} मा सकियो। हाम्रो टोलीले के गर्न सकिन्छ हेर्नेछ।",
    },
    "cod": {"en": "Cash on delivery", "ne": "डेलिभरीमा नगद"},
    "prepaid": {"en": "Online payment", "ne": "अनलाइन भुक्तानी"},
}
STATUS_WORDS: dict[str, dict[str, str]] = {
    "en": {
        "cod_pending": "confirmed, being packed",
        "payment_pending": "waiting for payment",
        "ready_to_ship": "packed, ready to ship",
        "shipped": "on the way",
        "delivered": "delivered",
        "completed": "delivered",
        "cancelled": "cancelled",
        "delivery_failed": "delivery attempt failed, we'll contact you",
        "returned": "returned",
        "confirmed": "confirmed",
        "pending_confirmation": "waiting for confirmation",
    },
    "ne": {
        "cod_pending": "पक्का भयो, प्याक हुँदैछ",
        "payment_pending": "भुक्तानी कुर्दै",
        "ready_to_ship": "प्याक भयो, पठाउन तयार",
        "shipped": "बाटोमा छ",
        "delivered": "डेलिभर भयो",
        "completed": "डेलिभर भयो",
        "cancelled": "रद्द भयो",
        "delivery_failed": "डेलिभरी हुन सकेन, सम्पर्क गर्छौं",
        "returned": "फिर्ता भयो",
        "confirmed": "पक्का भयो",
        "pending_confirmation": "पक्का हुन बाँकी",
    },
}


def t(key: str, locale: str, **kw: Any) -> str:
    v = T[key]
    return v.get(locale, v["en"]).format(**kw)


def money(minor: int, locale: str) -> str:
    rupees = minor / 100
    s = f"{rupees:,.0f}" if minor % 100 == 0 else f"{rupees:,.2f}"
    return f"रु {s}" if locale == "ne" else f"Rs {s}"


# ----------------------------------------------------------------------------- tools (read Commerce Core)
@dataclass
class ProductFacts:
    product: Product
    variants: list[Variant]
    options: dict[str, list[str]]  # option name → values in use
    variant_values: dict[uuid.UUID, dict[str, str]]


def tool_find_products(
    db: Session, merchant_id: uuid.UUID, words: list[str], product_ref: str | None, limit: int = 3
) -> list[Product]:
    """get_product: active products matching the message (or the post the customer wrote from)."""
    if product_ref:
        try:
            p = db.get(Product, uuid.UUID(product_ref))
        except ValueError:
            p = None
        if p is not None and p.merchant_id == merchant_id and p.status == "active":
            return [p]
    words = [w for w in words if len(w) >= 3][:12]
    if not words:
        return []
    rows = list(
        db.scalars(
            select(Product).where(
                Product.merchant_id == merchant_id,
                Product.status == "active",
                or_(
                    *[func.lower(Product.title).contains(w) for w in words],
                    *[func.lower(func.coalesce(Product.title_ne, "")).contains(w) for w in words],
                ),
            )
        )
    )
    rows.sort(
        key=lambda p: -sum(w in (p.title or "").lower() or w in (p.title_ne or "").lower() for w in words)
    )
    if len(rows) > 1:
        best = sum(w in rows[0].title.lower() for w in words)
        rows = [p for p in rows if sum(w in p.title.lower() for w in words) == best]
    return rows[:limit]


def tool_product_facts(db: Session, p: Product) -> ProductFacts:
    variants = list(
        db.scalars(
            select(Variant)
            .where(Variant.product_id == p.id, Variant.status == "active")
            .order_by(Variant.position)
        )
    )
    rows = db.execute(
        select(VariantOptionValue.variant_id, ProductOption.name, ProductOptionValue.value)
        .join(ProductOptionValue, ProductOptionValue.id == VariantOptionValue.option_value_id)
        .join(ProductOption, ProductOption.id == ProductOptionValue.option_id)
        .where(VariantOptionValue.variant_id.in_([v.id for v in variants]))
    ).all()
    vv: dict[uuid.UUID, dict[str, str]] = {}
    opts: dict[str, list[str]] = {}
    for vid, name, value in rows:
        vv.setdefault(vid, {})[name] = value
        if value not in opts.setdefault(name, []):
            opts[name].append(value)
    return ProductFacts(p, variants, opts, vv)


def tool_availability(
    db: Session, merchant_id: uuid.UUID, variant_ids: list[uuid.UUID]
) -> dict[uuid.UUID, inventory.Availability]:
    """get_inventory."""
    return inventory.availability(db, merchant_id, variant_ids)


def tool_latest_order(db: Session, customer_id: uuid.UUID) -> Order | None:
    """get_order."""
    return db.scalar(select(Order).where(Order.customer_id == customer_id).order_by(Order.id.desc()).limit(1))


def match_variant(
    facts: ProductFacts, text: str, chosen: dict[str, str]
) -> tuple[Variant | None, dict[str, str]]:
    picked = dict(chosen)
    for name, values in facts.options.items():
        for val in values:
            if option_match(text, val):
                picked[name] = val
    if len(facts.variants) == 1:
        return facts.variants[0], picked
    matches = [
        v
        for v in facts.variants
        if all(facts.variant_values.get(v.id, {}).get(k) == val for k, val in picked.items())
    ]
    if len(matches) == 1 and len(picked) >= len(facts.options):
        return matches[0], picked
    return None, picked


# ----------------------------------------------------------------------------- AI (optional enrichment)
INTENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "intent": {"enum": list(INTENTS)},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "customer_name": {"type": ["string", "null"], "maxLength": 80},
    },
    "required": ["intent", "confidence", "customer_name"],
}


def ai_intent(merchant_id: uuid.UUID, message: Message) -> dict[str, Any] | None:
    from app.domains.ai.gateway import gateway
    from app.domains.ai.types import AIRequest
    from app.domains.ai.types import Message as AIMessage

    try:
        res = gateway.run(
            task="INTENT_CLASSIFICATION",
            request=AIRequest(
                messages=(AIMessage(role="user", text=message.text),),
                system="Classify a shop customer's chat message (English, Nepali or Romanized Nepali). Never invent facts.",
                json_schema=INTENT_SCHEMA,
                max_tokens=200,
                prompt_name="inbox_intent",
                prompt_version=1,
            ),
            merchant_id=merchant_id,
            idempotency_key=f"intent:{message.id}",
            reference_type="message",
            reference_id=str(message.id),
        )
        return res.data if isinstance(res.data, dict) else None
    except (AppError, Exception) as e:  # no AI on the plan, provider down, budget: rules still work
        log.info("ai_intent_unavailable", reason=type(e).__name__)
        return None


# ----------------------------------------------------------------------------- reply dispatch
def _dispatch(
    db: Session,
    conv: Conversation,
    msg: Message,
    text: str,
    *,
    intent: str,
    confidence: float,
    grounding: dict[str, Any],
) -> Message:
    merchant = db.get(Merchant, conv.merchant_id)
    ent = entitlements.resolve(db, conv.merchant_id)
    auto = (
        merchant is not None
        and merchant.automation_mode in ("smart", "autopilot")
        and ent.has("inbox.ai_replies")
        and confidence >= AUTO_SEND_MIN_CONFIDENCE
    )
    if auto:
        try:
            entitlements.record(
                db,
                conv.merchant_id,
                "ai_inbox_replies",
                1,
                f"aireply:{msg.id}:{intent}",
                reference_type="message",
                reference_id=str(msg.id),
            )
        except UsageLimitReached:
            auto = False
            grounding = {**grounding, "held": "ai_reply_limit"}
    return inbox.queue_reply(
        db, conv, text, author="ai", intent=intent, confidence=confidence, grounding=grounding, send=auto
    )


def _answer_return(db: Session, conv: Conversation, msg: Message, intent: str, locale: str) -> bool:
    """check_return_eligibility(): say what the policy allows for their latest order, then hand over
    (a person creates the return). Never promises a refund amount."""
    from datetime import timedelta

    from app.core.db import utcnow
    from app.domains.returns import service as returns

    assert conv.customer_id is not None
    o = tool_latest_order(db, conv.customer_id)
    if o is None or o.status not in returns.RETURNABLE_ORDER_STATUSES:
        return False
    at = returns.delivered_at(db, o)
    if at is None:
        return False
    policy = returns.get_policy(db, conv.merchant_id)
    deadline = at + timedelta(days=policy.window_days)
    allowed = policy.allow_exchange if intent == "exchange" else policy.allow_refund
    key = "return_open" if allowed and utcnow() <= deadline else "return_closed"
    conv.escalated, conv.escalation_reason = True, intent
    _dispatch(
        db,
        conv,
        msg,
        t(key, locale, number=o.number, date=deadline.strftime("%d %b")),
        intent=intent,
        confidence=0.9,
        grounding={
            "check_return_eligibility": {
                "order_id": str(o.id),
                "deadline": deadline.isoformat(),
                "allowed": key == "return_open",
            }
        },
    )
    return True


def _escalate(db: Session, conv: Conversation, msg: Message, reason: str, locale: str) -> None:
    conv.escalated, conv.escalation_reason = True, reason
    _dispatch(
        db, conv, msg, t("handoff", locale), intent=reason, confidence=0.95, grounding={"escalated": reason}
    )


# ----------------------------------------------------------------------------- the pipeline
@handler("inbox.message_received", name="inbox.sales_agent")
def _on_message(db: Session, ev: OutboxEvent) -> None:
    conv = db.scalar(
        select(Conversation)
        .where(Conversation.id == uuid.UUID(ev.payload["conversation_id"]))
        .with_for_update()
        .execution_options(skip_tenant_filter=True)
    )
    if conv is None:
        return
    bind_tenant(db, conv.merchant_id)
    msg = db.get(Message, uuid.UUID(ev.payload["message_id"]))
    if msg is None or msg.direction != "in":
        return
    handle(db, conv, msg)


def handle(db: Session, conv: Conversation, msg: Message) -> None:
    from app.domains.fulfillment.service import capture_customer_reply

    if capture_customer_reply(db, conv, msg):
        return  # a reply to our failed-delivery question: recorded on the delivery attempt (FUL-008)
    if conv.human_handoff or conv.escalated or conv.status == "closed":
        return  # a person is handling it
    ent = entitlements.resolve(db, conv.merchant_id)
    if not ent.has("ai.sales_agent"):
        return  # plan without the Sales Agent: the seller answers from the inbox
    e = understand(msg.text)
    locale = e.locale  # answer in the script the customer just wrote in (Devanagari → Nepali)
    draft = db.scalar(
        select(OrderDraft)
        .where(
            OrderDraft.conversation_id == conv.id,
            OrderDraft.status.in_(("collecting", "awaiting_confirmation")),
        )
        .with_for_update()
    )

    intent = e.intent
    if intent is None and draft is None:
        ai = ai_intent(conv.merchant_id, msg)
        if ai and float(ai.get("confidence", 0)) >= AI_FILL_MIN_CONFIDENCE:
            intent = ai["intent"]
    intent = intent or ("order" if draft else "product_question")
    msg.intent = conv.last_intent = intent

    if draft is not None and draft.status == "awaiting_confirmation":
        if e.yes:
            _create_order(db, conv, msg, draft, locale)
            return
        if e.no:
            draft.status = "abandoned"
            _dispatch(
                db,
                conv,
                msg,
                t("draft_cancelled", locale),
                intent="order",
                confidence=0.95,
                grounding={"draft": str(draft.id)},
            )
            return
        draft.status = "collecting"  # treat it as a correction to the draft
    if (
        intent in ("return", "exchange")
        and draft is None
        and conv.customer_id
        and _answer_return(db, conv, msg, intent, locale)
    ):
        return
    if intent in ESCALATE:
        _escalate(db, conv, msg, intent, locale)
        return
    if intent == "order_status" and draft is None:
        o = tool_latest_order(db, conv.customer_id)
        if o is None:
            _escalate(db, conv, msg, "order_not_found", locale)
            return
        status = STATUS_WORDS[locale].get(o.status, o.status)
        _dispatch(
            db,
            conv,
            msg,
            t("order_status", locale, number=o.number, status=status),
            intent=intent,
            confidence=0.95,
            grounding={"get_order": {"order_id": str(o.id), "number": o.number, "status": o.status}},
        )
        return
    if draft is not None:
        _continue_draft(db, conv, msg, draft, e, locale)
        return

    products = tool_find_products(db, conv.merchant_id, e.words, (msg.grounding or {}).get("product_ref"))
    if not products and (recent := _recent_product(db, conv)) is not None:
        products = [recent]  # "XL 1 wota chahiyo" after asking about a product: same product
    if not products:
        _dispatch(
            db,
            conv,
            msg,
            t("which_product", locale),
            intent=intent,
            confidence=0.5,
            grounding={"get_product": []},
        )
        return
    if len(products) > 1:
        names = ", ".join(p.title for p in products)
        _dispatch(
            db,
            conv,
            msg,
            t("pick_product", locale, options=names),
            intent=intent,
            confidence=0.85,
            grounding={"get_product": [str(p.id) for p in products]},
        )
        return
    facts = tool_product_facts(db, products[0])
    variant, picked = match_variant(facts, msg.text, {})
    wants_order = intent == "order" or e.quantity is not None
    if wants_order and ent.has("orders.chat_to_order"):
        draft = OrderDraft(
            merchant_id=conv.merchant_id,
            conversation_id=conv.id,
            fields={"product_id": str(facts.product.id), "options": picked},
        )
        if variant is not None:
            draft.fields["variant_id"] = str(variant.id)
        if e.quantity:
            draft.fields["quantity"] = e.quantity
        db.add(draft)
        db.flush()
        _continue_draft(db, conv, msg, draft, e, locale)
        return
    _dispatch(
        db,
        conv,
        msg,
        _product_answer(db, conv, facts, variant, locale, ask_order=ent.has("orders.chat_to_order")),
        intent=intent,
        confidence=0.9,
        grounding=_facts_grounding(db, conv, facts, variant),
    )


def _recent_product(db: Session, conv: Conversation) -> Product | None:
    """The product this conversation was last about (from the agent's own recorded lookups)."""
    for m in db.scalars(
        select(Message)
        .where(Message.conversation_id == conv.id, Message.author_type == "ai")
        .order_by(Message.id.desc())
        .limit(5)
    ):
        ref = (m.grounding or {}).get("get_product")
        if isinstance(ref, dict) and ref.get("product_id"):
            p = db.get(Product, uuid.UUID(ref["product_id"]))
            if p is not None and p.status == "active":
                return p
    return None


def _facts_grounding(
    db: Session, conv: Conversation, facts: ProductFacts, variant: Variant | None
) -> dict[str, Any]:
    vids = [variant.id] if variant else [v.id for v in facts.variants]
    av = tool_availability(db, conv.merchant_id, vids)
    return {
        "get_product": {"product_id": str(facts.product.id), "title": facts.product.title},
        "get_price": {str(v.id): v.price_minor for v in facts.variants if v.id in vids},
        "get_inventory": {
            str(k): {
                "tracked": a.tracked,
                "available": a.available,
                "as_of": a.as_of.isoformat() if a.as_of else None,
            }
            for k, a in av.items()
        },
    }


def _stock_line(a: inventory.Availability, locale: str) -> str:
    if not a.tracked:
        return t("stock_unknown", locale)
    if a.available <= 0:
        return t("out_of_stock", locale)
    return t("low_stock", locale, n=a.available) if a.available <= 3 else t("in_stock", locale, n=a.available)


def _product_answer(
    db: Session,
    conv: Conversation,
    facts: ProductFacts,
    variant: Variant | None,
    locale: str,
    *,
    ask_order: bool,
) -> str:
    title = facts.product.title_ne if locale == "ne" and facts.product.title_ne else facts.product.title
    if variant is not None:
        a = tool_availability(db, conv.merchant_id, [variant.id])[variant.id]
        label = f"{title} ({variant.title})" if variant.title != "Default" else title
        out = t(
            "product",
            locale,
            title=label,
            price=money(variant.price_minor, locale),
            stock=_stock_line(a, locale),
        )
    else:
        prices = sorted({v.price_minor for v in facts.variants})
        price = (
            money(prices[0], locale)
            if len(prices) == 1
            else f"{money(prices[0], locale)}–{money(prices[-1], locale)}"
        )
        av = tool_availability(db, conv.merchant_id, [v.id for v in facts.variants])
        tracked = [a for a in av.values() if a.tracked]
        stock = (
            t("stock_unknown", locale)
            if not tracked
            else (t("out_of_stock", locale) if all(a.available <= 0 for a in tracked) else "")
        )
        out = t("product", locale, title=title, price=price, stock=stock).strip()
        in_stock = [
            "/".join(facts.variant_values.get(v.id, {}).values()) or v.title
            for v in facts.variants
            if not av[v.id].tracked or av[v.id].available > 0
        ]
        if facts.options and in_stock:
            out += " " + t("options", locale, options=", ".join(in_stock[:12]))
    if ask_order:
        out += "\n" + t("want_order", locale)
    return out


# ----------------------------------------------------------------------------- chat-to-order
def _fill(db: Session, conv: Conversation, draft: OrderDraft, e: Extracted, text: str) -> str | None:
    """Put what this message says into the draft. Returns an error template key if the input is bad."""
    f = dict(draft.fields)
    awaiting = draft.awaiting_field
    if "product_id" in f:
        p = db.get(Product, uuid.UUID(f["product_id"]))
        if p is not None and "variant_id" not in f:
            facts = tool_product_facts(db, p)
            v, picked = match_variant(facts, text, f.get("options", {}))
            f["options"] = picked
            if v is not None:
                f["variant_id"] = str(v.id)
    if e.quantity and "quantity" not in f:
        f["quantity"] = e.quantity
    elif awaiting == "quantity" and text.strip().isdigit() and 1 <= int(text.strip()) <= 50:
        f["quantity"] = int(text.strip())
    if e.phone:
        f["phone"] = e.phone
    elif awaiting == "phone":
        draft.fields = f
        return "bad_phone"
    if e.district:
        f["district"] = e.district
    elif awaiting == "district" and (dc := nepal.district_code(text.strip())):
        f["district"] = dc
    if e.ward:
        f["ward"] = e.ward
    elif awaiting == "ward" and text.strip().isdigit() and 1 <= int(text.strip()) <= nepal.MAX_WARD:
        f["ward"] = int(text.strip())
    if awaiting == "municipality":
        name = re.sub(
            r"(?:ward|wada|वडा)\s*(?:no\.?|number|नं\.?)?\s*[-:]?\s*\d{1,2}", " ", text, flags=re.I
        ).strip(" ,.-")
        if 2 <= len(name) <= 120:
            f["municipality"] = name
    if awaiting == "name" and not any(ch.isdigit() for ch in text) and 2 <= len(text.strip()) <= 80:
        f["name"] = text.strip().title() if text.strip().islower() else text.strip()
    if awaiting == "area":
        f["area"] = None if SKIP.match(text) else text.strip()[:160]
        f["area_asked"] = True
    if e.payment:
        f["payment"] = e.payment
    if f != draft.fields:
        draft.fields = f
        draft.version += 1
    return None


def _next_missing(db: Session, conv: Conversation, draft: OrderDraft) -> str | None:
    f = dict(draft.fields)  # JSONB: reassign (not mutate) so the change is saved
    missing = _first_missing(db, conv, f)
    draft.fields = f
    return missing


def _first_missing(db: Session, conv: Conversation, f: dict[str, Any]) -> str | None:
    from app.core.config import get_settings

    for slot in SLOTS:
        if slot == "product" and "product_id" not in f:
            return slot
        if slot == "variant" and "variant_id" not in f:
            return slot
        if slot == "quantity" and "quantity" not in f:
            f["quantity"] = 1  # default; shown in the summary so the customer can change it
        if slot == "name" and not f.get("name"):
            cust = db.get(Customer, conv.customer_id)
            if (
                cust
                and cust.display_name
                and cust.display_name != "Customer"
                and f.get("name_from_profile") is None
            ):
                f["name"], f["name_from_profile"] = cust.display_name, True
            else:
                return slot
        if slot in ("phone", "district", "municipality", "ward") and not f.get(slot):
            return slot
        if slot == "area" and not f.get("area_asked"):
            return slot
        if slot == "payment" and not f.get("payment"):
            if not get_settings().payment_provider:
                f["payment"] = "cod"
            else:
                return slot
    return None


def _ask(db: Session, conv: Conversation, draft: OrderDraft, slot: str, locale: str) -> str:
    if slot == "variant":
        p = db.get(Product, uuid.UUID(draft.fields["product_id"]))
        assert p is not None
        facts = tool_product_facts(db, p)
        chosen = draft.fields.get("options", {})
        av = tool_availability(db, conv.merchant_id, [v.id for v in facts.variants])
        for name, values in facts.options.items():
            if name in chosen:
                continue
            ok = [
                val
                for val in values
                if any(
                    facts.variant_values.get(v.id, {}).get(name) == val
                    and (not av[v.id].tracked or av[v.id].available > 0)
                    for v in facts.variants
                )
            ]
            return t("ask_variant", locale, option=name, values=" / ".join(ok or values))
        return t("ask_variant", locale, option="option", values=" / ".join(v.title for v in facts.variants))
    return t(f"ask_{slot}", locale)


def _continue_draft(
    db: Session, conv: Conversation, msg: Message, draft: OrderDraft, e: Extracted, locale: str
) -> None:
    err = _fill(db, conv, draft, e, msg.text)
    grounding: dict[str, Any] = {"draft": {"id": str(draft.id), "version": draft.version}}
    if err:
        _dispatch(db, conv, msg, t(err, locale), intent="order", confidence=0.9, grounding=grounding)
        return
    missing = _next_missing(db, conv, draft)
    if "variant_id" in draft.fields:
        v = db.get(Variant, uuid.UUID(draft.fields["variant_id"]))
        a = tool_availability(db, conv.merchant_id, [v.id])[v.id] if v else None
        grounding["get_inventory"] = (
            {str(v.id): {"tracked": a.tracked, "available": a.available}} if v and a else {}
        )
        if v and a and a.tracked and a.available < int(draft.fields.get("quantity", 1)):
            p = db.get(Product, v.product_id)
            if a.available <= 0:  # let the customer pick another option
                draft.fields = {k: val for k, val in draft.fields.items() if k != "variant_id"}
            _dispatch(
                db,
                conv,
                msg,
                t("sold_out_now", locale, title=p.title if p else "", n=max(0, a.available)),
                intent="order",
                confidence=0.9,
                grounding=grounding,
            )
            return
    if missing is not None:
        draft.awaiting_field = missing
        _dispatch(
            db,
            conv,
            msg,
            _ask(db, conv, draft, missing, locale),
            intent="order",
            confidence=0.9,
            grounding=grounding,
        )
        return
    draft.awaiting_field, draft.status = None, "awaiting_confirmation"
    _dispatch(
        db,
        conv,
        msg,
        _summary(db, draft, locale),
        intent="order",
        confidence=0.9,
        grounding={**grounding, "get_price": _draft_prices(db, draft)},
    )


def _draft_prices(db: Session, draft: OrderDraft) -> dict[str, int]:
    v = db.get(Variant, uuid.UUID(draft.fields["variant_id"]))
    return {str(v.id): v.price_minor} if v else {}


def _summary(db: Session, draft: OrderDraft, locale: str) -> str:
    f = draft.fields
    v = db.get(Variant, uuid.UUID(f["variant_id"]))
    p = db.get(Product, v.product_id) if v else None
    assert v is not None and p is not None
    qty = int(f.get("quantity", 1))
    title = p.title_ne if locale == "ne" and p.title_ne else p.title
    label = f"{title} ({v.title})" if v.title != "Default" else title
    district = nepal.DISTRICTS.get(f["district"], (f["district"],))[0]
    address = ", ".join(str(x) for x in (f.get("area"), f"{f['municipality']}-{f['ward']}", district) if x)
    from app.domains.fulfillment.couriers import quote_fee

    subtotal = v.price_minor * qty
    quote = quote_fee(db, f["district"], subtotal)
    # The fee shown is the fee charged: remember it on the draft for order creation.
    draft.fields = {**f, "delivery_fee_minor": quote["fee_minor"] if quote else None}
    if quote is not None:
        fee = t("free_delivery", locale) if quote["fee_minor"] == 0 else money(quote["fee_minor"], locale)
        return t(
            "summary_fee",
            locale,
            lines=f"{qty} × {label} @ {money(v.price_minor, locale)}",
            fee=fee,
            total=money(subtotal + quote["fee_minor"], locale),
            name=f["name"],
            phone=f["phone"],
            address=address,
            payment=t(f.get("payment", "cod"), locale),
        )
    return t(
        "summary",
        locale,
        lines=f"{qty} × {label} @ {money(v.price_minor, locale)}",
        total=money(v.price_minor * qty, locale),
        name=f["name"],
        phone=f["phone"],
        address=address,
        payment=t(f.get("payment", "cod"), locale),
    )


def _create_order(db: Session, conv: Conversation, msg: Message, draft: OrderDraft, locale: str) -> None:
    f = draft.fields
    ctx = TenantContext(merchant_id=conv.merchant_id, actor=Actor(type="ai", display="Sales Agent"))
    data = orders.OrderInput(
        lines=[orders.LineInput(uuid.UUID(f["variant_id"]), int(f.get("quantity", 1)))],
        customer_id=conv.customer_id,
        address=customers.AddressInput(
            recipient_name=f["name"],
            phone=f["phone"],
            province="",
            district=f["district"],
            municipality=f["municipality"],
            ward=int(f["ward"]),
            area=f.get("area"),
        ),
        payment_method=f.get("payment", "cod"),
        delivery_fee_minor=int(f.get("delivery_fee_minor") or 0),
        source="chat",
        source_key=f"chat:{conv.id}:{draft.version}",
        conversation_id=conv.id,
        confirm=True,
    )
    try:
        with db.begin_nested():
            o = orders.create_order(db, ctx, data)
    except inventory.OutOfStock as ex:
        draft.status = "collecting"
        draft.fields = {k: v for k, v in f.items() if k != "variant_id"}
        p = db.get(Product, uuid.UUID(f["product_id"]))
        _dispatch(
            db,
            conv,
            msg,
            t("sold_out_now", locale, title=p.title if p else "", n=ex.details.get("available", 0)),
            intent="order",
            confidence=0.9,
            grounding={"get_inventory": ex.details},
        )
        return
    except AppError as ex:  # e.g. the address didn't validate: hand to the seller rather than loop
        log.warning("chat_order_failed", conversation_id=str(conv.id), code=ex.code)
        _escalate(db, conv, msg, "order_failed", locale)
        return
    draft.status, draft.order_id = "confirmed", o.id
    text = t("confirmed", locale, number=o.number, total=money(o.total_minor, locale))
    if o.payment_method == "prepaid":
        from app.domains.payments import service as payments

        try:
            with db.begin_nested():
                pay = payments.start_online_payment(db, ctx, o.id, None)
            text += "\n" + t("pay_link", locale, url=pay.redirect_url)
        except AppError:
            text += "\n" + t("pay_later", locale)
    _dispatch(
        db,
        conv,
        msg,
        text,
        intent="order",
        confidence=0.95,
        grounding={"create_order": {"order_id": str(o.id), "number": o.number, "total_minor": o.total_minor}},
    )


# ----------------------------------------------------------------------------- summary (CRM-010)
def summarize(db: Session, conv: Conversation) -> str:
    """Factual summary from the conversation's own data; an AI model rephrases it when configured.

    The facts (intent, draft, latest order) are computed here; the model only shortens the transcript,
    and its output is not used when only the development sandbox model is available."""
    from app.core.db import utcnow

    msgs = list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conv.id, Message.status.in_(("received", "sent")))
            .order_by(Message.id.desc())
            .limit(30)
        )
    )[::-1]
    cust = db.get(Customer, conv.customer_id)
    draft = db.scalar(
        select(OrderDraft)
        .where(OrderDraft.conversation_id == conv.id)
        .order_by(OrderDraft.created_at.desc())
        .limit(1)
    )
    o = tool_latest_order(db, conv.customer_id)
    facts = [
        f"Customer: {cust.display_name if cust else 'unknown'}{' (' + cust.phone + ')' if cust and cust.phone else ''}."
    ]
    if conv.last_intent:
        facts.append(f"Latest intent: {conv.last_intent.replace('_', ' ')}.")
    if draft:
        facts.append(
            f"Order request: {draft.status.replace('_', ' ')}"
            + (f", waiting for {draft.awaiting_field}." if draft.awaiting_field else ".")
        )
    if o:
        facts.append(
            f"Latest order #{o.number}: {o.status.replace('_', ' ')}, total {money(o.total_minor, 'en')}."
        )
    if conv.escalated:
        facts.append(f"Needs a person: {(conv.escalation_reason or '').replace('_', ' ')}.")
    summary = " ".join(facts)
    transcript = "\n".join(f"{'Customer' if m.direction == 'in' else 'Shop'}: {m.text}" for m in msgs)
    try:
        from app.domains.ai.gateway import gateway
        from app.domains.ai.types import AIRequest
        from app.domains.ai.types import Message as AIMessage

        res = gateway.run(
            task="SUMMARIZATION",
            request=AIRequest(
                messages=(AIMessage(role="user", text=transcript[-6000:]),),
                system="Summarise this shop chat in 2 sentences for the seller. Do not add prices, stock or dates that aren't in the chat.",
                max_tokens=200,
                prompt_name="inbox_summary",
                prompt_version=1,
            ),
            merchant_id=conv.merchant_id,
            idempotency_key=f"summary:{conv.id}:{msgs[-1].id if msgs else 0}",
        )
        if res.provider != "sandbox" and res.text:
            summary = f"{res.text.strip()} {summary}"
    except Exception as e:
        log.info("ai_summary_unavailable", reason=type(e).__name__)
    conv.ai_summary, conv.ai_summary_at = summary[:2000], utcnow()
    return conv.ai_summary
