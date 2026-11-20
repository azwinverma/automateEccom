"""Facebook Page and Instagram publishing through the seller's own Meta app (Graph API).

A Meta app in development mode may publish to Pages and Instagram professional accounts that the
app's own admins manage, so a seller connects without Nivaro going through App Review: they paste a
long-lived Page access token and the Page id (the linked Instagram account is found from the Page).
Once Nivaro's own app passes review, the same adapters work with OAuth tokens.

Media must be reachable by Meta over the internet: posts send short-lived signed URLs of the
4:5 feed / 9:16 story renditions (or the reel's MP4). A local development server isn't reachable.
Meta has no idempotency keys, so publishing POSTs are never retried blindly.
"""

from __future__ import annotations

import time
from typing import Any, ClassVar

import httpx

from app.domains.integrations.base import ChannelAdapter, ChannelCapability, IntegrationError
from app.domains.integrations.http import ResilientClient

GRAPH = "https://graph.facebook.com/v21.0/"
transport_override: httpx.BaseTransport | None = None  # tests: httpx.MockTransport
sleep = time.sleep  # tests: no real waiting while a reel processes


def _caption(content: dict[str, Any], limit: int) -> str:
    tags = " ".join(f"#{t}" for t in content.get("hashtags") or [])
    text = (content.get("caption") or "").strip()
    return (f"{text}\n\n{tags}" if tags else text)[:limit]


class _MetaPublisher(ChannelAdapter):
    """Publishing works with any Page token. Messages (Messenger / Instagram DM) need Nivaro's Meta
    app: connections made with a pasted token are stored with content_publish only."""

    auth_kind = "api_keys"
    capabilities = frozenset({ChannelCapability.CONTENT_PUBLISH, ChannelCapability.MESSAGES})
    credential_fields: ClassVar[tuple[str, ...]] = ("page_access_token", "page_id")
    optional_fields: ClassVar[tuple[str, ...]] = ()
    needs_manual_webhook = False

    def _client(self) -> ResilientClient:
        return ResilientClient(self.code, base_url=GRAPH, transport=transport_override, timeout_s=60)

    def _token(self) -> str:
        t = self._credentials.get("page_access_token")
        if not t:
            raise IntegrationError("missing_credentials", self.code, auth=True)
        return t

    def _call(self, method: str, path: str, op: str, **kw: Any) -> dict[str, Any]:
        params = {**kw.pop("params", {}), "access_token": self._token()}
        r = self._client().request(method, path, operation=op, params=params, **kw)
        data = r.json() if r.content else {}
        if r.status_code < 400 and "error" not in data:
            return data
        err = data.get("error") or {}
        code, sub = err.get("code"), err.get("error_subcode")
        if code == 190 or r.status_code == 401:
            raise IntegrationError("invalid_credentials", f"{self.code} {op}", auth=True)
        if code in (10, 200, 3) or (isinstance(code, int) and 200 <= code < 300):
            raise IntegrationError("permission_missing", f"{self.code} {op}", auth=True)
        if code in (4, 17, 32, 613) or r.status_code >= 500 or r.status_code == 429:
            raise IntegrationError("provider_unavailable", f"{self.code} {op}", retryable=True)
        if code in (9004, 36001, 324) or sub in (2207052, 2207003, 2207026):
            raise IntegrationError("media_unreachable", f"{self.code} {op}")
        raise IntegrationError("provider_rejected", f"{self.code} {op}")

    def register_webhooks(self, delivery_url: str, secret: str) -> list[str]:
        return []  # DMs arrive on Nivaro's app-level webhook (/webhooks/meta), not per connection

    def send_message(self, conversation_external_id: str, text: str, idempotency_key: str) -> str:
        return _send_dm(self, conversation_external_id, text)

    def normalize_message(self, raw: dict[str, Any]) -> Any:
        from app.domains.integrations.base import ExternalMessage

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

    def verify_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        return False

    def health_check(self) -> bool:
        self.account()
        return True

    def account(self) -> tuple[str, str]:
        raise NotImplementedError

    def page_info(self) -> dict[str, Any]:
        pid = self._credentials.get("page_id") or ""
        if not pid.isdigit():
            raise IntegrationError("missing_credentials", self.code, auth=True)
        return self._call(
            "GET", pid, "health", params={"fields": "id,name,instagram_business_account{id,username}"}
        )

    @staticmethod
    def _media(content: dict[str, Any]) -> list[dict[str, str]]:
        media = [m for m in content.get("media") or [] if m.get("url")]
        if not media and content.get("asset_ids"):
            raise IntegrationError("media_unavailable", "meta")  # assets exist but have no rendition yet
        return media


