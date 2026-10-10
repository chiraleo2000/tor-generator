"""Helpers extracted during the complexity split, covered without a live model."""

from types import SimpleNamespace
import pytest

from app.domain.consultant_budget import (
    _person_profession,
    _sector_name,
    _sentence_meal_mismatch,
    budget_rule_findings,
    suggest_budget,
)
from app.domain.tor_draft_hints import _load_category_hints, category_hints_available, hint_for
from app.orchestrator.agents.base import (
    _append_current_draft,
    _append_rag_context,
    _append_template_guidance,
    _append_validation_findings,
    _project_intake_text,
)
from app.providers.llm.gemini_provider import (
    GeminiLLMProvider,
    _fallback_slices,
    _gemini_part_texts,
    _raise_for_gemini_status,
    _reject_http_status,
    _status_code,
    _stream_retry_kwargs,
    gemini_output_token_rejected,
)
from app.providers.base import LLMResponse
from app.providers.model_capabilities import _chat_model, _embedding_model, _setting_or_default


def test_budget_and_hint_edges(monkeypatch, tmp_path):
    assert _sector_name("สถาบันของรัฐ") == "state"
    assert _sector_name("firm") == "private"
    assert _person_profession({}, "วิศวกร") == "วิศวกร"
    assert _person_profession({"profession": "นักวิเคราะห์"}, "วิศวกร") == "นักวิเคราะห์"
    with pytest.raises(TypeError):
        suggest_budget(not_a_budget_field=1)
    assert _sentence_meal_mismatch("ครึ่งวันและเต็มวัน อาหาร 3 มื้อ อาหารว่าง 1 มื้อ")
    assert _sentence_meal_mismatch("ครึ่งวัน อาหาร 1 มื้อ อาหารว่าง 1 มื้อ") is False
    findings = budget_rule_findings("ครึ่งวัน อาหาร 3 มื้อ และอาหารว่าง 1 มื้อสำหรับผู้เข้าอบรม")
    assert any(item["rule_id"] == "training_meal_mismatch" for item in findings)
    missing = tmp_path / "category_hints.json"
    monkeypatch.setattr(
        "app.domain.tor_draft_hints.Path.with_name",
        lambda self, name: missing if name == "category_hints.json" else self.with_name(name),
    )
    _load_category_hints.cache_clear()
    try:
        assert _load_category_hints() == {}
        assert category_hints_available(None) is False
        assert isinstance(hint_for("s1"), str)
    finally:
        _load_category_hints.cache_clear()


def test_prompt_and_model_helpers():
    parts: list[str] = []
    _append_current_draft(parts, "nope")
    _append_current_draft(parts, {"s1": "  ", "s2": ""})
    _append_current_draft(parts, {"s1": "ร่าง"})
    assert any("ร่าง" in part for part in parts)
    _append_rag_context(parts, [])
    _append_rag_context(parts, [{"source_document": "พรบ", "text": "มาตรา 1"}])
    assert any("พรบ" in part for part in parts)
    _append_template_guidance(parts, None, "s1")
    _append_template_guidance(parts, {"placeholder_guidance": {}}, "s1")
    _append_template_guidance(parts, {"placeholder_guidance": {"s1": "เขียนเหตุผล"}}, "s1")
    _append_validation_findings(parts, None)
    _append_validation_findings(
        parts,
        [{"severity": "error", "message": "ขาดงบ", "recommended_correction": "ใส่ตัวเลข"}],
    )
    assert _project_intake_text("nope") == ""
    assert _project_intake_text({"_project_intake": "เอกสาร"}) == "เอกสาร"
    assert _project_intake_text({"slot_map": {"_project_intake": {"content": "จากสล็อต"}}}) == "จากสล็อต"
    settings = SimpleNamespace(
        sglang_model="",
        lm_studio_model="local-chat",
        openai_chat_model="",
        lm_studio_embedding_model="local-embed",
        openai_embedding_model="",
    )
    assert _setting_or_default(settings, "missing", "fallback") == "fallback"
    assert _chat_model("sglang", settings) == "local-chat"
    assert _chat_model("unknown", settings) == "local-chat"
    assert _embedding_model("openai", settings) == "text-embedding-3-small"
    assert "local-embed" in _embedding_model("local", settings)


