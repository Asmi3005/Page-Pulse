from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.middleware import RateLimitMiddleware, RequestContextMiddleware
from app.models import ErrorDetail, ErrorResponse
from app.routes import router

app = FastAPI(title="Page Pulse", version="1.0.0")

# Order matters: last added runs first. Request ID wraps rate limiting.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    message = "; ".join(
        f"{'.'.join(str(loc) for loc in err.get('loc', []))}: {err.get('msg')}"
        for err in exc.errors()
    )
    body = ErrorResponse(
        error=ErrorDetail(code="INVALID_URL", message=message or "Invalid request"),
    )
    return JSONResponse(status_code=400, content=body.model_dump())
