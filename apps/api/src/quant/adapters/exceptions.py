"""Exception taxonomy shared by every provider adapter."""

from __future__ import annotations


class AdapterError(Exception):
    """Base class for adapter failures."""


class ProviderError(AdapterError):
    """Upstream returned an error response (non-2xx)."""

    def __init__(self, provider: str, status_code: int, body: str | None = None) -> None:
        self.provider = provider
        self.status_code = status_code
        self.body = body
        super().__init__(f"[{provider}] HTTP {status_code}: {(body or '')[:200]}")


class RateLimitError(ProviderError):
    """Upstream signalled rate limiting (429 / provider-specific)."""


class AuthenticationError(ProviderError):
    """401 / 403 from upstream — API key invalid, expired, or lacks entitlement."""


class TransientError(AdapterError):
    """Network flake, timeout, or 5xx — safe to retry."""


class DataQualityError(AdapterError):
    """Upstream returned 200 but the payload is malformed or empty when it shouldn't be."""
