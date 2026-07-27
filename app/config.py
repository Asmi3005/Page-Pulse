import os


def _int_env(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _float_env(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


# Cache window is configurable so operators can tune freshness without code changes.
CACHE_TTL_SECONDS = _int_env("CACHE_TTL_SECONDS", 300)
CACHE_MAX_SIZE = _int_env("CACHE_MAX_SIZE", 256)

REQUEST_TIMEOUT_SECONDS = _float_env("REQUEST_TIMEOUT_SECONDS", 10.0)
MAX_OUTBOUND_REQUESTS = _int_env("MAX_OUTBOUND_REQUESTS", 3)

# Per-client rate limit (incoming requests), separate from outbound concurrency.
RATE_LIMIT_REQUESTS = _int_env("RATE_LIMIT_REQUESTS", 30)
RATE_LIMIT_WINDOW_SECONDS = _int_env("RATE_LIMIT_WINDOW_SECONDS", 60)