class FacebookPageAdapter(_MetaPublisher):
    code = "facebook_page"
    display_name = "Facebook Page"
    caption_style = "facebook"
    max_caption_chars = 5000

    def account(self) -> tuple[str, str]:
        info = self.page_info()
        return str(info["id"]), f"Facebook · {info.get('name') or info['id']}"

    def publish_content(self, content: dict[str, Any], idempotency_key: str) -> str:
        self._require(ChannelCapability.CONTENT_PUBLISH)
        page, kind = self._credentials["page_id"], content.get("kind") or "post"
        message = _caption(content, self.max_caption_chars)
        media = self._media(content)
        videos = [m for m in media if m["type"] == "video"]
        images = [m for m in media if m["type"] == "image"]
        if kind == "reel" or videos:
            if not videos:
                raise IntegrationError("media_required", "reel needs a video")
            res = self._call(
                "POST",
                f"{page}/videos",
                "publish",
                data={"file_url": videos[0]["url"], "description": message},
            )
            return str(res["id"])
        if kind == "story":
            if not images:
                raise IntegrationError("media_required", "story needs a photo")
            photo = self._call(
                "POST", f"{page}/photos", "upload", data={"url": images[0]["url"], "published": "false"}
            )
            res = self._call("POST", f"{page}/photo_stories", "publish", data={"photo_id": photo["id"]})
            return str(res.get("post_id") or res.get("id"))
        if len(images) == 1:
            res = self._call(
                "POST", f"{page}/photos", "publish", data={"url": images[0]["url"], "caption": message}
            )
            return str(res.get("post_id") or res["id"])
        if images:
            ids = [
                self._call("POST", f"{page}/photos", "upload", data={"url": m["url"], "published": "false"})[
                    "id"
                ]
                for m in images[:10]
            ]
            data: dict[str, Any] = {"message": message}
            for i, fbid in enumerate(ids):
                data[f"attached_media[{i}]"] = f'{{"media_fbid":"{fbid}"}}'
            return str(self._call("POST", f"{page}/feed", "publish", data=data)["id"])
        return str(self._call("POST", f"{page}/feed", "publish", data={"message": message})["id"])


class InstagramAdapter(_MetaPublisher):
    """Instagram professional account linked to the Page (Instagram Graph API content publishing)."""

    code = "instagram"
    display_name = "Instagram"
    caption_style = "instagram"
    max_caption_chars = 2200
    credential_fields = ("page_access_token", "page_id")
    POLLS = 20

    def _ig(self) -> str:
        ig = self._credentials.get("ig_user_id")
        if not ig:
            raise IntegrationError("instagram_not_linked", self.code, auth=True)
        return ig

    def account(self) -> tuple[str, str]:
        info = self.page_info()
        ig = info.get("instagram_business_account") or {}
        if not ig.get("id"):
            raise IntegrationError("instagram_not_linked", self.code)
        self._credentials["ig_user_id"] = str(ig["id"])
        return str(ig["id"]), f"Instagram @{ig.get('username') or ig['id']}"

    def _container(self, op: str, **data: str) -> str:
        return str(self._call("POST", f"{self._ig()}/media", op, data=data)["id"])

    def _wait(self, container: str) -> None:
        for _ in range(self.POLLS):
            st = self._call("GET", container, "status", params={"fields": "status_code"}).get("status_code")
            if st == "FINISHED":
                return
            if st in ("ERROR", "EXPIRED"):
                raise IntegrationError("media_rejected", "instagram processing failed")
            sleep(3)
        raise IntegrationError("media_processing", "instagram still processing", retryable=True)

    def publish_content(self, content: dict[str, Any], idempotency_key: str) -> str:
        self._require(ChannelCapability.CONTENT_PUBLISH)
        kind = content.get("kind") or "post"
        caption = _caption(content, self.max_caption_chars)
        media = self._media(content)
        if not media:
            raise IntegrationError("media_required", "Instagram posts need a photo or video")
        first = media[0]
        if kind == "story":
            key = "video_url" if first["type"] == "video" else "image_url"
            cid = self._container("container", media_type="STORIES", **{key: first["url"]})
            self._wait(cid)
        elif kind == "reel" or first["type"] == "video":
            video = next((m for m in media if m["type"] == "video"), None)
            if video is None:
                raise IntegrationError("media_required", "reel needs a video")
            cid = self._container("container", media_type="REELS", video_url=video["url"], caption=caption)
            self._wait(cid)
        elif len(media) == 1:
            cid = self._container("container", image_url=first["url"], caption=caption)
        else:
            children = [
                self._container("container", image_url=m["url"], is_carousel_item="true")
                for m in media[:10]
                if m["type"] == "image"
            ]
            cid = self._container(
                "container", media_type="CAROUSEL", children=",".join(children), caption=caption
            )
            self._wait(cid)
        return str(
            self._call("POST", f"{self._ig()}/media_publish", "publish", data={"creation_id": cid})["id"]
        )


# ------------------------------------------------ Nivaro's Meta app: one-click connect + DMs
OAUTH_SCOPES = (
    "pages_show_list",
    "pages_manage_metadata",
    "pages_read_engagement",
    "pages_manage_posts",
    "pages_messaging",
    "business_management",
    "instagram_basic",
    "instagram_content_publish",
    "instagram_manage_messages",
)


def app_configured() -> bool:
    from app.core.config import get_settings

    s = get_settings()
    return bool(s.meta_app_id and s.meta_app_secret and s.meta_verify_token)


