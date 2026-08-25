"""JSON schemas for SGLang guided generation (analyze / review / graph)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class IntakeSlot(BaseModel):
    content: str = ""
    status: Literal["filled", "gap", "reference_only"] = "gap"
    sources: list[str] = Field(default_factory=list)


class IntakeAnalyzeResult(BaseModel):
    slot_map: dict[str, IntakeSlot] = Field(default_factory=dict)
    gap_questions: list[str] = Field(default_factory=list)


class GapQuestionsResult(BaseModel):
    questions: list[str] = Field(default_factory=list)


class IncrementalTarget(BaseModel):
    slot_key: str
    content: str = ""
    action: Literal["append", "replace"] = "append"


class IncrementalClassifyResult(BaseModel):
    targets: list[IncrementalTarget] = Field(default_factory=list)


class ReviewSuggestionItem(BaseModel):
    category: Literal["compliance", "clarity", "completeness", "consistency"]
    section_key: str
    current_text: str = ""
    suggested_text: str = ""
    predicted_score_improvement: float = 1.0


class ReviewSuggestionsResult(BaseModel):
    suggestions: list[ReviewSuggestionItem] = Field(default_factory=list)


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    label: Literal["Document", "Law", "Article", "TorSlot", "Concept"]
    name: str = ""


class GraphRel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    from_id: str = Field(alias="from")
    to: str
    type: Literal["CONTAINED_IN", "CITES", "APPLIES_TO", "DEFINES", "SUPERSEDES"]


class GraphExtractResult(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    rels: list[GraphRel] = Field(default_factory=list)


def json_schema_for(model: type[BaseModel]) -> dict[str, Any]:
    return model.model_json_schema()
