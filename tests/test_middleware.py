from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient

import app.middleware as middleware_module
from app.models import AuditData


def _mock_response() -> MagicMock:
    response = MagicMock()
    response.url = httpx.URL("https://example.com/")
    response.status_code = 200
    response.text = "<html><head><title>Example</title></head></html>"
    response.headers = {"content-type": "text/html"}
    return response


@pytest.mark.asyncio
async def test_rate_limit_per_client(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(middleware_module, "RATE_LIMIT_REQUESTS", 2)
    monkeypatch.setattr(middleware_module, "RATE_LIMIT_WINDOW_SECONDS", 60)

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_mock_response())
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.service.httpx.AsyncClient", return_value=mock_client):
        first = await client.post("/audit", json={"url": "https://example.com/a"})
        second = await client.post("/audit", json={"url": "https://example.com/b"})
        third = await client.post("/audit", json={"url": "https://example.com/c"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    body = third.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RATE_LIMITED"
    assert "X-Request-ID" in third.headers


@pytest.mark.asyncio
async def test_request_id_header_present(client: AsyncClient) -> None:
    cached = AuditData(
        url="https://cached.example.com/",
        final_url="https://cached.example.com/",
        status_code=200,
        response_time_ms=1.0,
        title="Cached",
        meta_description=None,
        content_type="text/html",
        is_https=True,
        cached=False,
    )
    from app.cache import set_cached

    set_cached("https://cached.example.com/", cached)
    response = await client.post("/audit", json={"url": "https://cached.example.com/"})

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0
