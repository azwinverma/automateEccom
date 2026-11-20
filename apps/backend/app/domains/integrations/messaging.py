"""Customer messaging channels a seller connects with their own credentials (no Nivaro app review):

- Telegram: a bot the seller makes with @BotFather. Webhook carries our per-connection secret in
  `X-Telegram-Bot-Api-Secret-Token` (set via setWebhook); private chats only.
- WhatsApp Business Cloud API, the seller's own Meta app: permanent access token, phone number id,
  app secret. Inbound POSTs are signed `X-Hub-Signature-256: sha256=HMAC(app_secret, body)`; the
  callback URL is verified once with our per-connection verify token. Free-form replies are only
  allowed within 24 hours of the customer's last message (Meta's customer-service window).

Credentials arrive sealed (channels.service) and are opened only for the call.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, ClassVar

import httpx

from app.domains.integrations.base import (
    ChannelAdapter,
    ChannelCapability,
    ExternalMessage,
    IntegrationError,
    NormalizedWebhook,
)
from app.domains.integrations.http import ResilientClient

transport_override: httpx.BaseTransport | None = None  # tests: httpx.MockTransport


class _KeyedMessagingChannel(ChannelAdapter):
    auth_kind = "api_keys"
    caption_style = "facebook"
    capabilities = frozenset({ChannelCapability.MESSAGES})
    credential_fields: ClassVar[tuple[str, ...]] = ()  # secret, sealed
    optional_fields: ClassVar[tuple[str, ...]] = ()
    needs_manual_webhook: ClassVar[bool] = False  # seller pastes callback URL + verify token in their app

    def _cred(self, key: str) -> str:
        v = self._credentials.get(key)
        if not v:
            raise IntegrationError("missing_credentials", self.code, auth=True)
        return v

    def _raise_for(self, r: httpx.Response, op: str) -> Any:
        if r.status_code in (401, 403):
            raise IntegrationError("invalid_credentials", f"{self.code} {op}", auth=True)
        if r.status_code == 429 or r.status_code >= 500:
            raise IntegrationError("provider_unavailable", f"{self.code} {op}", retryable=True)
        data = r.json() if r.content else {}
        if r.status_code >= 400:
            raise IntegrationError(self._error_code(data), f"{self.code} {op}")
        return data

    def _error_code(self, data: dict[str, Any]) -> str:
        return "provider_rejected"

    def account(self) -> tuple[str, str]:
        """(external account id, display name) for the connection, proving the credentials work."""
        raise NotImplementedError


# ----------------------------------------------------------------------------- Telegram
class TelegramAdapter(_KeyedMessagingChannel):
    code = "telegram"
    display_name = "Telegram"
    credential_fields = ("bot_token",)

    def _client(self) -> ResilientClient:
        return ResilientClient(
            "telegram",
            base_url=f"https://api.telegram.org/bot{self._cred('bot_token')}/",
            transport=transport_override,
        )

    def _call(self, method: str, op: str, **payload: Any) -> Any:
        r = self._client().request("POST", method, operation=op, json=payload, retry_unsafe=op != "send")
        if r.status_code == 404:  # Telegram answers 404 for an unknown bot token
            raise IntegrationError("invalid_credentials", "telegram", auth=True)
        data = self._raise_for(r, op)
        if not data.get("ok"):
            raise IntegrationError("provider_rejected", "telegram")
        return data["result"]

    def account(self) -> tuple[str, str]:
        me = self._call("getMe", "health")
        return str(me["id"]), f"Telegram @{me.get('username') or me['id']}"

    def health_check(self) -> bool:
        self.account()
        return True

    def register_webhooks(self, delivery_url: str, secret: str) -> list[str]:
        self._call(
            "setWebhook",
            "webhook_register",
            url=delivery_url,
            secret_token=secret,
            allowed_updates=["message"],
            drop_pending_updates=False,
        )
        return []

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        secret = self._credentials.get("webhook_secret", "")
        got = {k.lower(): v for k, v in headers.items()}.get("x-telegram-bot-api-secret-token", "")
        return bool(secret) and hmac.compare_digest(secret, got)

    def parse_webhook(self, headers: dict[str, str], body: bytes) -> list[NormalizedWebhook]:
        doc = json.loads(body)
        msg = doc.get("message") or {}
        chat = msg.get("chat") or {}
        if not msg or chat.get("type") != "private" or not msg.get("text"):
            return []  # groups, channels, stickers, edits: not customer text for the inbox
        sender = msg.get("from") or {}
        name = " ".join(x for x in (sender.get("first_name"), sender.get("last_name")) if x) or sender.get(
            "username"
        )
        bot = self._credentials.get("bot_id", "")
        return [
            NormalizedWebhook(
                provider=self.code,
                external_event_id=f"tg:{bot}:{doc['update_id']}",
                event_type="message.received",
                occurred_at=None,
                payload={
                    "thread_id": str(chat["id"]),
                    "message_id": str(msg["message_id"]),
                    "sender": {"id": str(sender.get("id") or chat["id"]), "name": name},
                    "text": str(msg["text"]),
                },
            )
        ]

    def normalize_message(self, raw: dict[str, Any]) -> ExternalMessage | None:
        text = str(raw.get("text") or "").strip()
        if not text:
            return None
        sender = raw.get("sender") or {}
        return ExternalMessage(
            thread_id=str(raw["thread_id"]),
            message_id=str(raw["message_id"]),
            sender_id=str(sender.get("id") or raw["thread_id"]),
            sender_name=sender.get("name"),
            text=text[:4000],
        )

    def send_message(self, conversation_external_id: str, text: str, idempotency_key: str) -> str:
        res = self._call("sendMessage", "send", chat_id=conversation_external_id, text=text[:4096])
        return str(res["message_id"])


# ----------------------------------------------------------------------------- WhatsApp Cloud
class WhatsAppCloudAdapter(_KeyedMessagingChannel):
    code = "whatsapp_cloud"
    display_name = "WhatsApp Business"
    credential_fields = ("access_token", "app_secret")
    optional_fields = ("phone_number_id", "business_account_id")
    needs_manual_webhook = True
    GRAPH = "https://graph.facebook.com/v21.0/"

    def _client(self) -> ResilientClient:
        return ResilientClient("whatsapp_cloud", base_url=self.GRAPH, transport=transport_override)

    def _h(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._cred('access_token')}"}

    def _error_code(self, data: dict[str, Any]) -> str:
        code = (data.get("error") or {}).get("code")
        if code == 131047:  # more than 24 hours since the customer's last message
            return "outside_reply_window"
        if code in (190, 10, 200):
            return "invalid_credentials"
        return "provider_rejected"

    def _phone_id(self) -> str:
        return self._credentials.get("phone_number_id") or str(self.config.get("external_account_id") or "")

    def account(self) -> tuple[str, str]:
        pid = self._phone_id()
        if not pid:
            raise IntegrationError("missing_credentials", self.code, auth=True)
        r = self._client().request(
            "GET",
            pid,
            operation="health",
            headers=self._h(),
            params={"fields": "display_phone_number,verified_name"},
        )
        data = self._raise_for(r, "health")
        name = data.get("verified_name") or "WhatsApp"
        return pid, f"WhatsApp {data.get('display_phone_number') or ''} ({name})".replace("  ", " ")

    def health_check(self) -> bool:
        self.account()
        return True

    def register_webhooks(self, delivery_url: str, secret: str) -> list[str]:
        """The seller pastes the callback URL and verify token into their Meta app. If they gave us the
        business account id, also subscribe the app to it so messages flow."""
        waba = self._credentials.get("business_account_id")
        if waba:
            r = self._client().request(
                "POST", f"{waba}/subscribed_apps", operation="webhook_register", headers=self._h()
            )
            self._raise_for(r, "subscribe")
        return []

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        app_secret = self._credentials.get("app_secret", "")
        got = {k.lower(): v for k, v in headers.items()}.get("x-hub-signature-256", "")
        want = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
        return bool(app_secret) and hmac.compare_digest(want, got)

    def parse_webhook(self, headers: dict[str, str], body: bytes) -> list[NormalizedWebhook]:
        doc = json.loads(body)
        out: list[NormalizedWebhook] = []
        for entry in doc.get("entry") or []:
            for change in entry.get("changes") or []:
                if change.get("field") != "messages":
                    continue
                value = change.get("value") or {}
                names = {
                    c.get("wa_id"): (c.get("profile") or {}).get("name") for c in value.get("contacts") or []
                }
                for m in value.get("messages") or []:
                    if m.get("type") != "text":
                        continue  # media, reactions, locations: shown later; text goes to the agent
                    out.append(
                        NormalizedWebhook(
                            provider=self.code,
                            external_event_id=f"wa:{m['id']}",
                            event_type="message.received",
                            occurred_at=None,
                            payload={
                                "thread_id": str(m["from"]),
                                "message_id": str(m["id"]),
                                "sender": {"id": str(m["from"]), "name": names.get(m["from"])},
                                "text": str((m.get("text") or {}).get("body") or ""),
                            },
                        )
                    )
        return out

    normalize_message = TelegramAdapter.normalize_message

    def send_message(self, conversation_external_id: str, text: str, idempotency_key: str) -> str:
        r = self._client().request(
            "POST",
            f"{self._phone_id()}/messages",
            operation="send",
            headers=self._h(),
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": conversation_external_id,
                "type": "text",
                "text": {"preview_url": False, "body": text[:4096]},
            },
        )
        data = self._raise_for(r, "send")
        return str((data.get("messages") or [{}])[0].get("id", ""))
