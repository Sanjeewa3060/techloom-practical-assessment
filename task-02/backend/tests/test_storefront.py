from .conftest import add_to_cart


def mk(client, **kw):
    body = {"name": "X", "price": 10, "stock_total": 5, **kw}
    return client.post("/products", json=body).json()


def test_search_and_filters(client):
    mk(client, name="Zebra Lamp", price=50, category="Lighting", description="striped")
    mk(client, name="Zebra Mug", price=5, category="Kitchen", stock_total=0)
    names = lambda r: [p["name"] for p in r.json()]
    assert names(client.get("/products?search=zebra&sort=name")) == ["Zebra Lamp", "Zebra Mug"]
    assert names(client.get("/products?search=zebra&category=Kitchen")) == ["Zebra Mug"]
    assert names(client.get("/products?search=zebra&min_price=20")) == ["Zebra Lamp"]
    assert names(client.get("/products?search=zebra&in_stock=true")) == ["Zebra Lamp"]


def test_cancel_paid_order_creates_one_refund_and_restores_stock(client):
    p = mk(client, name="Refundable", stock_total=4)
    add_to_cart(client, "r1", p["id"], 2)
    oid = client.post("/checkout", headers={"X-User-Id": "r1"}).json()["id"]
    client.post(f"/orders/{oid}/pay", json={"outcome": "success"})
    done = client.post(f"/orders/{oid}/refund").json()
    assert done["status"] == "CANCELLED" and done["refund"]["amount"] == 20
    assert client.get(f"/products/{p['id']}").json()["stock_total"] == 4
    assert client.post(f"/orders/{oid}/refund").status_code == 409  # no double refund


def test_pagination_returns_total_count_header(client):
    for i in range(12):
        mk(client, name=f"Pager item {i:02d}", category="PagerCat")
    p1 = client.get("/products?category=PagerCat&page=1&page_size=10&sort=name")
    p2 = client.get("/products?category=PagerCat&page=2&page_size=10&sort=name")
    assert p1.headers["X-Total-Count"] == "12"
    assert len(p1.json()) == 10 and len(p2.json()) == 2
