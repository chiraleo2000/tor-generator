# -*- coding: utf-8 -*-
import json
import urllib.request
from pathlib import Path

out = Path(__file__).resolve().parent
req = urllib.request.Request(
    "http://127.0.0.1:4000/api/v1/auth/login",
    data=json.dumps(
        {"email": "officer@example.go.th", "password": "Passw0rd!"}
    ).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=30) as resp:
    token = json.loads(resp.read().decode())["data"]["token"]
pid = "e0bd0d2c-397b-485e-8c6a-d02ec82099b4"
req2 = urllib.request.Request(
    f"http://127.0.0.1:4000/api/v1/projects/{pid}/sections",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(req2, timeout=60) as resp:
    secs = json.loads(resp.read().decode())["data"]
(out / "draft-sections.json").write_text(
    json.dumps(secs, ensure_ascii=False, indent=2), encoding="utf-8"
)
parts: list[str] = []
for section in secs.get("sections") or []:
    key = section.get("key") or section.get("section_key")
    title = section.get("title") or ""
    content = section.get("content") or ""
    if content.strip():
        parts.append(f"# {key} {title}\n\n{content}\n")
    for sub in section.get("subs") or []:
        sub_content = sub.get("content") or ""
        if sub_content.strip():
            parts.append(
                f"## {sub.get('key')} {sub.get('title')}\n\n{sub_content}\n"
            )
text = "\n".join(parts) if parts else "(ยังไม่มีเนื้อหาร่างจาก compose)\n"
(out / "draft-tor.md").write_text(text, encoding="utf-8")
print("draft_chars", len(text), "parts", len(parts))
