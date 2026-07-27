from cachetools import TTLCache

from app.config import CACHE_MAX_SIZE, CACHE_TTL_SECONDS
from app.models import AuditData

audit_cache: TTLCache[str, AuditData] = TTLCache(
    maxsize=CACHE_MAX_SIZE,
    ttl=CACHE_TTL_SECONDS,
)


def cache_key(url: str) -> str:
    return url.rstrip("/").lower()


def get_cached(url: str) -> AuditData | None:
    return audit_cache.get(cache_key(url))


def set_cached(url: str, data: AuditData) -> None:
    audit_cache[cache_key(url)] = data


def clear_cache() -> None:
    audit_cache.clear()
