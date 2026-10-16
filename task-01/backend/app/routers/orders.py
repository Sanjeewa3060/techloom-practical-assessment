"""Checkout, payment, cancellation and order listing."""
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..models import Order
from ..schemas import OrderOut, PayIn

router = APIRouter(tags=["orders"])


@router.post("/checkout", response_model=OrderOut, status_code=201)
def checkout(response: Response, x_user_id: str = Header("demo"),
             idempotency_key: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Validate stock, reserve it for 5 minutes and create a RESERVED order.
    Send an Idempotency-Key header to make retries/double-clicks safe."""
    order_id, replay = services.checkout(db, x_user_id, idempotency_key)
    if replay:
        response.status_code = 200
    return services.fetch_order(db, order_id)


@router.post("/orders/{order_id}/pay", response_model=OrderOut)
def pay(order_id: int, body: PayIn, idempotency_key: Optional[str] = Header(None),
        db: Session = Depends(get_db)):
    """Mock gateway. outcome = success | failure | timeout (random if omitted)."""
    services.pay(db, order_id, body.outcome, idempotency_key)
    return services.fetch_order(db, order_id)


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
def cancel(order_id: int, db: Session = Depends(get_db)):
    services.cancel(db, order_id)
    return services.fetch_order(db, order_id)


@router.get("/orders", response_model=list[OrderOut])
def list_orders(user_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    services.expire_due(db)
    q = select(Order).order_by(Order.id.desc())
    if user_id:
        q = q.where(Order.user_id == user_id)
    return db.scalars(q).all()


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    services.expire_due(db)
    return services.fetch_order(db, order_id)