def test_gemini_status_retry_and_fallback():
    assert _gemini_part_texts("nope") == []
    assert _gemini_part_texts({"content": {"parts": ["x", {"text": ""}, {"text": "ก"}]}}) == ["ก"]
    assert gemini_output_token_rejected("max output tokens")
    bad = SimpleNamespace(status_code="nope", text="body")
    assert _status_code(bad) == 200
    _reject_http_status(SimpleNamespace(status_code=200, text=""))
    unavailable = SimpleNamespace(status_code=503, text="down")
    with pytest.raises(ConnectionError):
        _reject_http_status(unavailable)
    kwargs = {"max_tokens": 16000}
    error = ConnectionError("maxOutputTokens is too large")
    retried = _stream_retry_kwargs(1, error, kwargs)
    assert retried is not None
    assert retried["max_tokens"] == 8192
    assert _stream_retry_kwargs(2, error, kwargs) is None


async def test_gemini_status_read_and_stream_fallback(monkeypatch):
    class _Response:
        status_code = 500
        text = "plain"

        async def aread(self):
            return "ไม่ใช่ไบต์".encode()

    failed = _Response()
    with pytest.raises(ConnectionError):
        await _raise_for_gemini_status(failed)

    class _Broken:
        status_code = 502
        text = "from-text"

        async def aread(self):
            raise RuntimeError("unread")

    broken = _Broken()
    with pytest.raises(ConnectionError):
        await _raise_for_gemini_status(broken)

    provider = GeminiLLMProvider(api_key="fake", model_name="gemini-test")

    async def _boom(*_args, **_kwargs):
        raise ConnectionError("maxOutputTokens rejected")
        yield ""  # pragma: no cover

    monkeypatch.setattr(provider, "_stream_sse", _boom)

    async def _invoke(_messages, **_kwargs):
        return LLMResponse(content="ก" * 130, model="m", usage={}, finish_reason="stop")

    monkeypatch.setattr(provider, "invoke", _invoke)
    pieces = [piece async for piece in provider.stream([{"role": "user", "content": "ถาม"}], max_tokens=9000)]
    assert "".join(pieces).startswith("ก")
    empty = [piece async for piece in _fallback_slices(LLMResponse(content="", model="m", usage={}, finish_reason="stop"))]
    assert empty == []


def test_drafting_revision_and_wrong_owner_draft():
    from app.api.v1.endpoints.drafting import (
        _apply_revision_instruction,
        _copy_intake_fields,
        _discard_wrong_owner_draft,
        _license_table_source,
    )

    user_input = {"user_feedback": "ให้สั้นลง", "revision_instruction": "เดิม"}
    _apply_revision_instruction(user_input)
    assert user_input["redraft"] is True
    assert "ให้สั้นลง" in user_input["revision_instruction"]
    forced = {"redraft": True, "revision_instruction": ""}
    _apply_revision_instruction(forced)
    assert "ร่างใหม่" in forced["revision_instruction"]
    copied: dict = {}
    _copy_intake_fields(
        copied,
        {
            "_project_intake": {"content": "เอกสารขั้นที่ ๐"},
            "s4": {"content": "ขอบเขต", "status": "filled", "sources": ["ไฟล์"]},
        },
        "s4",
    )
    assert copied["_project_intake"] == "เอกสารขั้นที่ ๐"
    string_intake: dict = {}
    _copy_intake_fields(string_intake, {"_project_intake": " ข้อความ "}, "s1")
    assert string_intake["_project_intake"] == " ข้อความ "
    prior, feedback = _discard_wrong_owner_draft(
        "licenses",
        "s4.licenses",
        "ลิขสิทธิ์",
        "ขอบเขตและวิธีการดำเนินงานทั้งหมวด",
        {},
        "",
    )
    assert prior == ""
    assert "ร่างเดิมผิดหัวข้อ" in feedback
    kept, same = _discard_wrong_owner_draft("functional", "s4.functional", "งาน", "งานฟังก์ชัน", {}, "คงไว้")
    assert kept == "งานฟังก์ชัน"
    assert same == "คงไว้"
    source = _license_table_source(
        "licenses",
        "licenses",
        "ขอบเขตและวิธีการดำเนินงาน",
        "",
        {"licenses": {"content": "ตารางสิทธิ์จากเอกสาร", "status": "filled"}},
    )
    assert "ตารางสิทธิ์" in source
