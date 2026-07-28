"""Rate limiting middleware — enforces per-IP request limits."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import RATE_LIMIT_PER_MINUTE

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{RATE_LIMIT_PER_MINUTE}/minute"],
    headers_enabled=True,
)
