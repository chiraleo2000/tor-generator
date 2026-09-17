from __future__ import annotations

import json
from pathlib import Path

import httpx

API = "http://127.0.0.1:4000"
PROJECT = "31a38454-fd31-41c6-80f4-d82fc895c16a"
OUT = Path(__file__).resolve().parent / "_gemini-phase4-review.json"


def data(response: httpx.Response) -> dict:
    body = response.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"] or {}
    return body if isinstance(body, dict) else {}


def main() -> int:
    with httpx.Client(base_url=API, timeout=httpx.Timeout(900.0, connect=20.0)) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "officer@example.go.th", "password": "Passw0rd!"},
        )
        login.raise_for_status()
        client.headers["Authorization"] = f"Bearer {data(login)['token']}"
        reviewed = client.post(f"/api/v1/projects/{PROJECT}/review", json={})
        payload = data(reviewed)
        report = {
            "status": reviewed.status_code,
            "quality_score": payload.get("quality_score"),
            "is_valid": payload.get("is_valid"),
            "findings": len(payload.get("findings") or []),
            "assessment": str(payload.get("assessment") or payload.get("summary") or "")[:400],
        }
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if reviewed.status_code == 200 and payload.get("quality_score") is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
