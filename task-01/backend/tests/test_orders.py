import time

from .conftest import add_to_cart


def stock(client, pid):
    return next(s for s in client.get("/products/stock").json() if s["id"] == pid)


def checkout(client, user, key=None):
    h = {"X-User-Id": user}
    if key:
        h["Idempotency-Key"] = key
    return client.post("/checkout", headers=h)


def test_checkout_reserves_then_payment_confirms(client, product):
    add_to_cart(client, "u1", product["id"], 2)
    r = checkout(client, "u1")
    assert r.status_code == 201 and r.json()["status"] == "RESERVED"
    assert stock(client, product["id"])["available"] == 3
    paid = client.post(f"/orders/{r.json()['id']}/pay", json={"outcome": "success"})
    assert paid.json()["status"] == "PAID"
    s = stock(client, product["id"])
    assert s["stock_total"] == 3 and s["stock_reserved"] == 0


def test_cannot_oversell(client, product):
    add_to_cart(client, "a", product["id"], 5)
    add_to_cart(client, "b", product["id"], 5)  # both pass early validation
    assert checkout(client, "a").status_code == 201
    assert checkout(client, "b").status_code == 409
    assert stock(client, product["id"])["available"] == 0


def test_failure_and_timeout_release_stock(client, product):
    for outcome, status in (("failure", "FAILED"), ("timeout", "EXPIRED")):
        add_to_cart(client, "u", product["id"], 2)
        oid = checkout(client, "u").json()["id"]
        assert client.post(f"/orders/{oid}/pay", json={"outcome": outcome}).json()["status"] == status
        assert stock(client, product["id"])["available"] == 5


def test_duplicate_checkout_and_payment(client, product):
    add_to_cart(client, "u", product["id"], 1)
    first = checkout(client, "u", key="k1")
    again = checkout(client, "u", key="k1")
    assert again.status_code == 200 and again.json()["id"] == first.json()["id"]
    oid = first.json()["id"]
    assert client.post(f"/orders/{oid}/pay", json={"outcome": "success"},
                       headers={"Idempotency-Key": "p1"}).status_code == 200
    # replay with the same key -> same order, no second charge
    assert client.post(f"/orders/{oid}/pay", json={"outcome": "success"},
                       headers={"Idempotency-Key": "p1"}).status_code == 200
    # a fresh attempt on an already paid order is rejected
    assert client.post(f"/orders/{oid}/pay", json={"outcome": "success"}).status_code == 409
    assert len(client.get(f"/orders/{oid}").json()["payments"]) == 1


def test_cancel_restores_stock_and_blocks_invalid_transitions(client, product):
    add_to_cart(client, "u", product["id"], 2)
    oid = checkout(client, "u").json()["id"]
    client.post(f"/orders/{oid}/pay", json={"outcome": "success"})
    assert client.post(f"/orders/{oid}/cancel").json()["status"] == "CANCELLED"
    assert stock(client, product["id"])["stock_total"] == 5
    assert client.post(f"/orders/{oid}/cancel").status_code == 409
    assert client.post(f"/orders/{oid}/pay", json={"outcome": "success"}).status_code == 409


def test_reservation_expires_and_releases_stock(client, product):
    add_to_cart(client, "u", product["id"], 3)
    oid = checkout(client, "u").json()["id"]
    assert stock(client, product["id"])["available"] == 2
    time.sleep(3)  # TTL is 2s in tests
    assert client.get(f"/orders/{oid}").json()["status"] == "EXPIRED"
    assert stock(client, product["id"])["available"] == 5
