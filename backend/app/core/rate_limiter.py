import time
import threading
from collections import defaultdict
from typing import Dict, Tuple, Optional
from fastapi import Request, HTTPException, status
from app.core.config import settings

class InMemoryRateLimiter:
    """
    Sliding-window rate limiter for sensitive API endpoints (auth, LLM generation, scraping).
    Tracks requests per client IP or authenticated user.
    """
    def __init__(self):
        self._lock = threading.Lock()
        # key -> list of timestamps
        self._requests: Dict[str, list] = defaultdict(list)
        # Enabled by default, can be toggled via settings or tests
        self.enabled: bool = True

    def _cleanup_old(self, key: str, window_seconds: float, current_time: float):
        cutoff = current_time - window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    def check_rate_limit(
        self,
        request: Request,
        key_prefix: str,
        max_requests: int,
        window_seconds: int = 60,
        custom_identifier: Optional[str] = None
    ):
        if not self.enabled or getattr(settings, "AUTH_DISABLED", False):
            return

        # Check for test bypass header if provided
        if request.headers.get("X-Test-Bypass-Rate-Limit") == "true":
            return

        client_ip = request.client.host if request.client else "127.0.0.1"
        ident = custom_identifier or client_ip
        cache_key = f"{key_prefix}:{ident}"
        now = time.time()

        with self._lock:
            self._cleanup_old(cache_key, window_seconds, now)
            history = self._requests[cache_key]

            if len(history) >= max_requests:
                earliest = history[0]
                retry_after = max(1, int(window_seconds - (now - earliest)))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for {key_prefix}. Please retry after {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )

            self._requests[cache_key].append(now)

limiter = InMemoryRateLimiter()

def rate_limit(key_prefix: str, max_requests: int, window_seconds: int = 60):
    """
    FastAPI dependency for rate limiting an endpoint.
    Example: Depends(rate_limit("auth", max_requests=10, window_seconds=60))
    """
    def dependency(request: Request):
        limiter.check_rate_limit(request, key_prefix, max_requests, window_seconds)
    return dependency
