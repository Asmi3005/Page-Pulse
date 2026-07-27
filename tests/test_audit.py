import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient

from app import service
from app.cache import get_cached, set_cached
from app.models import AuditData

SAMPLE_HTML = """
<html>
  <head>
    <title>Example Domain</title>
    <meta name="description" content="An example page for audits." />
  </head>
  <body>Hello</body>
</html>
"""


def _mock_response(
    *,
    url: str = "https://example.com/",
    status_code: int = 200,
    text: str = SAMPLE_HTML,
    content_type: str = "text/html; charset=utf-8",
) -> MagicMock:
    response = MagicMock()
    response.url = httpx.URL(url)
    response.status_code = status_code
    response.text = text
    response.headers = {"content-type": content_type}
    return response


@pytest.mark.asyncio
async def test_successful_audit(client: AsyncClient) -> None:
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_mock_response())
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.service.httpx.AsyncClient", return_value=mock_client):
        response = await client.post("/audit", json={"url": "https://example.com"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["url"] == "https://example.com/"
    assert data["final_url"] == "https://example.com/"
    assert data["status_code"] == 200
    assert data["title"] == "Example Domain"
    assert data["meta_description"] == "An example page for audits."
    assert data["content_type"] == "text/html; charset=utf-8"
    assert data["is_https"] is True
    assert data["cached"] is False
    assert isinstance(data["response_time_ms"], (int, float))


@pytest.mark.asyncio
async def test_invalid_url(client: AsyncClient) -> None:
    response = await client.post("/audit", json={"url": "not-a-valid-url"})

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_URL"
    assert "message" in body["error"]


@pytest.mark.asyncio
async def test_timeout(client: AsyncClient) -> None:
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.service.httpx.AsyncClient", return_value=mock_client):
        response = await client.post("/audit", json={"url": "https://slow.example.com"})

    assert response.status_code == 408
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "TIMEOUT"
    assert "10 seconds" in body["error"]["message"].lower()


@pytest.mark.asyncio
async def test_cache_hit(client: AsyncClient) -> None:
    cached = AuditData(
        url="https://cached.example.com/",
        final_url="https://cached.example.com/",
        status_code=200,
        response_time_ms=12.5,
        title="Cached",
        meta_description="From cache",
        content_type="text/html",
        is_https=True,
        cached=False,
    )
    set_cached("https://cached.example.com/", cached)

    with patch("app.service.httpx.AsyncClient") as mock_async_client:
        response = await client.post(
            "/audit",
            json={"url": "https://cached.example.com/"},
        )
        mock_async_client.assert_not_called()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["title"] == "Cached"
    assert body["data"]["cached"] is True
    assert get_cached("https://cached.example.com/") is not None
    assert get_cached("https://cached.example.com/").cached is False


@pytest.mark.asyncio
async def test_concurrency_limit() -> None:
    original = service._outbound_limit
    service._outbound_limit = asyncio.Semaphore(1)

    started: list[float] = []
    finished: list[float] = []
    release_first = asyncio.Event()

    async def slow_fetch(url: str) -> AuditData:
        loop = asyncio.get_running_loop()
        started.append(loop.time())
        await release_first.wait()
        finished.append(loop.time())
        return AuditData(
            url=url,
            final_url=url,
            status_code=200,
            response_time_ms=1.0,
            title=None,
            meta_description=None,
            content_type="text/html",
            is_https=True,
            cached=False,
        )

    try:
        with patch("app.service._fetch_and_parse", side_effect=slow_fetch):
            task1 = asyncio.create_task(service.audit_url("https://one.example.com"))
            await asyncio.sleep(0.05)
            task2 = asyncio.create_task(service.audit_url("https://two.example.com"))
            await asyncio.sleep(0.05)

            assert len(started) == 1

            release_first.set()
            await asyncio.gather(task1, task2)

            assert len(started) == 2
            assert len(finished) == 2
            assert started[1] >= finished[0]
    finally:
        service._outbound_limit = original
