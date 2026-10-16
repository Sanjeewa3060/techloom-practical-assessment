"""Product CRUD + live stock levels."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..models import Product
from ..schemas import ProductIn, ProductOut, ProductUpdate, StockOut

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    services.expire_due(db)
    return db.scalars(select(Product).order_by(Product.id)).all()


@router.get("/stock", response_model=list[StockOut])
def stock_levels(db: Session = Depends(get_db)):
    """Current, accurate stock for every product (available = total - reserved)."""
    services.expire_due(db)
    return db.scalars(select(Product).order_by(Product.id)).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@router.post("", response_model=ProductOut, status_code=201)
def create_product(body: ProductIn, db: Session = Depends(get_db)):
    product = Product(**body.model_dump())
    db.add(product)
    db.commit()
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, body: ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    data = body.model_dump(exclude_unset=True)
    if "stock_total" in data and data["stock_total"] < product.stock_reserved:
        raise HTTPException(409, f"Cannot set stock below the {product.stock_reserved} units "
                                 "currently reserved")
    for k, v in data.items():
        setattr(product, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Update violates stock constraints")
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    try:
        db.delete(product)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Product is used by carts or orders and cannot be deleted")
