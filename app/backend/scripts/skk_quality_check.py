"""Live SKK pack quality check against Docker API + LM Studio."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
from docx import Document

API = "http://127.0.0.1:4000"
EMAIL = "officer@example.go.th"
PASSWORD = "Passw0rd!"
SKK = Path(r"C:\Users\chira\Downloads\สกก. edit1.docx")
OLD = Path(r"C:\Users\chira\Downloads\TOR (4).docx")
OUT_DIR = Path(__file__).resolve().parents[3] / "Discussions" / "test-evidence"
SECTIONS = ("s1", "s5", "s8", "s11")
SCAFFOLD = (
    "ประวัติ/สถานการณ์ปัจจุบันของระบบเดิม",
    "ปัญหาที่พบ (ระบุตัวเลข/สถิติ)",
    "### history",
    "### problems",
)
ENGLISH = (
    "Server",
    "Cyber Attack",
    "Digital Government",
    "Big Data",
    "Public AI",
    "Deliverables",
    "Price-Performance",
    "Price Only",
)


def _step(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def _data(response: httpx.Response) -> dict:
    body = response.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"] or {}
    return body if isinstance(body, dict) else {}


def _login(client: httpx.Client) -> None:
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    response.raise_for_status()
    token = _data(response).get("token")
    if token:
        client.headers["Authorization"] = f"Bearer {token}"


def _scan_docx(path: Path) -> dict:
    doc = Document(str(path))
    text = "\n".join(p.text for p in doc.paragraphs)
    section = doc.sections[0]
    normal = doc.styles["Normal"]
    return {
        "chars": len(text),
        "has_background_title": "ความเป็นมา" in text,
        "has_numbered_thai_heading": "๑. ความเป็นมา" in text,
        "has_arabic_heading": "1. ความเป็นมา" in text,
        "scaffold": [item for item in SCAFFOLD if item in text],
        "english": [item for item in ENGLISH if item in text],
        "has_payment_table": "งวดที่" in text and "ร้อยละ" in text,
        "font_pt": float(normal.font.size.pt) if normal.font.size else None,
        "line_spacing": normal.paragraph_format.line_spacing,
        "left_cm": round(section.left_margin.cm, 2) if section.left_margin else None,
        "top_cm": round(section.top_margin.cm, 2) if section.top_margin else None,
        "sample": text[:1200],
    }


def _wait_healthy(client: httpx.Client) -> None:
    for _ in range(30):
        try:
            health = client.get("/health", timeout=5.0)
            if health.status_code == 200:
                return
        except httpx.HTTPError:
            time.sleep(2)
    raise SystemExit("API not healthy")


def _create_project(client: httpx.Client) -> str:
    created = client.post(
        "/api/v1/projects",
        json={
            "name": f"SKK quality {datetime.now():%H%M%S}",
            "ministry": "สำนักงานเศรษฐกิจการเกษตร",
            "budget": 5_730_000,
            "project_type": "hire_develop",
        },
    )
    created.raise_for_status()
    return str(_data(created)["id"])


def _intake_pack(client: httpx.Client, project_id: str) -> list[str]:
    raw = SKK.read_bytes()
    uploaded = client.post(
        f"/api/v1/projects/{project_id}/intake/upload",
        files={
            "files": (
                "skk-edit1.docx",
                raw,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    uploaded.raise_for_status()
    _step("uploaded SKK pack")
    analyzed = client.post(f"/api/v1/projects/{project_id}/intake/analyze")
    analyzed.raise_for_status()
    coverage = _data(analyzed).get("coverage") or []
    filled = [
        row.get("key")
        for row in coverage
        if row.get("filled") or row.get("status") == "filled"
    ]
    _step(f"analyze filled {len(filled)}/{len(coverage)} {filled[:12]}")
    refs = client.post(f"/api/v1/projects/{project_id}/intake/fill-references")
    _step(f"fill-references {refs.status_code}")
    if refs.status_code != 200:
        _step(refs.text[:400])
        refs.raise_for_status()
    ready = client.post(
        f"/api/v1/projects/{project_id}/intake/confirm-ready",
        json={"confirm": True},
    )
    ready.raise_for_status()
    return filled


def _draft_sections(client: httpx.Client, project_id: str) -> dict[str, str]:
    drafts: dict[str, str] = {}
    for key in SECTIONS:
        drafted = client.post(
            f"/api/v1/projects/{project_id}/draft-section",
            json={"section_key": key},
        )
        text = str(_data(drafted).get("draft_content") or "")
        score = _data(drafted).get("quality_score")
        drafts[key] = text
        _step(f"draft {key} status={drafted.status_code} chars={len(text)} score={score}")
        if drafted.status_code != 200:
            _step(drafted.text[:400])
            raise SystemExit(f"draft failed for {key} status={drafted.status_code}")
        if score is not None and int(score) <= 0:
            raise SystemExit(f"guardrail score 0 for {key}")
        if len(text) < 200:
            raise SystemExit(f"draft too short for {key} chars={len(text)}")
    return drafts


def _export_docx(client: httpx.Client, project_id: str) -> bytes:
    export = client.post(
        f"/api/v1/projects/{project_id}/export",
        json={"use_thai_numerals": True, "numbering_scheme": "none"},
    )
    _step(f"export start {export.status_code}")
    for _ in range(40):
        status = client.get(f"/api/v1/projects/{project_id}/export/status")
        payload = _data(status)
        _step(f"export status={payload.get('status')}")
        if payload.get("status") == "completed":
            return client.get(f"/api/v1/projects/{project_id}/export/download/docx").content
        if payload.get("status") in {"failed", "error"}:
            break
        time.sleep(3)
    return b""


def _write_report(project_id: str, drafts: dict[str, str], new_scan: dict, old_scan: dict) -> dict:
    joined = "\n".join(drafts.values())
    report = {
        "project_id": project_id,
        "chat_model": "google/gemma-4-e4b",
        "embedding_model": "text-embedding-embeddinggemma-300m",
        "thinking": "enabled",
        "old_tor4": old_scan,
        "new_export": new_scan,
        "draft_chars": {key: len(value) for key, value in drafts.items()},
        "draft_scaffold": [item for item in SCAFFOLD if item in joined],
        "draft_english": [item for item in ENGLISH if item in joined],
        "s1_sample": drafts.get("s1", "")[:800],
        "s8_sample": drafts.get("s8", "")[:800],
    }
    dest = OUT_DIR / "_round-2026-09-10-skk-quality-thinking.json"
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _step(f"wrote {dest}")
    print(json.dumps({k: report[k] for k in ("draft_scaffold", "draft_english", "new_export")}, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    old_scan = _scan_docx(OLD) if OLD.exists() else {}
    with httpx.Client(base_url=API, timeout=httpx.Timeout(1800.0, connect=30.0)) as client:
        _wait_healthy(client)
        _login(client)
        project_id = _create_project(client)
        _step(f"project {project_id}")
        _intake_pack(client, project_id)
        drafts = _draft_sections(client, project_id)
        confirm4 = client.post(
            f"/api/v1/projects/{project_id}/intake/confirm-phase4",
            json={"confirm": True},
        )
        _step(f"confirm-phase4 {confirm4.status_code}")
        docx_bytes = _export_docx(client, project_id)
        out_docx = OUT_DIR / "skk-quality-export.docx"
        if docx_bytes.startswith(b"PK"):
            out_docx.write_bytes(docx_bytes)
            new_scan = _scan_docx(out_docx)
        else:
            new_scan = {"error": "no docx", "raw_prefix": docx_bytes[:80].decode("utf-8", "replace")}
        report = _write_report(project_id, drafts, new_scan, old_scan)
        bad = bool(report["draft_scaffold"]) or bool(new_scan.get("has_arabic_heading"))
        if new_scan.get("error"):
            bad = True
        return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
