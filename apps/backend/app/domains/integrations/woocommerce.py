"""WooCommerce channel adapter (CHN-009) — WooCommerce REST API v3 (``/wp-json/wc/v3``).

Auth: per-store REST API keys (consumer key/secret) over HTTPS basic auth. No platform app review is
needed, which makes this the first real channel. Status: implemented against the documented v3 API
and contract-tested with mocked HTTP; NOT yet exercised against a live store (docs/KNOWN_GAPS.md).

Products with options become ``variable`` products with one variation per variant (matched by SKU on
updates, so re-publishing updates in place). Prices are sent as decimal strings in the store currency.
Images are passed as short-lived signed URLs that WooCommerce downloads into its media library.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, ClassVar
from urllib.parse import urlparse

import httpx

from app.domains.integrations.base import (
    ChannelAdapter,
    ChannelCapability,
    IntegrationError,
    NormalizedWebhook,
)
from app.domains.integrations.http import ResilientClient


def _money(minor: int | None) -> str:
    return "" if minor is None else str((Decimal(minor) / 100).quantize(Decimal("0.01")))


def validate_store_url(url: str) -> str:
    u = urlparse(url.strip())
    if u.scheme != "https" or not u.netloc:
        raise IntegrationError("invalid_store_url", "WooCommerce store URL must be https://")
    if u.hostname in ("localhost", "127.0.0.1") or (u.hostname or "").endswith(".local"):
        raise IntegrationError("invalid_store_url", "store URL must be publicly reachable")
    return f"https://{u.netloc}{u.path.rstrip('/')}"


class WooCommerceAdapter(ChannelAdapter):
    code = "woocommerce"
    display_name = "WooCommerce"
    capabilities = frozenset(
        {ChannelCapability.PRODUCT_LISTING, ChannelCapability.INVENTORY_SYNC, ChannelCapability.ORDERS}
    )
    caption_style: ClassVar[str] = "marketplace"
    auth_kind: ClassVar[str] = "api_keys"

    def __init__(
        self,
        credentials: dict[str, str] | None = None,
        config: dict[str, Any] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(credentials, config)
        self._transport = transport

    # ------------------------------------------------------------------ http
    def _client(self) -> ResilientClient:
        store = self.config.get("store_url") or self._credentials.get("store_url")
        key, secret = self._credentials.get("consumer_key"), self._credentials.get("consumer_secret")
        if not (store and key and secret):
            raise IntegrationError("not_configured", "WooCommerce credentials missing", auth=True)
        client = ResilientClient(
            "woocommerce", base_url=f"{store}/wp-json/wc/v3", timeout_s=20, transport=self._transport
        )
        client._client.auth = httpx.BasicAuth(key, secret)
        return client

    def _call(self, method: str, path: str, operation: str, **kw: Any) -> Any:
        client = self._client()
        try:
            resp = client.request(method, path, operation=operation, retry_unsafe=method in ("PUT",), **kw)
        finally:
            client.close()
        if resp.status_code in (401, 403):
            raise IntegrationError(
                "auth_failed", f"WooCommerce rejected the API keys ({resp.status_code})", auth=True
            )
        if resp.status_code == 429 or resp.status_code >= 500:
            raise IntegrationError(f"http_{resp.status_code}", "WooCommerce unavailable", retryable=True)
        if resp.status_code == 404:
            raise IntegrationError("not_found", path)
        if resp.status_code >= 400:
            code = "bad_request"
            with contextlib.suppress(ValueError):
                code = str(resp.json().get("code") or code)[:60]
            raise IntegrationError(code, f"WooCommerce {resp.status_code}")
        return resp.json() if resp.content else None

    # ------------------------------------------------------------------ connection
    def health_check(self) -> bool:
        self._call("GET", "/products", "health", params={"per_page": 1})
        return True

    def store_currency(self) -> str | None:
        data = self._call("GET", "/settings/general/woocommerce_currency", "settings")
        return (data or {}).get("value")

    # ------------------------------------------------------------------ listings
    def _product_body(self, listing: dict[str, Any]) -> dict[str, Any]:
        variants = listing["variants"]
        variable = bool(listing.get("options")) and len(variants) > 0 and any(v["options"] for v in variants)
        body: dict[str, Any] = {
            "name": listing["title"],
            "type": "variable" if variable else "simple",
            "status": "publish",
            "description": listing.get("description") or "",
            "short_description": listing.get("description_ne") or "",
            "tags": [{"name": t} for t in listing.get("tags", [])],
            "images": [{"src": url} for url in listing.get("image_urls", [])],
        }
        if variable:
            body["attributes"] = [
                {"name": o["name"], "options": o["values"], "variation": True, "visible": True}
                for o in listing["options"]
            ]
        else:
            v = variants[0]
            body.update(
                {
                    "sku": v["sku"] or "",
                    "regular_price": _money(v.get("compare_at_minor") or v["price_minor"]),
                    "sale_price": _money(v["price_minor"]) if v.get("compare_at_minor") else "",
                    "weight": str(v["weight_grams"] / 1000) if v.get("weight_grams") else "",
                }
            )
        return body

    def _variation_body(self, v: dict[str, Any]) -> dict[str, Any]:
        return {
            "sku": v["sku"] or "",
            "regular_price": _money(v.get("compare_at_minor") or v["price_minor"]),
            "sale_price": _money(v["price_minor"]) if v.get("compare_at_minor") else "",
            "attributes": [{"name": k, "option": val} for k, val in v["options"].items()],
            "weight": str(v["weight_grams"] / 1000) if v.get("weight_grams") else "",
        }

    def publish_listing(
        self, listing: dict[str, Any], idempotency_key: str, external_id: str | None = None
    ) -> str:
        body = self._product_body(listing)
        if external_id:
            product = self._call("PUT", f"/products/{external_id}", "product_update", json=body)
        else:
            product = self._call("POST", "/products", "product_create", json=body)
        pid = str(product["id"])
        if body["type"] == "variable":
            existing = self._call(
                "GET", f"/products/{pid}/variations", "variations_list", params={"per_page": 100}
            )
            by_sku = {v.get("sku"): v["id"] for v in existing or [] if v.get("sku")}
            create, update = [], []
            for v in listing["variants"]:
                vb = self._variation_body(v)
                if v["sku"] in by_sku:
                    update.append({"id": by_sku[v["sku"]], **vb})
                else:
                    create.append(vb)
            wanted = {v["sku"] for v in listing["variants"]}
            delete = [vid for sku, vid in by_sku.items() if sku not in wanted]
            if create or update or delete:
                result = self._call(
                    "POST",
                    f"/products/{pid}/variations/batch",
                    "variations_batch",
                    json={"create": create, "update": update, "delete": delete},
                )
                errors = [
                    item.get("error")
                    for kind in ("create", "update")
                    for item in (result or {}).get(kind, [])
                    if isinstance(item, dict) and item.get("error")
                ]
                if errors:
                    raise IntegrationError("variation_rejected", json.dumps(errors[0])[:200])
        return pid

    def unpublish_listing(self, external_id: str, idempotency_key: str) -> None:
        # Draft (not delete): the seller's store keeps the product and its history.
        try:
            self._call("PUT", f"/products/{external_id}", "product_unpublish", json={"status": "draft"})
        except IntegrationError as e:
            if e.code != "not_found":
                raise

    def update_inventory(self, external_sku: str, available: int, idempotency_key: str) -> None:
        found = self._call("GET", "/products", "find_sku", params={"sku": external_sku})
        if not found:
            raise IntegrationError("sku_not_found", external_sku)
        item = found[0]
        path = (
            f"/products/{item['parent_id']}/variations/{item['id']}"
            if item.get("parent_id")
            else f"/products/{item['id']}"
        )
        self._call(
            "PUT", path, "stock_update", json={"manage_stock": True, "stock_quantity": max(0, available)}
        )

    def fetch_orders(self, since: datetime) -> list[dict[str, Any]]:
        return (
            self._call(
                "GET",
                "/orders",
                "orders_list",
                params={"after": since.astimezone(UTC).isoformat(), "per_page": 100},
            )
            or []
        )

    # ------------------------------------------------------------------ webhooks
    TOPICS: ClassVar[tuple[str, ...]] = ("order.created", "order.updated", "product.deleted")

    def register_webhooks(self, delivery_url: str, secret: str) -> list[str]:
        """Create one webhook per topic; returns the store's webhook ids (stored for later cleanup)."""
        ids = []
        for topic in self.TOPICS:
            hook = self._call(
                "POST",
                "/webhooks",
                "webhook_register",
                json={
                    "name": f"Nivaro: {topic}",  # display only; webhooks are tracked by id
                    "topic": topic,
                    "delivery_url": delivery_url,
                    "secret": secret,
                    "status": "active",
                },
            )
            ids.append(str(hook["id"]))
        return ids

    def delete_webhooks(self, ids: list[str]) -> None:
        for wid in ids:
            try:
                self._call("DELETE", f"/webhooks/{wid}", "webhook_delete", params={"force": "true"})
            except IntegrationError as e:
                if e.code != "not_found":
                    raise

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        secret = self._credentials.get("webhook_secret", "")
        sig = {k.lower(): v for k, v in headers.items()}.get("x-wc-webhook-signature", "")
        expected = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
        return bool(secret) and hmac.compare_digest(expected, sig)

    def parse_webhook(self, headers: dict[str, str], body: bytes) -> list[NormalizedWebhook]:
        h = {k.lower(): v for k, v in headers.items()}
        doc = json.loads(body)
        source = h.get("x-wc-webhook-source", "").rstrip("/")
        return [
            NormalizedWebhook(
                provider=self.code,
                external_event_id=(
                    f"{h.get('x-wc-webhook-id', '0')}:{h.get('x-wc-webhook-delivery-id') or doc.get('id')}"
                ),
                event_type=h.get("x-wc-webhook-topic", "unknown"),  # e.g. order.created
                occurred_at=None,
                payload=doc,
                external_account_id=source or None,
            )
        ]
