import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS
from app.logger import get_request_id, logger, request_id_var
from app.models import ErrorDetail, ErrorResponse

_client_hits: dict[str, deque[float]] = defaultdict(deque)


def clear_rate_limits() -> None:
    _client_hits.clear()


def _client_key(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "request_id=%s method=%s endpoint=%s status_code=%s execution_time_ms=%s",
                request_id,
                request.method,
                request.url.path,
                500,
                duration_ms,
            )
            raise
        finally:
            request_id_var.reset(token)

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s endpoint=%s status_code=%s execution_time_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limit incoming requests per client IP. Separate from outbound concurrency."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.url.path != "/audit" or request.method != "POST":
            return await call_next(request)

        client = _client_key(request)
        now = time.monotonic()
        window = _client_hits[client]
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS

        while window and window[0] <= cutoff:
            window.popleft()

        if len(window) >= RATE_LIMIT_REQUESTS:
            logger.warning(
                "request_id=%s rate_limited client=%s",
                get_request_id(),
                client,
            )
            body = ErrorResponse(
                error=ErrorDetail(
                    code="RATE_LIMITED",
                    message=(
                        f"Rate limit exceeded: max {RATE_LIMIT_REQUESTS} requests "
                        f"per {RATE_LIMIT_WINDOW_SECONDS} seconds"
                    ),
                ),
            )
            return JSONResponse(status_code=429, content=body.model_dump())

        window.append(now)
        return await call_next(request)
