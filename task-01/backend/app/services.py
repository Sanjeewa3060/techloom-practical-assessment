"""Business logic: stock reservation, checkout, mock payment, cancellation, expiry.

Concurrency strategy (works on PostgreSQL and SQLite):
  * Stock is only ever changed with ATOMIC conditional UPDATEs, e.g.
        UPDATE products SET stock_reserved = stock_reserved + :q
        WHERE id = :id AND stock_total - stock_reserved >= :q
    If rowcount == 0 there was not enough stock. PostgreSQL locks the row for the
    duration of the statement/transaction, so two buyers can never both win the last unit.
  * Order status changes are compare-and-set UPDATEs (WHERE status = :old), so a
    duplicate or racing request can only succeed once.
  * Everything for one action happens in ONE transaction: an exception means rollback.
"""
import random
from datetime import timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import state
from .config import RESERVATION_TTL_SECONDS
from .models import CartItem, Order, OrderItem, Payment, Product, utcnow

NO_SYNC = {"synchronize_session": False}


# ----------------------------------------------------------------- helpers
def fetch_order(db: Session, order_id: int) -> Order:
    order = db.scalar(
        select(Order).where(Order.id == order_id).execution_options(populate_existing=True)
    )
    if not order:
        raise HTTPException(404, "Order not found")
    return order


def _transition(db: Session, order: Order, to: str) -> None:
    """Enforce the state machine, atomically (compare-and-set on the current status)."""
    if to not in state.ALLOWED[order.status]:
        raise HTTPException(409, f"Invalid transition {order.status} -> {to}")
    res = db.execute(
        update(Order)
        .where(Order.id == order.id, Order.status == order.status)
        .values(status=to, updated_at=utcnow())
        .execution_options(**NO_SYNC)
    )
    if res.rowcount != 1:
        raise HTTPException(409, "Order was changed by another request. Reload and retry.")
    order.status = to


def _hold(db: Session, lines: list[tuple[int, int]]) -> None:
    """Reserve stock. Sorted by product id so concurrent checkouts lock rows in the same
    order (prevents deadlocks)."""
    for pid, qty in sorted(lines):
        res = db.execute(
            update(Product)
            .where(Product.id == pid, Product.stock_total - Product.stock_reserved >= qty)
            .values(stock_reserved=Product.stock_reserved + qty)
            .execution_options(**NO_SYNC)
        )
        if res.rowcount != 1:
            raise HTTPException(409, f"Not enough stock for product {pid}")


def _release_hold(db: Session, lines: list[tuple[int, int]]) -> None:
    for pid, qty in sorted(lines):
        db.execute(
            update(Product)
            .where(Product.id == pid, Product.stock_reserved >= qty)
            .values(stock_reserved=Product.stock_reserved - qty)
            .execution_options(**NO_SYNC)
        )


def _commit_sale(db: Session, lines: list[tuple[int, int]]) -> None:
    """Payment succeeded: reserved units are now sold (leave physical stock)."""
    for pid, qty in sorted(lines):
        db.execute(
            update(Product)
            .where(Product.id == pid)
            .values(
                stock_total=Product.stock_total - qty,
                stock_reserved=Product.stock_reserved - qty,
            )
            .execution_options(**NO_SYNC)
        )


def _restore_sale(db: Session, lines: list[tuple[int, int]]) -> None:
    """A PAID order is cancelled: put the units back on the shelf."""
    for pid, qty in sorted(lines):
        db.execute(
            update(Product)
            .where(Product.id == pid)
            .values(stock_total=Product.stock_total + qty)
            .execution_options(**NO_SYNC)
        )


def _lines(order: Order) -> list[tuple[int, int]]:
    return [(i.product_id, i.qty) for i in order.items]


