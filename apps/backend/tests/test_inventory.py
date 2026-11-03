"""INV-001…009: ledger, levels, reservations (no oversell), transfers, low stock, channel stock sync."""

from __future__ import annotations

import threading
import uuid

import pytest
from sqlalchemy import func, select, text

from app.core.context import Actor
from app.core.db import session_scope
from app.domains.inventory import service
from app.domains.inventory.models import InventoryLedgerEntry, InventoryLevel
from app.domains.platform.models import OutboxEvent
from tests.conftest import onboard, set_plan

API = "/api/v1"


def product(client, s, sku="KURTA-M", price=245000):
    p = client.post(
        f"{API}/catalog/products",
        headers=s.h(),
        json={"title": "Cotton Kurta", "variants": [{"price_minor": price, "sku": sku}]},
    ).json()
    return p, p["variants"][0]["id"]


def stock(client, s, pid):
    return client.get(f"{API}/catalog/products/{pid}/stock", headers=s.h()).json()["variants"][0]


def test_untracked_until_stock_recorded_then_ledger_and_levels_agree(client, seller):
    p, vid = product(client, seller)
    assert stock(client, seller, p["id"])["tracked"] is False
    r = client.post(
        f"{API}/inventory/variants/{vid}/receive",
        headers=seller.h(),
        json={"quantity": 10, "reason": "first batch"},
    )
    assert r.status_code == 200 and r.json()["available"] == 10
    client.post(
        f"{API}/inventory/variants/{vid}/adjust", headers=seller.h(), json={"delta": -2, "reason": "gift"}
    )
    client.post(
        f"{API}/inventory/variants/{vid}/damage", headers=seller.h(), json={"quantity": 1, "reason": "torn"}
    )
    client.post(f"{API}/inventory/variants/{vid}/count", headers=seller.h(), json={"counted": 6})
    s = stock(client, seller, p["id"])
    assert s["tracked"] and s["on_hand"] == 6 and s["locations"][0]["damaged"] == 1
    entries = client.get(f"{API}/inventory/variants/{vid}/ledger", headers=seller.h()).json()["items"]
    assert [e["kind"] for e in entries] == ["count", "damage", "adjust", "receive"]
    with session_scope() as db:  # ledger sum == level (the ledger is the truth)
        total = db.scalar(
            select(func.sum(InventoryLedgerEntry.on_hand_delta)).where(
                InventoryLedgerEntry.variant_id == uuid.UUID(vid)
            )
        )
        lvl = db.scalar(select(InventoryLevel).where(InventoryLevel.variant_id == uuid.UUID(vid)))
        assert total == lvl.on_hand == 6


