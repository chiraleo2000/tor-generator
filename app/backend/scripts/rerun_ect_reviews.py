import sys
import time
from pathlib import Path

import httpx

from app.services.tor_assemble import plain_tor_from_section_items

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "http://127.0.0.1:4000"
PACK = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "ect_ai_chatbot_pack.txt"
PID = "4ffe28ec-9de6-4a45-a7a1-b3057e952770"

for _ in range(30):
    try:
        if httpx.get(f"{API}/health", timeout=3).status_code == 200:
            break
    except Exception:
        time.sleep(1)

pack = PACK.read_text(encoding="utf-8")
client = httpx.Client(base_url=API, timeout=120)
login = client.post(
    "/api/v1/auth/login",
    json={"email": "officer@example.go.th", "password": "Passw0rd!"},
)
login.raise_for_status()
token = (login.json().get("data") or login.json()).get("token")
client.headers["Authorization"] = f"Bearer {token}"


def review_file(name: str, body: str) -> dict:
    extracted = client.post(
        "/api/v1/review/extract",
        files={"file": (name, body.encode("utf-8"), "text/plain")},
    )
    extracted.raise_for_status()
    job_id = (extracted.json().get("data") or extracted.json())["id"]
    ran = client.post("/api/v1/review/run", json={"id": job_id})
    ran.raise_for_status()
    return ran.json().get("data") or ran.json()


src = review_file("ect-ai-chatbot-tor.txt", pack)
print("SOURCE_SCORE", src.get("quality_score"), "FINDINGS", len(src.get("findings") or []))
for item in (src.get("findings") or [])[:6]:
    print(" ", item.get("section"), item.get("severity"), (item.get("message") or "")[:80])

sections = client.get(f"/api/v1/projects/{PID}/sections").json()["data"]
tor = plain_tor_from_section_items(sections.get("sections") or [])
print("ASSEMBLED_CHARS", len(tor))
drafted = review_file("ect-drafted-tor.txt", tor)
print("DRAFTED_SCORE", drafted.get("quality_score"), "FINDINGS", len(drafted.get("findings") or []))
for item in (drafted.get("findings") or [])[:6]:
    print(" ", item.get("section"), item.get("severity"), (item.get("message") or "")[:80])

phase4 = client.post(f"/api/v1/projects/{PID}/intake/confirm-phase4", json={"confirm": True})
print("PHASE4", phase4.status_code, phase4.text[:240])
