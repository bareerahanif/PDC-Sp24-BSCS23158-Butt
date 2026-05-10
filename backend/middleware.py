# backend/middleware.py
# BSCS23157 - PDC Assignment 02
# Custom middleware: injects X-Student-ID into every response header

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class StudentHeaderMiddleware(BaseHTTPMiddleware):
    STUDENT_ID = "BSCS23158"

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Student-ID"] = self.STUDENT_ID
        return response
