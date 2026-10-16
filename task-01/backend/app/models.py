"""Database models. DB-level CHECK constraints are a safety net against overselling."""
from datetime import datetime, timezone

from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, Index, Integer,
                        Numeric, String, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .state import PENDING


def utcnow() -> datetime:
    """Naive UTC timestamp (works the same on Postgres and SQLite)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("stock_total >= 0", name="ck_stock_total_nonneg"),
        CheckConstraint("stock_reserved >= 0", name="ck_stock_reserved_nonneg"),
        CheckConstraint("stock_total >= stock_reserved", name="ck_reserved_lte_total"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    stock_total: Mapped[int] = mapped_column(Integer, default=0)      # physically in stock
    stock_reserved: Mapped[int] = mapped_column(Integer, default=0)   # held by open checkouts
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    @property
    def available(self) -> int:
        return self.stock_total - self.stock_reserved


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[int] = mapped_column(Integer)
    product: Mapped[Product] = relationship(lazy="selectin")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_status_expires", "status", "expires_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default=PENDING)
    total: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    # UNIQUE -> the database itself rejects a duplicate checkout with the same key
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    items: Mapped[list["OrderItem"]] = relationship(lazy="selectin", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(lazy="selectin", order_by="Payment.id")

    @property
    def seconds_left(self) -> int:
        if self.status != "RESERVED":
            return 0
        return max(0, int((self.expires_at - utcnow()).total_seconds()))


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    product: Mapped[Product] = relationship(lazy="selectin")

    @property
    def name(self) -> str:
        return self.product.name


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    outcome: Mapped[str] = mapped_column(String(20))   # success | failure | timeout
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
