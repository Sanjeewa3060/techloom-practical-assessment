"""Central configuration, read from environment variables."""
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pos.db")
RESERVATION_TTL_SECONDS = int(os.getenv("RESERVATION_TTL_SECONDS", "300"))  # 5 minutes
EXPIRY_SWEEP_SECONDS = int(os.getenv("EXPIRY_SWEEP_SECONDS", "5"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
SEED_ON_START = os.getenv("SEED_ON_START", "true").lower() == "true"
