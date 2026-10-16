import os
import tempfile

# Must be set BEFORE the app is imported.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["RESERVATION_TTL_SECONDS"] = "2"
os.environ["EXPIRY_SWEEP_SECONDS"] = "1"
os.environ["SEED_ON_START"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def product(client):
    r = client.post("/products", json={"name": "Widget", "price": 10, "stock_total": 5})
    assert r.status_code == 201
    return r.json()


def add_to_cart(client, user, product_id, qty):
    return client.put("/cart/items", json={"product_id": product_id, "qty": qty},
                      headers={"X-User-Id": user})
