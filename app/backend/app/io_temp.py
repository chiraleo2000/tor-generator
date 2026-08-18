"""Async wrappers around short synchronous tempfile writes."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path


async def write_temp_bytes(data: bytes, suffix: str) -> str:
    """Write bytes to a NamedTemporaryFile without blocking the event loop."""

    def _write() -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            return tmp.name

    return await asyncio.to_thread(_write)


async def unlink_path(path: str) -> None:
    await asyncio.to_thread(Path(path).unlink, missing_ok=True)
