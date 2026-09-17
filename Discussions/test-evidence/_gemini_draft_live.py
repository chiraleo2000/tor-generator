"""Live Gemini hybrid check: TOR draft intake → analyze → draft s1 → project review."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

API = "http://127.0.0.1:4000"
EMAIL = "officer@example.go.th"
PASSWORD = "Passw0rd!"
OUT = Path(__file__).resolve().parent / "_gemini-draft-live.json"
GOLD = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "backend"
    / "tests"
    / "fixtures"
    / "hire_develop_gold_pack.txt"
)
STUBS = ("ชิ้นจำลอง", "custom-rag-stub", "mcp-retrieve-stub")


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def step(msg: str) -> None:
    print(f"[{_now()}] {msg}", flush=True)


def data(response: httpx.Response) -> dict:
    body = response.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"] or {}
    return body if isinstance(body, dict) else {}


def thai_count(text: str) -> int:
    return sum(1 for ch in text if "\u0e00" <= ch <= "\u0e7f")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    intake = GOLD.read_text(encoding="utf-8") if GOLD.is_file() else (
        "ความเป็นมา (s1): กรมบัญชีกลางต้องพัฒนาระบบบริหารสัญญา\n"
        "วัตถุประสงค์ (s2): ให้เจ้าหน้าที่พัสดุติดตามงวดจ่ายได้\n"
        "ระยะเวลาดำเนินการ (s5): 180 วัน\n"
        "วงเงินงบประมาณ (s6): 2,500,000 บาท\n"
        "สถานที่ดำเนินการ (s7): กรุงเทพมหานคร\n"
    )
    report: dict = {"started": datetime.now().isoformat(timespec="seconds")}
    with httpx.Client(base_url=API, timeout=httpx.Timeout(1800.0, connect=20.0)) as client:
        health = client.get("/health", timeout=10.0)
        report["health"] = health.status_code
        if health.status_code != 200:
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return 1

        login = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
        login.raise_for_status()
        client.headers["Authorization"] = f"Bearer {data(login)['token']}"
        step("login ok")

        created = client.post(
            "/api/v1/projects",
            json={
                "name": f"โครงการทดสอบ Gemini draft {datetime.now():%H%M%S}",
                "ministry": "สำนักงานปลัดกระทรวง",
                "budget": 5000000,
                "project_type": "hire_develop",
            },
            timeout=30.0,
        )
        if created.status_code not in {200, 201}:
            report["create"] = {"ok": False, "status": created.status_code, "body": created.text[:800]}
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return 1
        project_id = data(created)["id"]
        report["project_id"] = project_id
        step(f"project {project_id}")

        pasted = client.post(
            f"/api/v1/projects/{project_id}/intake/text",
            json={"content": intake},
            timeout=180.0,
        )
        report["intake_text"] = {"status": pasted.status_code}
        if pasted.status_code != 200:
            report["ok"] = False
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return 1
        step("intake text ok")

        analyzed = client.post(
            f"/api/v1/projects/{project_id}/intake/analyze",
            timeout=httpx.Timeout(900.0, connect=20.0),
        )
        analysis = data(analyzed) if analyzed.status_code == 200 else {}
        coverage = analysis.get("coverage") or []
        filled = [row for row in coverage if row.get("filled") or row.get("status") == "filled"]
        report["analyze"] = {
            "ok": analyzed.status_code == 200 and bool(coverage),
            "status": analyzed.status_code,
            "filled": len(filled),
            "body": analyzed.text[:800] if analyzed.status_code != 200 else None,
        }
        step(f"analyze filled={len(filled)} ok={report['analyze']['ok']}")
        if not report["analyze"]["ok"]:
            report["ok"] = False
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return 1

        refs = client.post(
            f"/api/v1/projects/{project_id}/intake/fill-references",
            timeout=httpx.Timeout(900.0, connect=20.0),
        )
        report["fill_references"] = {"ok": refs.status_code == 200, "status": refs.status_code}
        step(f"fill-references ok={report['fill_references']['ok']}")
        if not report["fill_references"]["ok"]:
            report["ok"] = False
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return 1

        ready = client.post(
            f"/api/v1/projects/{project_id}/intake/confirm-ready",
            json={"confirm": True},
            timeout=30.0,
        )
        ready_payload = data(ready) if ready.status_code == 200 else {}
        report["confirm_ready"] = {
            "ok": ready.status_code == 200 and ready_payload.get("ready_to_compose") is True,
            "status": ready.status_code,
        }
        step(f"confirm-ready ok={report['confirm_ready']['ok']}")
        if not report["confirm_ready"]["ok"]:
            report["ok"] = False
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return 1

        drafted = None
        draft = ""
        for attempt in range(1, 4):
            drafted = client.post(
                f"/api/v1/projects/{project_id}/draft-section",
                json={"section_key": "s1"},
                timeout=httpx.Timeout(1800.0, connect=20.0),
            )
            if drafted.status_code == 200:
                draft = str(data(drafted).get("draft_content") or "")
                break
            body = drafted.text[:400]
            step(f"draft-section attempt {attempt} status={drafted.status_code} {body[:160]}")
            if "หมดเวลารอคิว" not in body and drafted.status_code not in {429, 503}:
                break
            time.sleep(20)

        stub = [s for s in STUBS if s in draft]
        draft_ok = (
            drafted is not None
            and drafted.status_code == 200
            and len(draft) >= 50
            and thai_count(draft) >= 8
            and ("โครงการ" in draft or "จัดซื้อ" in draft)
            and not stub
        )
        report["draft_s1"] = {
            "ok": draft_ok,
            "status": drafted.status_code if drafted is not None else None,
            "chars": len(draft),
            "thai": thai_count(draft),
            "stub": stub,
            "preview": draft[:500],
        }
        step(f"draft-section chars={len(draft)} ok={draft_ok}")
        if not draft_ok:
            report["ok"] = False
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return 1

        reviewed = client.post(
            f"/api/v1/projects/{project_id}/review",
            json={},
            timeout=httpx.Timeout(900.0, connect=20.0),
        )
        payload = data(reviewed) if reviewed.status_code == 200 else {}
        score = payload.get("quality_score")
        review_ok = reviewed.status_code == 200 and (score is None or float(score) >= 0)
        report["project_review"] = {
            "ok": review_ok,
            "status": reviewed.status_code,
            "quality_score": score,
            "findings": len(payload.get("findings") or []),
            "assessment": str(payload.get("assessment") or payload.get("summary") or "")[:400],
        }
        step(f"project review score={score} ok={review_ok}")

        # Keep phase4 helper in sync with a real project id for follow-up.
        phase4 = Path(__file__).resolve().parent / "_gemini_phase4_review.py"
        if phase4.is_file() and review_ok:
            src = phase4.read_text(encoding="utf-8")
            if 'PROJECT = "' in src:
                import re

                src2 = re.sub(
                    r'PROJECT = "[^"]+"',
                    f'PROJECT = "{project_id}"',
                    src,
                    count=1,
                )
                if src2 != src:
                    phase4.write_text(src2, encoding="utf-8")
                    step(f"updated phase4 PROJECT={project_id}")

        report["ok"] = bool(
            report["analyze"]["ok"]
            and report["fill_references"]["ok"]
            and report["confirm_ready"]["ok"]
            and report["draft_s1"]["ok"]
            and report["project_review"]["ok"]
        )
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    step(f"wrote {OUT} ok={report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
