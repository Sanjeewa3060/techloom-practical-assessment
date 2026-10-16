"""Product CRUD + live stock levels."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..models import Product
from ..schemas import ProductIn, ProductOut, ProductUpdate, StockOut

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(
    response: Response,
    search: Optional[str] = Query(None, description="matches name or description"),
    category: Optional[str] = None,
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    in_stock: Optional[bool] = Query(None, description="true = only items with stock available"),
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc|name)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Product discovery: search + category / price / availability filters, sorted and paginated.
    The total number of matches (before paging) is returned in the X-Total-Count header."""
    services.expire_due(db)
    q = select(Product)
    if search:
        like = f"%{search.strip()}%"
        q = q.where(or_(Product.name.ilike(like), Product.description.ilike(like)))
    if category:
        q = q.where(Product.category == category)
    if min_price is not None:
        q = q.where(Product.price >= min_price)
    if max_price is not None:
        q = q.where(Product.price <= max_price)
    if in_stock is True:
        q = q.where(Product.stock_total - Product.stock_reserved > 0)
    elif in_stock is False:
        q = q.where(Product.stock_total - Product.stock_reserved <= 0)
    order = {"newest": Product.id.desc(), "price_asc": Product.price.asc(),
             "price_desc": Product.price.desc(), "name": Product.name.asc()}[sort]
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    response.headers["X-Total-Count"] = str(total)
    return db.scalars(q.order_by(order, Product.id).limit(page_size).offset((page - 1) * page_size)).all()


@router.get("/categories", response_model=list[str])
def categories(db: Session = Depends(get_db)):
    rows = db.scalars(select(Product.category).where(Product.category.is_not(None)).distinct()).all()
    return sorted(rows)


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
