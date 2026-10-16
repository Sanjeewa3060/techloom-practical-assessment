"""Pydantic request/response models."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: float = Field(ge=0)
    stock_total: int = Field(ge=0)
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    price: Optional[float] = Field(default=None, ge=0)
    stock_total: Optional[int] = Field(default=None, ge=0)
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None


class ProductOut(ORM):
    id: int
    name: str
    price: float
    stock_total: int
    stock_reserved: int
    available: int
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None


class StockOut(ORM):
    id: int
    name: str
    stock_total: int
    stock_reserved: int
    available: int


class CartItemIn(BaseModel):
    product_id: int
    qty: int = Field(ge=0, description="New quantity for this product. 0 removes it.")


class CartItemOut(ORM):
    id: int
    product_id: int
    qty: int
    product: ProductOut


class CartOut(BaseModel):
    items: list[CartItemOut]
    total: float


class OrderItemOut(ORM):
    product_id: int
    name: str
    qty: int
    unit_price: float


class PaymentOut(ORM):
    id: int
    outcome: str
    amount: float
    created_at: datetime


class RefundOut(ORM):
    id: int
    amount: float
    status: str
    created_at: datetime


class OrderOut(ORM):
    id: int
    user_id: str
    status: str
    total: float
    expires_at: datetime
    seconds_left: int
    created_at: datetime
    items: list[OrderItemOut]
    payments: list[PaymentOut]
    refund: Optional[RefundOut] = None


class PayIn(BaseModel):
    # Omit to let the mock gateway pick randomly (70% success / 20% failure / 10% timeout).
    outcome: Optional[Literal["success", "failure", "timeout"]] = None
