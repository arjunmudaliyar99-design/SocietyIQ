"""API errors carry a code and an i18n key so the front end can translate (docs/04 §3)."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message_key: str) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.message_key = message_key


def not_found() -> AppError:
    # Also used for "exists but not yours", so another society's ids are not confirmed.
    return AppError(404, "NOT_FOUND", "errors.notFound")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message_key": exc.message_key}},
        )
