"""エラーを 5.2 の共通の形 {"error": {"code", "message", ("fields")}} で返す。

401 は2種類(DP-52): UNAUTHORIZED(内部キー・IDトークンが違う)と LOGIN_REQUIRED(保護APIを未ログインで呼んだ)。
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# Pydantic のエラーの種類 → fields の reason(5.2 の例 "too_long" に合わせる)
_REASONS = {"missing": "required", "string_too_long": "too_long", "string_too_short": "too_short"}
_LIMIT_KEYS = {"too_long": "max_length", "too_short": "min_length"}


class ApiError(Exception):
    """extra: error の中に足す項目(A06 の missing_question_nos など)。"""
    def __init__(self, status: int, code: str, message: str, fields: list | None = None,
                 extra: dict | None = None):
        self.status, self.code, self.message, self.fields, self.extra = status, code, message, fields, extra


def _response(status: int, code: str, message: str, fields: list | None = None,
              extra: dict | None = None) -> JSONResponse:
    error = {"code": code, "message": message}
    if fields is not None:
        error["fields"] = fields
    if extra:
        error.update(extra)
    return JSONResponse({"error": error}, status_code=status)


def _field(err: dict) -> dict:
    # 取り除くのは先頭のリクエスト種別だけ(本文に path などという項目があっても消さない)
    loc = list(err["loc"])
    if loc and loc[0] in ("body", "query", "path", "header"):
        loc = loc[1:]
    loc = [str(p) for p in loc]
    reason = _REASONS.get(err["type"], "invalid")
    field = {"field": ".".join(loc), "reason": reason}
    if reason in _LIMIT_KEYS:
        # 文字数は len() で数える(MySQL の VARCHAR・画面の [...text].length とそろう。11.3)
        field["limit"] = err["ctx"][_LIMIT_KEYS[reason]]
        field["actual"] = len(err["input"])
    return field


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return _response(exc.status, exc.code, exc.message, exc.fields, exc.extra)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return _response(404, "NOT_FOUND", "見つかりません")
        return _response(exc.status_code, "BAD_REQUEST", "リクエストの形が違います")

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        errors = exc.errors()
        if any(e["type"] == "json_invalid" for e in errors):
            return _response(400, "BAD_REQUEST", "リクエストの形が違います")
        return _response(422, "VALIDATION_ERROR", "入力に誤りがあります", [_field(e) for e in errors])

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        # 中身(DBのエラー文など)は返さず、サーバーのログにだけ残す
        logger.exception("想定外のエラー: %s %s", request.method, request.url.path)
        return _response(500, "INTERNAL_ERROR", "サーバーで問題が起きました")