def test_stock_never_negative_and_receive_is_idempotent(client, seller):
    _, vid = product(client, seller)
    h = seller.h(**{"Idempotency-Key": "grn-0001-abcd"})
    client.post(f"{API}/inventory/variants/{vid}/receive", headers=h, json={"quantity": 5})
    again = client.post(f"{API}/inventory/variants/{vid}/receive", headers=h, json={"quantity": 5})
    assert again.json()["on_hand"] == 5  # a retried delivery note isn't counted twice
    r = client.post(
        f"{API}/inventory/variants/{vid}/adjust", headers=seller.h(), json={"delta": -6, "reason": "miscount"}
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "stock_negative"
    assert (
        client.post(
            f"{API}/inventory/variants/{vid}/receive", headers=seller.h(), json={"quantity": 0}
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"{API}/inventory/variants/{vid}/receive", headers=seller.h(), json={"quantity": "3"}
        ).status_code
        == 400
    )


def test_ledger_is_append_only(client, seller):
    _, vid = product(client, seller)
    client.post(f"{API}/inventory/variants/{vid}/receive", headers=seller.h(), json={"quantity": 1})
    with pytest.raises(Exception, match="append-only"), session_scope() as db:
        db.execute(text("UPDATE inventory_ledger SET on_hand_delta = 100"))


def test_concurrent_reservations_never_oversell(client, seller):
    _, vid = product(client, seller)
    client.post(f"{API}/inventory/variants/{vid}/receive", headers=seller.h(), json={"quantity": 5})
    mid = uuid.UUID(seller.merchant_id)
    ok, sold_out = [], []

    def buy(i: int) -> None:
        try:
            with session_scope(mid) as db:
                service.reserve(
                    db,
                    mid,
                    Actor.system("t"),
                    uuid.UUID(vid),
                    1,
                    reference_type="order",
                    reference_id=f"o{i}",
                )
            ok.append(i)
        except service.OutOfStock:
            sold_out.append(i)

    threads = [threading.Thread(target=buy, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ok) == 5 and len(sold_out) == 7


def test_reservation_idempotent_release_and_commit(client, seller):
    p, vid = product(client, seller)
    client.post(f"{API}/inventory/variants/{vid}/receive", headers=seller.h(), json={"quantity": 3})
    mid, v = uuid.UUID(seller.merchant_id), uuid.UUID(vid)
    a = Actor.system("t")
    with session_scope(mid) as db:
        r1 = service.reserve(db, mid, a, v, 2, reference_type="order", reference_id="o1")
        r2 = service.reserve(db, mid, a, v, 2, reference_type="order", reference_id="o1")
        assert r1.id == r2.id
    assert stock(client, seller, p["id"])["available"] == 1
    with session_scope(mid) as db:
        (r,) = service.reservations_for(db, mid, "order", "o1")
        service.release(db, a, r)
        service.release(db, a, r)  # double release is a no-op
    assert stock(client, seller, p["id"])["available"] == 3
    with session_scope(mid) as db:
        r = service.reserve(db, mid, a, v, 2, reference_type="order", reference_id="o1")  # re-reserve
        service.commit(db, a, r)
    s = stock(client, seller, p["id"])
    assert s["on_hand"] == 1 and s["reserved"] == 0
    with session_scope(mid) as db:
        with pytest.raises(service.OutOfStock) as e:
            service.reserve(db, mid, a, v, 2, reference_type="order", reference_id="o2")
        assert e.value.details["available"] == 1
        _, untracked = product(client, seller, sku="MADE-TO-ORDER")
        assert (
            service.reserve(db, mid, a, uuid.UUID(untracked), 9, reference_type="order", reference_id="o3")
            is None
        )


def test_second_location_needs_plan_and_transfer_moves_stock(client, seller):
    p, vid = product(client, seller)
    r = client.post(f"{API}/inventory/locations", headers=seller.h(), json={"name": "Pokhara shop"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "feature_not_in_plan"
    set_plan(seller.merchant_id, "business")
    loc = client.post(
        f"{API}/inventory/locations", headers=seller.h(), json={"name": "Pokhara shop", "district": "kaski"}
    ).json()
    main = next(
        x
        for x in client.get(f"{API}/inventory/locations", headers=seller.h()).json()["items"]
        if x["is_default"]
    )
    client.post(f"{API}/inventory/variants/{vid}/receive", headers=seller.h(), json={"quantity": 8})
    t = client.post(
        f"{API}/inventory/variants/{vid}/transfer",
        headers=seller.h(),
        json={"quantity": 3, "from_location_id": main["id"], "to_location_id": loc["id"]},
    )
    assert t.status_code == 200 and t.json()["from"]["on_hand"] == 5 and t.json()["to"]["on_hand"] == 3
    assert stock(client, seller, p["id"])["available"] == 8
    bad = client.post(
        f"{API}/inventory/variants/{vid}/transfer",
        headers=seller.h(),
        json={"quantity": 30, "from_location_id": main["id"], "to_location_id": loc["id"]},
    )
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "stock_negative"


def test_low_stock_flag_once_per_crossing(client, seller):
    _, vid = product(client, seller)
    client.post(f"{API}/inventory/variants/{vid}/receive", headers=seller.h(), json={"quantity": 10})
    client.put(f"{API}/inventory/variants/{vid}/threshold", headers=seller.h(), json={"threshold": 3})
    for _ in range(2):
        client.post(
            f"{API}/inventory/variants/{vid}/adjust",
            headers=seller.h(),
            json={"delta": -4, "reason": "sold offline"},
        )
    low = client.get(f"{API}/inventory/low-stock", headers=seller.h()).json()["items"]
    assert [x["variant_id"] for x in low] == [vid] and low[0]["available"] == 2
    with session_scope() as db:
        flags = [
            e.payload["low_stock"]
            for e in db.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.event_type == "inventory.level_changed")
                .order_by(OutboxEvent.created_at)
            )
        ]
    assert flags == [False, False, True]  # 10 → 6 → 2: flagged when it crossed 3, once


def test_stock_syncs_to_inventory_channels_minus_safety_stock(client, seller):
    from sqlalchemy import update

    from app.domains.channels.models import ChannelConnection
    from app.domains.integrations.sandbox import SandboxChannelAdapter
    from tests.test_channels import _dispatch, connect

    conn = connect(client, seller)
    p, vid = product(client, seller, sku="SYNC-1")
    client.post(f"{API}/catalog/products/{p['id']}/status", headers=seller.h(), json={"status": "active"})
    client.post(
        f"{API}/catalog/products/{p['id']}/publish", headers=seller.h(), json={"connection_ids": [conn["id"]]}
    )
    _dispatch()
    with session_scope() as db:
        db.execute(update(ChannelConnection).values(safety_stock=2))
    client.post(f"{API}/inventory/variants/{vid}/receive", headers=seller.h(), json={"quantity": 7})
    _dispatch()
    assert SandboxChannelAdapter.stock["SYNC-1"] == 5
    client.post(
        f"{API}/inventory/variants/{vid}/adjust",
        headers=seller.h(),
        json={"delta": -6, "reason": "sold offline"},
    )
    _dispatch()
    assert SandboxChannelAdapter.stock["SYNC-1"] == 0  # never negative on the channel


def test_inventory_is_tenant_isolated(client, seller):
    other = onboard(client, shop="Patan Crafts")
    p, vid = product(client, seller)
    assert (
        client.post(
            f"{API}/inventory/variants/{vid}/receive", headers=other.h(), json={"quantity": 1}
        ).status_code
        == 404
    )
    assert client.get(f"{API}/catalog/products/{p['id']}/stock", headers=other.h()).status_code == 404
    assert client.get(f"{API}/inventory/variants/{vid}/ledger", headers=other.h()).status_code == 404
