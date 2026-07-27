from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models import AuditRequest, AuditResponse, ErrorResponse
from app.service import AuditError, audit_url

router = APIRouter()

ERROR_STATUS_CODES = {
    "INVALID_URL": 400,
    "TIMEOUT": 408,
    "CONNECTION_ERROR": 502,
    "RATE_LIMITED": 429,
}


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/audit",
    response_model=AuditResponse,
    responses={
        400: {"model": ErrorResponse},
        408: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def audit(request: AuditRequest) -> AuditResponse | JSONResponse:
    try:
        data = await audit_url(str(request.url))
        return AuditResponse(data=data)
    except AuditError as exc:
        status_code = ERROR_STATUS_CODES.get(exc.detail.code, 500)
        return JSONResponse(
            status_code=status_code,
            content=ErrorResponse(error=exc.detail).model_dump(),
        )


@router.get("/")
async def root() -> dict[str, str]:
    return {"service": "Page Pulse", "audit": "POST /audit"}
