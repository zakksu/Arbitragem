"""Optional HTTP Basic auth for HTMX blackboard (3.0 GA VPS)."""

from __future__ import annotations

import base64
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.config import get_settings


class BoardAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/board"):
            return await call_next(request)

        settings = get_settings()
        if not settings.board_auth_enabled or not settings.board_password:
            return await call_next(request)

        # Local dev: skip basic-auth popup loops (use admin/admin on public tunnel only)
        host = (request.client.host if request.client else "") or ""
        if host in ("127.0.0.1", "::1", "localhost"):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode("utf-8")
                user, _, pwd = decoded.partition(":")
                if secrets.compare_digest(user, settings.board_username) and secrets.compare_digest(
                    pwd, settings.board_password
                ):
                    return await call_next(request)
            except Exception:
                pass

        return Response(
            "Board authentication required",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Arbitragem Board"'},
        )
