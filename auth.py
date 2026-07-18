from __future__ import annotations

import base64
import hmac

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings


class OptionalBasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.app_username or not settings.app_password:
            return await call_next(request)

        if request.url.path == "/health":
            return await call_next(request)

        header = request.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
                username, password = decoded.split(":", 1)
                user_ok = hmac.compare_digest(username, settings.app_username)
                pass_ok = hmac.compare_digest(password, settings.app_password)
                if user_ok and pass_ok:
                    return await call_next(request)
            except (ValueError, UnicodeDecodeError, base64.binascii.Error):
                pass

        return Response(
            content="Autenticação necessária",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Cretino Factory"'},
        )
