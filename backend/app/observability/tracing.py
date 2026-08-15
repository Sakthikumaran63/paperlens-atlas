"""
Request Tracing Context
-----------------------
Provides contextual request IDs and user context across asynchronous spans.
"""
import uuid
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_current_request_id() -> str:
    rid = request_id_ctx.get()
    if not rid:
        rid = str(uuid.uuid4())
        request_id_ctx.set(rid)
    return rid


def set_current_request_id(request_id: str) -> None:
    request_id_ctx.set(request_id)
