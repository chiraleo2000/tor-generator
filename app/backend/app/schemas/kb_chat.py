"""Pydantic schemas for knowledge-base chat."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class CreateKBChatSessionResponse(BaseModel):
    session_id: uuid.UUID


class KBChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class KBChatMessageResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    no_results: bool = False


class KBChatHistoryResponse(BaseModel):
    messages: list[dict[str, Any]] = Field(default_factory=list)
