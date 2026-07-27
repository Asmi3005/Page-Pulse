from typing import Literal

from pydantic import BaseModel, HttpUrl


class AuditRequest(BaseModel):
    url: HttpUrl


class AuditData(BaseModel):
    url: str
    final_url: str
    status_code: int
    response_time_ms: float
    title: str | None
    meta_description: str | None
    content_type: str | None
    is_https: bool
    cached: bool = False


class AuditResponse(BaseModel):
    success: Literal[True] = True
    data: AuditData


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    error: ErrorDetail