def _app() -> tuple[str, str]:
    from app.core.config import get_settings

    s = get_settings()
    if not (s.meta_app_id and s.meta_app_secret):
        raise IntegrationError("meta_app_not_configured", "meta")
    return s.meta_app_id, s.meta_app_secret.get_secret_value()


def authorize_url(state: str, redirect_uri: str) -> str:
    from urllib.parse import urlencode

    app_id, _ = _app()
    q = urlencode(
        {
            "client_id": app_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": ",".join(OAUTH_SCOPES),
            "response_type": "code",
        }
    )
    return f"https://www.facebook.com/v21.0/dialog/oauth?{q}"


def _graph(method: str, path: str, op: str, **kw: Any) -> dict[str, Any]:
    r = ResilientClient("meta", base_url=GRAPH, transport=transport_override, timeout_s=30).request(
        method, path, operation=op, **kw
    )
    data = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in data:
        code = (data.get("error") or {}).get("code")
        if code == 190 or r.status_code == 401:
            raise IntegrationError("invalid_credentials", f"meta {op}", auth=True)
        if r.status_code >= 500 or code in (4, 17, 32, 613):
            raise IntegrationError("provider_unavailable", f"meta {op}", retryable=True)
        raise IntegrationError("provider_rejected", f"meta {op}")
    return data


def exchange_code(code: str, redirect_uri: str) -> str:
    """Code → long-lived user token (60 days); Page tokens derived from it don't expire."""
    app_id, secret = _app()
    short = _graph(
        "GET",
        "oauth/access_token",
        "oauth_exchange",
        params={"client_id": app_id, "client_secret": secret, "redirect_uri": redirect_uri, "code": code},
    )
    long = _graph(
        "GET",
        "oauth/access_token",
        "oauth_extend",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": secret,
            "fb_exchange_token": short["access_token"],
        },
    )
    return str(long["access_token"])


def list_pages(user_token: str) -> list[dict[str, Any]]:
    data = _graph(
        "GET",
        "me/accounts",
        "pages",
        params={
            "access_token": user_token,
            "fields": "id,name,access_token,instagram_business_account{id,username}",
            "limit": 50,
        },
    )
    return list(data.get("data") or [])


def subscribe_page(page_id: str, page_token: str) -> None:
    _graph(
        "POST",
        f"{page_id}/subscribed_apps",
        "webhook_register",
        params={"access_token": page_token},
        data={"subscribed_fields": "messages,messaging_postbacks"},
    )


def verify_app_signature(headers: dict[str, str], body: bytes) -> bool:
    import hashlib
    import hmac

    try:
        _, secret = _app()
    except IntegrationError:
        return False
    got = {k.lower(): v for k, v in headers.items()}.get("x-hub-signature-256", "")
    want = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(want, got)


def parse_app_webhook(body: bytes) -> tuple[str, list[Any]]:
    """Meta's app-level webhook → (provider, [NormalizedWebhook]). Echoes and non-text are dropped."""
    import json

    from app.domains.integrations.base import NormalizedWebhook

    doc = json.loads(body)
    provider = {"page": "facebook_page", "instagram": "instagram"}.get(doc.get("object", ""), "")
    out = []
    for entry in doc.get("entry") or []:
        account = str(entry.get("id", ""))
        for ev in entry.get("messaging") or []:
            msg = ev.get("message") or {}
            if not msg or msg.get("is_echo") or not msg.get("text") or not msg.get("mid"):
                continue
            sender = str((ev.get("sender") or {}).get("id", ""))
            out.append(
                NormalizedWebhook(
                    provider=provider,
                    external_event_id=f"meta:{msg['mid']}",
                    event_type="message.received",
                    occurred_at=None,
                    payload={
                        "thread_id": sender,
                        "message_id": str(msg["mid"]),
                        "sender": {"id": sender, "name": None},
                        "text": str(msg["text"]),
                    },
                    external_account_id=account,
                )
            )
    return provider, out


def _send_dm(adapter: _MetaPublisher, recipient: str, text: str) -> str:
    r = adapter._client().request(
        "POST",
        "me/messages",
        operation="send",
        params={"access_token": adapter._token()},
        json={"recipient": {"id": recipient}, "messaging_type": "RESPONSE", "message": {"text": text[:2000]}},
    )
    data = r.json() if r.content else {}
    if r.status_code < 400 and "error" not in data:
        return str(data.get("message_id", ""))
    err = data.get("error") or {}
    if (err.get("code") == 10 and err.get("error_subcode") == 2018278) or err.get("error_subcode") == 2534022:
        raise IntegrationError("outside_reply_window", "meta send")
    if err.get("code") == 190:
        raise IntegrationError("invalid_credentials", "meta send", auth=True)
    if err.get("code") in (10, 200, 230) or err.get("error_subcode") == 2018108:
        raise IntegrationError("messaging_not_approved", "meta send")  # Meta App Review pending
    if r.status_code >= 500 or err.get("code") in (4, 17, 32, 613):
        raise IntegrationError("provider_unavailable", "meta send", retryable=True)
    raise IntegrationError("provider_rejected", "meta send")
