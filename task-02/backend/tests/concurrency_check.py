"""Fire many simultaneous checkouts at a LIVE server and verify nothing is oversold.

    python tests/concurrency_check.py http://localhost:8000 --stock 5 --buyers 30
"""
import argparse
from concurrent.futures import ThreadPoolExecutor

import httpx

ap = argparse.ArgumentParser()
ap.add_argument("base")
ap.add_argument("--stock", type=int, default=5)
ap.add_argument("--buyers", type=int, default=30)
args = ap.parse_args()
base = args.base.rstrip("/")

with httpx.Client(base_url=base, timeout=30) as c:
    p = c.post("/products", json={"name": "Concurrency test item", "price": 1,
                                  "stock_total": args.stock}).json()
    for i in range(args.buyers):  # every buyer has 1 unit in their cart
        c.put("/cart/items", json={"product_id": p["id"], "qty": 1}, headers={"X-User-Id": f"buyer{i}"})


def buy(i):
    with httpx.Client(base_url=base, timeout=60) as c:
        return c.post("/checkout", headers={"X-User-Id": f"buyer{i}"}).status_code


with ThreadPoolExecutor(max_workers=args.buyers) as pool:
    codes = list(pool.map(buy, range(args.buyers)))

ok, rejected = codes.count(201), codes.count(409)
with httpx.Client(base_url=base) as c:
    s = next(x for x in c.get("/products/stock").json() if x["id"] == p["id"])
print(f"success={ok} rejected={rejected} other={len(codes) - ok - rejected}  stock={s}")
assert ok == args.stock, "OVERSOLD or UNDERSOLD!"
assert s["available"] == 0 and s["stock_reserved"] == args.stock
print("PASS: exactly", args.stock, "units were reserved, none oversold")
