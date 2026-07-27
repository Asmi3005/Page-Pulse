import asyncio
import time

import httpx

from app.cache import get_cached, set_cached
from app.config import MAX_OUTBOUND_REQUESTS, REQUEST_TIMEOUT_SECONDS
from app.logger import get_request_id, logger
from app.models import AuditData, ErrorDetail
from app.utils import extract_meta_description, extract_title, is_https

_outbound_limit = asyncio.Semaphore(MAX_OUTBOUND_REQUESTS)


class AuditError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.detail = ErrorDetail(code=code, message=message)
        super().__init__(message)


async def audit_url(url: str) -> AuditData:
    cached = get_cached(url)
    if cached is not None:
        logger.info("request_id=%s cache_hit url=%s", get_request_id(), url)
        return cached.model_copy(update={"cached": True})

    async with _outbound_limit:
        return await _fetch_and_parse(url)


async def _fetch_and_parse(url: str) -> AuditData:
    timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS)
    started = time.perf_counter()

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
    except httpx.TimeoutException as exc:
        logger.warning(
            "request_id=%s audit_timeout url=%s error=%s",
            get_request_id(),
            url,
            exc,
        )
        raise AuditError(
            code="TIMEOUT",
            message=f"The URL did not respond within {REQUEST_TIMEOUT_SECONDS:.0f} seconds",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning(
            "request_id=%s audit_connection_error url=%s error=%s",
            get_request_id(),
            url,
            exc,
        )
        raise AuditError(
            code="CONNECTION_ERROR",
            message="Could not connect to the URL. Check that it exists and is reachable.",
        ) from exc

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    content_type = response.headers.get("content-type")
    body = response.text if _is_html(content_type) else ""

    data = AuditData(
        url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        response_time_ms=elapsed_ms,
        title=extract_title(body) if body else None,
        meta_description=extract_meta_description(body) if body else None,
        content_type=content_type,
        is_https=is_https(str(response.url)),
        cached=False,
    )
    set_cached(url, data)
    logger.info(
        "request_id=%s audit_success url=%s status=%s time_ms=%s",
        get_request_id(),
        url,
        data.status_code,
        data.response_time_ms,
    )
    return data


def _is_html(content_type: str | None) -> bool:
    if not content_type:
        return False
    return "text/html" in content_type.lower()
