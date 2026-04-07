from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ai_stock_agent.adapters.inbound.schemas import (
    InvocationRequest,
    InvocationResponse,
    PingResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_use_case(request: Request) -> Any:
    use_case = getattr(request.app.state, "use_case", None)
    if use_case is None:
        raise HTTPException(status_code=503, detail="Agent not initialised")
    return use_case


def _get_langfuse_handler(request: Request) -> Any | None:
    factory = getattr(request.app.state, "langfuse_factory", None)
    if factory is None:
        return None
    return factory()


async def _sse_generator(token_iter: AsyncIterator[str]) -> AsyncIterator[str]:
    """Wrap an async token iterator into SSE-formatted lines."""
    try:
        async for token in token_iter:
            payload = json.dumps({"type": "token", "content": token})
            yield f"data: {payload}\n\n"
    except Exception:
        logger.exception("Error during SSE streaming")
        error = json.dumps({"type": "error", "content": "Internal streaming error"})
        yield f"data: {error}\n\n"
    finally:
        yield f"data: {json.dumps({'type': 'end'})}\n\n"


@router.get("/ping", response_model=PingResponse)
async def ping() -> PingResponse:
    return PingResponse()


@router.post("/invocations")
async def invocations(body: InvocationRequest, request: Request):
    use_case = _get_use_case(request)

    thread_id = body.thread_id or str(uuid.uuid4())

    langfuse_handler = _get_langfuse_handler(request)
    callbacks = [langfuse_handler] if langfuse_handler else []

    try:
        result = await use_case.invoke(
            prompt=body.prompt,
            thread_id=thread_id,
            stream=body.stream,
            callbacks=callbacks,
        )
    except Exception:
        logger.exception("Agent invocation failed")
        raise HTTPException(status_code=500, detail="Agent invocation failed")

    if body.stream:
        return StreamingResponse(
            _sse_generator(result),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Thread-Id": thread_id,
            },
        )

    return InvocationResponse(response=result, thread_id=thread_id)
