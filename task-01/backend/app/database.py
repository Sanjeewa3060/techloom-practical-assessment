"""SQLAlchemy engine + session factory."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

url = DATABASE_URL
# Render/Heroku style URLs start with postgres:// - SQLAlchemy needs a driver name.
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+psycopg2://", 1)
elif url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

if url.startswith("sqlite"):
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})
else:
    engine = create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """One session per request. Closing without commit rolls everything back,
    so any exception leaves the database untouched."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
