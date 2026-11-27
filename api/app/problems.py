"""RFC 7807 problem responses."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from layersight.config.adapter import ConfigError


class Problem(Exception):
    def __init__(
        self,
        status: int,
        title: str,
        detail: str,
        errors: list[dict[str, str]] | None = None,
    ) -> None:
        self.status = status
        self.title = title
        self.detail = detail
        self.errors = errors or []


def problem_body(
    *,
    status: int,
    title: str,
    detail: str,
    errors: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
    }
    if errors:
        body["errors"] = errors
    return body


def _response(status: int, title: str, detail: str, errors: list[dict[str, str]] | None = None) -> JSONResponse:
    return JSONResponse(
        problem_body(status=status, title=title, detail=detail, errors=errors),
        status_code=status,
        media_type="application/problem+json",
    )


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(Problem)
    async def handle_problem(_request: Request, exc: Problem) -> JSONResponse:
        return _response(exc.status, exc.title, exc.detail, exc.errors)

    @app.exception_handler(ConfigError)
    async def handle_config(_request: Request, exc: ConfigError) -> JSONResponse:
        return _response(422, "Invalid layer configuration", exc.detail, exc.fields)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(part) for part in error.get("loc", ()) if part != "body"),
                "message": str(error.get("msg", "invalid")),
            }
            for error in exc.errors()
        ]
        return _response(422, "Invalid request", "The request body is not valid.", errors)

    @app.exception_handler(HTTPException)
    async def handle_http(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return _response(exc.status_code, "Request failed", detail)
