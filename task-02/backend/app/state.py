"""Order status values and the allowed transitions (the order state machine)."""
PENDING = "PENDING"
RESERVED = "RESERVED"
PAID = "PAID"
FAILED = "FAILED"
EXPIRED = "EXPIRED"
CANCELLED = "CANCELLED"

ALLOWED = {
    PENDING: {RESERVED, FAILED, CANCELLED},
    RESERVED: {PAID, FAILED, EXPIRED, CANCELLED},
    PAID: {CANCELLED},
    FAILED: set(),
    EXPIRED: set(),
    CANCELLED: set(),
}
