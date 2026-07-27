from app.cache import cache_key, get_cached, set_cached
from app.models import AuditData


def test_cache_key_normalization() -> None:
    assert cache_key("https://Example.COM/") == "https://example.com"
    assert cache_key("https://example.com") == "https://example.com"


def test_cache_hit_case_insensitive() -> None:
    data = AuditData(
        url="https://example.com/",
        final_url="https://example.com/",
        status_code=200,
        response_time_ms=10.0,
        title="Test",
        meta_description=None,
        content_type="text/html",
        is_https=True,
        cached=False,
    )
    set_cached("https://EXAMPLE.com/", data)
    assert get_cached("https://example.com") is not None
