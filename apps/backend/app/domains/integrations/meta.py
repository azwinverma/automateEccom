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
    auth_kind = "api_keys"
    capabilities = frozenset({ChannelCapability.CONTENT_PUBLISH})
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
        return []  # publishing only; nothing to subscribe to

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
