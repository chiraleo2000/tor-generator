"""Focused tests for POST /api/v1/analyze and per-section web sources."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db
from app.main import app
from app.models.user import User
from app.services.tor_analysis import AnalyzerFinding, PartScore, TorAnalysisResult
from app.services.web_search import HARD_MAX_RESULTS, HARD_MIN_RESULTS, WebSource
from app.api.v1.endpoints.analyze import (
    PREFER_LEGAL_CORPUS,
    collect_section_recommendations,
    source_conflicts_with_legal_kb,
)


def _user(role: str = "officer") -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = role
    user.email = "officer@example.go.th"
    user.name = "Officer"
    return user


def _client(user: User | None = None) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: user or _user()

    async def mock_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = mock_db
    return TestClient(app, raise_server_exceptions=False)


def _result_with_sections() -> TorAnalysisResult:
    legal = PartScore(
        key="legal",
        label="ส่วนที่คาดว่าผิดกฎหมาย",
        score=70,
        explanation="หักจากค่าปรับ",
        findings=[
            AnalyzerFinding(
                source_quote="ค่าปรับร้อยละ 5 ต่อวัน",
                reason="อัตราค่าปรับอยู่นอกช่วง 0.01–0.20",
                suggested_text="กำหนดค่าปรับร้อยละ 0.10 ต่อวัน และไม่ต่ำกว่า 100 บาทต่อวัน",
                section_key="s10",
                legal_basis="ระเบียบกระทรวงการคลัง พ.ศ. 2560",
            )
        ],
    )
    lock_in = PartScore(
        key="lock_in",
        label="ความเสี่ยง lock specs",
        score=60,
        explanation="หักจาก Oracle",
        findings=[
            AnalyzerFinding(
                source_quote="ต้องใช้ฐานข้อมูล Oracle Processor",
                reason="การเจาะจงผลิตภัณฑ์โดยไม่มีหรือเทียบเท่า",
                suggested_text="ระบุความต้องการเชิงหน้าที่ หรือเพิ่มข้อความ หรือเทียบเท่า",
                section_key="s4",
            )
        ],
    )
    project = PartScore(
        key="project",
        label="ความเสี่ยงบริหารโครงการ",
        score=80,
        explanation="ไม่พบประเด็น",
        findings=[],
    )
    return TorAnalysisResult(
        legal=legal,
        lock_in=lock_in,
        project=project,
        total=70,
        summary="ความเสี่ยง lock specs ดึงคะแนนลง",
    )


def _sources(count: int, *, snippet: str = "แนวทางร่าง TOR ภาครัฐ") -> list[WebSource]:
    return [
        WebSource(
            title=f"แหล่ง {index + 1}",
            url=f"https://example.go.th/tor/{index + 1}",
            snippet=snippet,
            published="2024-01-01",
        )
        for index in range(count)
    ]


def test_source_conflicts_when_penalty_rate_differs() -> None:
    rag = "กำหนดค่าปรับร้อยละ 0.10 ต่อวัน ตามระเบียบกระทรวงการคลัง พ.ศ. 2560"
    snippet = "บางหน่วยงานกำหนดค่าปรับร้อยละ 1 ต่อวัน ตามระเบียบกระทรวงการคลัง"
    assert source_conflicts_with_legal_kb(snippet, rag) is True


def test_source_does_not_conflict_when_rates_match() -> None:
    rag = "กำหนดค่าปรับร้อยละ 0.10 ต่อวัน ตามระเบียบกระทรวงการคลัง พ.ศ. 2560"
    snippet = "ระเบียบกระทรวงการคลังกำหนดค่าปรับร้อยละ 0.10 ต่อวัน"
    assert source_conflicts_with_legal_kb(snippet, rag) is False


@pytest.mark.asyncio
async def test_recommendations_include_five_to_ten_sources_per_section() -> None:
    calls: list[str] = []

    async def fake_search(query: str, *, limit: int | None = None) -> list[WebSource]:
        calls.append(query)
        return _sources(8)

    with patch("app.api.v1.endpoints.analyze.search_web", new=fake_search):
        rows = await collect_section_recommendations(_result_with_sections(), rag_text="")

    assert len(calls) == 2
    assert {row["section_key"] for row in rows} == {"s4", "s10"}
    for row in rows:
        assert HARD_MIN_RESULTS <= row["source_count"] <= HARD_MAX_RESULTS
        assert row["source_count"] == 8
        assert "พบ 8 แหล่ง" in row["source_count_note"]
        assert row["sources"]
        for suggestion in row["suggestions"]:
            assert suggestion["suggested_text"]
            assert suggestion["source_count"] == 8
            assert len(suggestion["sources"]) == 8


@pytest.mark.asyncio
async def test_recommendations_state_actual_count_when_below_five() -> None:
    async def fake_search(query: str, *, limit: int | None = None) -> list[WebSource]:
        return _sources(3)

    with patch("app.api.v1.endpoints.analyze.search_web", new=fake_search):
        rows = await collect_section_recommendations(_result_with_sections(), rag_text="")

    for row in rows:
        assert row["source_count"] == 3
        assert "น้อยกว่า 5" in row["source_count_note"]
        assert len(row["sources"]) == 3


@pytest.mark.asyncio
async def test_conflicting_web_source_prefers_legal_corpus() -> None:
    rag = "กำหนดค่าปรับร้อยละ 0.10 ต่อวัน ตามระเบียบกระทรวงการคลัง พ.ศ. 2560"

    async def fake_search(query: str, *, limit: int | None = None) -> list[WebSource]:
        if "ค่าปรับ" in query:
            return _sources(5, snippet="ค่าปรับร้อยละ 1 ต่อวัน ตามระเบียบกระทรวงการคลัง")
        return _sources(5)

    with patch("app.api.v1.endpoints.analyze.search_web", new=fake_search):
        rows = await collect_section_recommendations(_result_with_sections(), rag_text=rag)

    penalty = next(row for row in rows if row["section_key"] == "s10")
    assert penalty["prefer_legal_corpus"] is True
    assert PREFER_LEGAL_CORPUS in penalty["legal_corpus_note"]
    assert any(item["conflicts_with_legal_kb"] for item in penalty["sources"])


def test_analyze_endpoint_returns_sources_per_revised_section() -> None:
    client = _client()
    text = (
        "1. ความเป็นมา\n"
        "ตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ "
        "พ.ศ. 2560 และระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้าง"
        "และการบริหารพัสดุภาครัฐ พ.ศ. 2560\n"
        "4. ขอบเขตของงาน\n"
        "ต้องใช้ฐานข้อมูล Oracle Processor license บนเครื่อง Exadata "
        "และบังคับ hard partitioning ผ่าน Integrated Virtualization Manager "
        "โดยไม่มีข้อความหรือเทียบเท่า พร้อมส่งมอบผลงานส่งมอบรายงานและระบบ\n"
        "10. ค่าปรับ\n"
        "ค่าปรับร้อยละ 5 ต่อวัน"
    )

    async def fake_search(query: str, *, limit: int | None = None) -> list[WebSource]:
        return _sources(7)

    async def empty_law(_project_type: str | None = None) -> str:
        return ""

    with (
        patch("app.api.v1.endpoints.analyze.search_web", new=fake_search),
        patch("app.api.v1.endpoints.analyze._law_context", new=empty_law),
    ):
        response = client.post("/api/v1/analyze", json={"text": text})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert "legal" in data
    assert "lock_in" in data
    assert "project" in data
    recommendations = data["recommendations"]
    assert recommendations
    for row in recommendations:
        assert HARD_MIN_RESULTS <= row["source_count"] <= HARD_MAX_RESULTS
        assert row["source_count"] == 7
        assert row["suggestions"]
        assert all(item.get("suggested_text") for item in row["suggestions"])


def test_analyze_endpoint_requires_text_or_project() -> None:
    client = _client()
    response = client.post("/api/v1/analyze", json={})
    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["ok"] is False
