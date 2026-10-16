"""FastAPI entry point."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import services
from .config import CORS_ORIGINS, EXPIRY_SWEEP_SECONDS, SEED_ON_START
from .database import Base, SessionLocal, engine
from .routers import cart, orders, products
from .seed import seed_if_empty

log = logging.getLogger("pos")


def _sweep_once() -> int:
    with SessionLocal() as db:
        return services.expire_due(db)


async def _sweeper():
    """Background loop: release stock from reservations older than 5 minutes."""
    while True:
        try:
            n = await asyncio.to_thread(_sweep_once)
            if n:
                log.info("expired %s reservations", n)
        except Exception:  # never let the loop die
            log.exception("expiry sweep failed")
        await asyncio.sleep(EXPIRY_SWEEP_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    if SEED_ON_START:
        seed_if_empty()
    task = asyncio.create_task(_sweeper())
    yield
    task.cancel()


app = FastAPI(title="POS Order & Inventory API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"],
                   allow_headers=["*"], expose_headers=["*"])
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
