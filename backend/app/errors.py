"""One error format for every endpoint: {"error": {"code": "...", "message": "..."}}.

The frontend relies on `code` to show the right explanation, so codes are stable;
messages are for humans and may change.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("nexus.errors")


class NexusError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def not_found(what: str) -> NexusError:
    return NexusError("NOT_FOUND", f"{what} not found.", 404)


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


_HTTP_CODES = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NexusError)
    async def _nexus(_: Request, exc: NexusError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
        return error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        message = f"{where}: {first.get('msg', 'invalid value')}" if where else first.get("msg", "Invalid request.")
        return error_response(422, "VALIDATION_ERROR", message)

    @app.exception_handler(OperationalError)
    async def _database_down(_: Request, exc: OperationalError) -> JSONResponse:
        # Connection-level database failure (DB stopped, network down, bad credentials).
        log.error("Database unavailable: %s", exc.orig.__class__.__name__ if exc.orig else exc.__class__.__name__)
        return error_response(503, "DATABASE_UNAVAILABLE", "The NEXUS database is not reachable. Try again shortly.")

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Log the full traceback on the server, but never leak internals to the client.
        log.exception("Unhandled error", exc_info=exc)
        return error_response(500, "INTERNAL_ERROR", "Unexpected server error.")
