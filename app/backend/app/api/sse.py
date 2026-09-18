"""Shared Server-Sent Event response helpers."""

from collections.abc import AsyncIterator

from starlette.responses import StreamingResponse

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def sse_streaming_response(body: AsyncIterator[str]) -> StreamingResponse:
    """Return an unbuffered text/event-stream response."""
    return StreamingResponse(
        body,
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
