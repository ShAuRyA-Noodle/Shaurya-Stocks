import time
from collections import defaultdict
from fastapi import Header, HTTPException, status

# -------------------------
# API KEYS (DEV / MVP)
# -------------------------
# Later: move to env vars or database
VALID_API_KEYS = {
    "free-key-123": "free",
    "pro-key-456": "pro",
}

# -------------------------
# RATE LIMIT CONFIG
# -------------------------
RATE_LIMITS = {
    "free": 10,    # requests per minute
    "pro": 120,
}

# In-memory request log: {api_key: [timestamps]}
_request_log = defaultdict(list)


def require_api_key(x_api_key: str = Header(...)):
    """
    Validates API key and enforces per-tier rate limits.
    Returns the user's tier if allowed.
    """
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    tier = VALID_API_KEYS[x_api_key]
    limit = RATE_LIMITS[tier]

    now = time.time()
    window_start = now - 60  # 1-minute rolling window

    # Clean old requests
    requests = _request_log[x_api_key]
    _request_log[x_api_key] = [t for t in requests if t > window_start]

    # Enforce limit
    if len(_request_log[x_api_key]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    # Record this request
    _request_log[x_api_key].append(now)

    return tier
