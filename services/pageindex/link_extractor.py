"""
Web/link ingestion helpers.

Fetches a public URL, extracts readable article-like text, then asks Azure
OpenAI to keep only the real news/content body before PageIndex runs.
"""

import json
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx


class _ReadableHTMLParser(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "form", "nav", "footer", "header"}
    BLOCK_TAGS = {"p", "br", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "blockquote"}

    def __init__(self):
        super().__init__()
        self.skip_depth = 0
        self.title = ""
        self._in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title = f"{self.title} {text}".strip()
        if not self.skip_depth:
            self.parts.append(text)

    def text(self) -> str:
        raw = " ".join(self.parts)
        raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
        raw = re.sub(r"\n\s+", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def _clean_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise ValueError("กรุณาใส่ URL")
    if re.search(r"\s", url):
        raise ValueError("URL ไม่ถูกต้อง")
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL ไม่ถูกต้อง")
    return url


def _compact_text(text: str, max_chars: int = 45000) -> str:
    lines = []
    seen = set()
    for line in re.split(r"\n+", text):
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) < 20:
            continue
        key = line[:160]
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
        if sum(len(x) for x in lines) >= max_chars:
            break
    return "\n\n".join(lines)[:max_chars].strip()


async def fetch_url_text(url: str) -> dict:
    url = _clean_url(url)
    headers = {
        "User-Agent": "Mozilla/5.0 Knowledge-RAG/1.0 (+article extraction)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.7",
    }
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        text = resp.text

    if "text/plain" in content_type:
        title = urlparse(str(resp.url)).netloc
        readable = _compact_text(text)
    else:
        parser = _ReadableHTMLParser()
        parser.feed(text)
        title = parser.title or urlparse(str(resp.url)).netloc
        readable = _compact_text(parser.text())

    if len(readable) < 200:
        raise ValueError(
            "ดึงเนื้อหาจากลิงก์ได้น้อยเกินไป อาจเป็นหน้า login, dynamic page, หรือถูกบล็อก"
        )

    return {"url": str(resp.url), "title": title.strip()[:180], "text": readable}


async def ai_clean_article_text(raw: dict, cfg: dict) -> dict:
    prompt = f"""คัดกรองเนื้อหาจากเว็บให้เหลือเฉพาะเนื้อหาข่าว/บทความจริงสำหรับทำ RAG

ตัดสิ่งต่อไปนี้ออก: เมนูเว็บ, ปุ่มแชร์, โฆษณา, cookie banner, footer, related posts, comment, login prompt
คงไว้: headline, วันที่/แหล่งข่าวถ้ามี, เนื้อหาข่าวหลัก, quote สำคัญ, bullet/table ที่เป็นเนื้อหาข่าว

ตอบ JSON object เดียว:
{{"title":"...", "content":"plain text ข่าวจริง", "published_date": null หรือ "YYYY-MM-DD", "source_name":"..."}}

URL: {raw.get("url")}
TITLE: {raw.get("title")}

RAW TEXT:
{raw.get("text", "")[:30000]}
"""
    try:
        ep = cfg.get("endpoint", "").rstrip("/")
        model = cfg.get("model", "gpt-4o-mini")
        api_ver = cfg.get("api_version", "2024-08-01-preview")
        url = f"{ep}/openai/deployments/{model}/chat/completions?api-version={api_ver}"
        headers = {"api-key": cfg.get("api_key", ""), "Content-Type": "application/json"}
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": 5000,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
        data = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(re.sub(r"```json|```", "", data).strip())
        content = _compact_text(str(parsed.get("content") or ""))
        if len(content) >= 200:
            return {
                "title": str(parsed.get("title") or raw.get("title") or raw.get("url")).strip(),
                "content": content,
                "published_date": parsed.get("published_date"),
                "source_name": str(parsed.get("source_name") or "").strip(),
            }
    except Exception as exc:
        print(f"[link_extractor] AI cleanup fallback: {exc}")

    return {
        "title": raw.get("title") or raw.get("url"),
        "content": raw.get("text", ""),
        "published_date": None,
        "source_name": "",
    }