# ---------------------------------------------------------------- checkout
def checkout(db: Session, user_id: str, key: str | None) -> tuple[int, bool]:
    """Convert the user's cart into a RESERVED order. Returns (order_id, is_replay)."""
    expire_due(db)  # free stock from stale reservations first

    if key:
        existing = db.scalar(select(Order).where(Order.idempotency_key == key))
        if existing:
            if existing.user_id != user_id:
                raise HTTPException(409, "Idempotency-Key already used")
            return existing.id, True

    cart = db.scalars(
        select(CartItem).where(CartItem.user_id == user_id).order_by(CartItem.product_id)
    ).all()
    if not cart:
        raise HTTPException(400, "Cart is empty (it may already have been checked out)")
    lines = [(c.product_id, c.qty, c.product.price) for c in cart]
    cart_ids = [c.id for c in cart]

    order = Order(
        user_id=user_id,
        status=state.PENDING,
        total=0,
        idempotency_key=key,
        expires_at=utcnow() + timedelta(seconds=RESERVATION_TTL_SECONDS),
    )
    db.add(order)
    try:
        db.flush()
    except IntegrityError:  # two requests with the same key raced: the DB UNIQUE index decides
        db.rollback()
        existing = db.scalar(select(Order).where(Order.idempotency_key == key))
        if existing:
            return existing.id, True
        raise

    # Claim the cart rows. If a parallel checkout already took them, rowcount differs.
    res = db.execute(delete(CartItem).where(CartItem.id.in_(cart_ids)).execution_options(**NO_SYNC))
    if res.rowcount != len(cart_ids):
        raise HTTPException(409, "This cart was already submitted")

    _hold(db, [(pid, qty) for pid, qty, _ in lines])  # raises 409 if oversold -> rollback
    order.items = [OrderItem(product_id=p, qty=q, unit_price=price) for p, q, price in lines]
    order.total = sum((price * q for _, q, price in lines), Decimal("0"))
    _transition(db, order, state.RESERVED)
    db.commit()
    return order.id, False


# ------------------------------------------------------------- mock payment
def simulate_gateway(requested: str | None) -> str:
    """Mock payment gateway. Returns success | failure | timeout."""
    return requested or random.choices(["success", "failure", "timeout"], [70, 20, 10])[0]


def pay(db: Session, order_id: int, requested: str | None, key: str | None) -> tuple[int, bool]:
    """Returns (order_id, is_replay)."""
    if key:
        prior = db.scalar(select(Payment).where(Payment.idempotency_key == key))
        if prior:
            if prior.order_id != order_id:
                raise HTTPException(409, "Idempotency-Key already used for another order")
            return order_id, True  # same request replayed -> same result, no second charge

    order = fetch_order(db, order_id)
    if order.status == state.PAID:
        raise HTTPException(409, "Duplicate payment rejected: order is already paid")
    if order.status != state.RESERVED:
        raise HTTPException(409, f"Order is {order.status}; it cannot be paid")

    if order.expires_at <= utcnow():  # lazy expiry: correct even if the sweeper is late
        _transition(db, order, state.EXPIRED)
        _release_hold(db, _lines(order))
        db.commit()
        raise HTTPException(409, "Reservation expired; stock was released")

    outcome = simulate_gateway(requested)
    lines = _lines(order)
    _transition(db, order, {"success": state.PAID, "failure": state.FAILED,
                            "timeout": state.EXPIRED}[outcome])
    if outcome == "success":
        _commit_sale(db, lines)
    else:
        _release_hold(db, lines)
    db.add(Payment(order_id=order.id, outcome=outcome, idempotency_key=key,
                   amount=order.total if outcome == "success" else 0))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Duplicate payment request")
    return order.id, False


# ----------------------------------------------------------- cancellation
def cancel(db: Session, order_id: int) -> int:
    order = fetch_order(db, order_id)
    lines = _lines(order)
    previous = order.status
    if previous not in (state.PENDING, state.RESERVED, state.PAID):
        raise HTTPException(409, f"Order is {previous}; it cannot be cancelled")
    _transition(db, order, state.CANCELLED)
    if previous == state.RESERVED:
        _release_hold(db, lines)
    elif previous == state.PAID:
        _restore_sale(db, lines)
    db.commit()
    return order.id


# ------------------------------------------------------------------ expiry
def expire_due(db: Session) -> int:
    """Expire every RESERVED order past its deadline and release its stock."""
    ids = db.scalars(
        select(Order.id)
        .where(Order.status == state.RESERVED, Order.expires_at <= utcnow())
        .limit(200)
    ).all()
    done = 0
    for oid in ids:
        try:
            order = fetch_order(db, oid)
            _transition(db, order, state.EXPIRED)
            _release_hold(db, _lines(order))
            db.commit()
            done += 1
        except HTTPException:  # someone else handled it first
            db.rollback()
    db.rollback()  # end any read-only transaction
    return done
