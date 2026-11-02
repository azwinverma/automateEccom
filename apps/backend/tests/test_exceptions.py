from __future__ import annotations

from app.domains.integrations.base import IntegrationError
from app.domains.integrations.sandbox import SandboxChannelAdapter
from tests.conftest import onboard
from tests.test_channels import _dispatch, connect, live_product


def test_exception_inbox_reflects_live_state_and_clears_when_fixed(client, seller):
    assert client.get("/api/v1/exceptions", headers=seller.h()).json() == {
        "items": [],
        "counts": {},
        "total": 0,
    }
    c = connect(client, seller)
    p = live_product(client, seller)
    SandboxChannelAdapter.failures.push(IntegrationError("token_revoked", auth=True))
    client.post(
        f"/api/v1/catalog/products/{p['id']}/publish", headers=seller.h(), json={"connection_ids": [c["id"]]}
    )
    _dispatch()
    inbox = client.get("/api/v1/exceptions", headers=seller.h()).json()
    types = [(i["type"], i["severity"], i["action"]) for i in inbox["items"]]
    assert types[0] == ("channel_expired", "urgent", "reconnect")  # most urgent first
    assert ("publish_failed", "high", "reconnect") in types
    assert inbox["counts"] == {"urgent": 1, "high": 1}
    # Another merchant never sees these.
    other = onboard(client, shop="Patan Crafts")
    assert client.get("/api/v1/exceptions", headers=other.h()).json()["total"] == 0


def test_reconnecting_clears_channel_and_listing_exceptions(client, seller, monkeypatch):
    import uuid

    from app.core.db import session_scope
    from app.domains.channels.models import ChannelConnection

    c = connect(client, seller)
    p = live_product(client, seller)
    SandboxChannelAdapter.failures.push(IntegrationError("token_revoked", auth=True))
    client.post(
        f"/api/v1/catalog/products/{p['id']}/publish", headers=seller.h(), json={"connection_ids": [c["id"]]}
    )
    _dispatch()
    assert client.get("/api/v1/exceptions", headers=seller.h()).json()["total"] == 2
    with session_scope() as db:
        acct = db.get(ChannelConnection, uuid.UUID(c["id"])).external_account_id
    original = SandboxChannelAdapter.exchange_code

    def same_account(self, code, redirect_uri):
        t = original(self, code, redirect_uri)
        t.external_account_id = acct
        return t

    monkeypatch.setattr(SandboxChannelAdapter, "exchange_code", same_account)
    connect(client, seller, reconnect_id=c["id"])
    _dispatch()
    assert client.get("/api/v1/exceptions", headers=seller.h()).json()["total"] == 0
