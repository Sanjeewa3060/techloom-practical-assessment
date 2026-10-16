"""Shopping cart. The user is identified by the X-User-Id header (demo-level identity)."""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CartItem, Product
from ..schemas import CartItemIn, CartItemOut, CartOut

router = APIRouter(prefix="/cart", tags=["cart"])


def _cart(db: Session, user_id: str) -> CartOut:
    items = db.scalars(
        select(CartItem).where(CartItem.user_id == user_id).order_by(CartItem.id)
    ).all()
    total = sum(float(i.product.price) * i.qty for i in items)
    return CartOut(items=[CartItemOut.model_validate(i) for i in items], total=round(total, 2))


@router.get("", response_model=CartOut)
def get_cart(x_user_id: str = Header("demo"), db: Session = Depends(get_db)):
    return _cart(db, x_user_id)


@router.put("/items", response_model=CartOut)
def set_item(body: CartItemIn, x_user_id: str = Header("demo"), db: Session = Depends(get_db)):
    """Set the quantity of a product in the cart (0 removes it)."""
    product = db.get(Product, body.product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    item = db.scalar(select(CartItem).where(CartItem.user_id == x_user_id,
                                            CartItem.product_id == body.product_id))
    if body.qty == 0:
        if item:
            db.delete(item)
    else:
        if body.qty > product.available:  # early validation; checkout re-validates atomically
            raise HTTPException(409, f"Only {product.available} in stock")
        if item:
            item.qty = body.qty
        else:
            db.add(CartItem(user_id=x_user_id, product_id=body.product_id, qty=body.qty))
    db.commit()
    return _cart(db, x_user_id)


@router.delete("", response_model=CartOut)
def clear_cart(x_user_id: str = Header("demo"), db: Session = Depends(get_db)):
    for item in db.scalars(select(CartItem).where(CartItem.user_id == x_user_id)).all():
        db.delete(item)
    db.commit()
    return _cart(db, x_user_id)
