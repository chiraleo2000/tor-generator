"""Slow headed UI walk: chat → draft → review, one LLM job at a time."""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

# Playwright is an optional host-side dependency for this manual script.
from playwright.sync_api import TimeoutError as PlaywrightTimeout  # pyright: ignore[reportMissingImports]
from playwright.sync_api import expect, sync_playwright  # pyright: ignore[reportMissingImports]

BASE = "http://localhost:3000"
LM_STUDIO = "http://127.0.0.1:1234/v1"
EMAIL = "officer@example.go.th"
PASSWORD = "Passw0rd!"
EVIDENCE = Path(__file__).resolve().parents[3] / "Discussions" / "test-evidence"

SLOW_MO_MS = 900
PAUSE_MS = 5_000
COOLDOWN_MS = 22_000
TYPE_DELAY_MS = 45

INTAKE = (
    "ความเป็นมา (s1): กรมบัญชีกลางมีความจำเป็นต้องจัดซื้อระบบสารสนเทศบริหารสัญญาจัดซื้อจัดจ้าง "
    "เพื่อติดตามงวดจ่ายและการส่งมอบให้เป็นไปตาม พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560\n"
    "วัตถุประสงค์ (s2): เพื่อให้เจ้าหน้าที่พัสดุบริหารสัญญา ตรวจรับงาน และรายงานสถานะได้ครบถ้วนตามกฎหมาย\n"
    "ระยะเวลาดำเนินการ (s5): 180 วัน นับจากวันที่ลงนามในสัญญา\n"
    "วงเงินงบประมาณ (s6): 2,500,000 บาท (สองล้านห้าแสนบาทถ้วน) จากงบดำเนินงานประจำปี\n"
    "สถานที่ดำเนินการ (s7): กรมบัญชีกลาง ถนนพระรามที่ 6 แขวงพญาไท เขตพญาไท กรุงเทพมหานคร\n"
    "ขอบเขตงานหลัก (s4.1): วิเคราะห์ความต้องการ พัฒนาโมดูลบริหารสัญญา ทดสอบระบบ อบรมผู้ใช้ และส่งมอบคู่มือใช้งาน"
)

GAPS = [
    "ความเป็นมาคือกรมบัญชีกลางต้องมีระบบบริหารสัญญาจัดซื้อจัดจ้างภาครัฐ",
    "วัตถุประสงค์เพื่อติดตามงวดจ่าย ตรวจรับงาน และรายงานสถานะตามกฎหมาย",
    "ระยะเวลาดำเนินการหนึ่งร้อยแปดสิบวันนับจากวันลงนามในสัญญา",
    "วงเงินงบประมาณสองล้านห้าแสนบาทถ้วน จากงบดำเนินงานประจำปี",
    "สถานที่ดำเนินการคือกรมบัญชีกลาง ถนนพระรามที่ 6 กรุงเทพมหานคร",
    "ขอบเขตงานหลักคือวิเคราะห์ความต้องการ พัฒนา ทดสอบ อบรม และส่งมอบคู่มือ",
]

TOR = (
    "1. ความเป็นมา\n"
    "โครงการจัดซื้อครุภัณฑ์คอมพิวเตอร์ของสำนักงานปลัดกระทรวง วงเงิน 5,000,000 บาท\n"
    "2. วัตถุประสงค์ เพื่อทดแทนครุภัณฑ์ตาม พ.ร.บ. การจัดซื้อจัดจ้าง พ.ศ. 2560\n"
    "ระยะเวลา 180 วัน สถานที่กรุงเทพมหานคร\n"
)

FACT = ["s1", "s2", "s5", "s6", "s7", "s4.1"]
STUB = re.compile(r"ชิ้นจำลอง|custom-rag-stub|mcp-retrieve-stub", re.I)


def say(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def shot(page: Any, name: str) -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / f"ui3-{name}.png"
    page.screenshot(path=str(path), full_page=True)
    say(f"ภาพ {path.name}")


def pause(page: Any, ms: int = PAUSE_MS, why: str = "") -> None:
    if why:
        say(why)
    page.wait_for_timeout(ms)


def type_slow(locator: Any, text: str) -> None:
    locator.click()
    locator.fill("")
    if len(text) > 120:
        locator.fill(text)
        return
    locator.press_sequentially(text, delay=TYPE_DELAY_MS)


def lm_studio_ok() -> str:
    try:
        with urllib.request.urlopen(f"{LM_STUDIO}/models", timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        ids = [row.get("id", "") for row in payload.get("data") or []]
        return ", ".join(ids) or "(empty)"
    except (json.JSONDecodeError, OSError) as exc:
        return f"DOWN ({exc})"


def cooldown(page: Any, why: str) -> None:
    status = lm_studio_ok()
    say(f"{why} — LM Studio: {status}")
    page.wait_for_timeout(COOLDOWN_MS)


def confirm(page: Any) -> None:
    expect(page.get_by_test_id("confirm-phase-dialog")).to_be_visible()
    pause(page, 1_200, "รอกล่องยืนยันให้เห็นบนจอ")
    page.get_by_test_id("confirm-phase-ok").click()


def _assistant_nodes(page: Any) -> Any:
    return page.locator("[data-testid=chat-msg-assistant] p")


def _send_ready(page: Any) -> bool:
    try:
        return page.get_by_test_id("chat-send").is_enabled()
    except PlaywrightTimeout:
        return False


def _poll_assistant(page: Any, last_len: int, last_change: float) -> tuple[str, int, float]:
    nodes = _assistant_nodes(page)
    if not nodes.count():
        return "", last_len, last_change
    text = nodes.last.inner_text().strip()
    if len(text) > last_len:
        last_len = len(text)
        last_change = time.time()
        say(f"กำลังได้คำตอบ {last_len} ตัวอักษร...")
    return text, last_len, last_change


def wait_assistant_long(page: Any, timeout_ms: int = 600_000) -> str | None:
    deadline = time.time() + timeout_ms / 1000
    last_len = 0
    last_change = time.time()
    text = ""
    while time.time() < deadline:
        text, last_len, last_change = _poll_assistant(page, last_len, last_change)
        if last_len > 80 and _send_ready(page):
            return text
        if last_len > 80 and (time.time() - last_change) > 25:
            say("คำตอบหยุดยาวแล้ว ปุ่มส่งยังไม่กลับ — ไปต่อเพื่อไม่ให้โมเดลค้าง")
            return text
        page.wait_for_timeout(4_000)
    if last_len > 80:
        say("หมดเวลารอสตรีม แต่มีคำตอบแล้ว — ไปต่อ")
        nodes = _assistant_nodes(page)
        return nodes.last.inner_text().strip() if nodes.count() else text
    return None


def all_facts_filled(page: Any) -> bool:
    for key in FACT:
        row = page.get_by_test_id(f"coverage-row-{key}")
        if row.count() == 0:
            return False
        if row.get_attribute("data-status") != "filled":
            return False
    return True


def section_has_text(page: Any) -> bool:
    return page.evaluate(
        """() => {
          const inputs = [...document.querySelectorAll(
            '[data-testid=phase3-draft] textarea, [data-testid=phase3-draft] input'
          )];
          return inputs.some((el) => ((el.value || '').trim().length > 20));
        }"""
    )


def draft_count_text(page: Any) -> str:
    el = page.get_by_test_id("draft-chat-count")
    if el.count() == 0:
        return ""
    return el.inner_text().strip()


def watch_draft(page: Any, seconds: int, name: str) -> bool:
    say(f"เฝ้าดูการร่างบนจอ {seconds} วินาที (ไม่กดซ้ำ)")
    end = time.time() + seconds
    n = 0
    while time.time() < end:
        n += 1
        count = draft_count_text(page)
        filled = section_has_text(page)
        say(f"  ร่าง… {count or '?'} | ช่องมีข้อความ={filled}")
        if n % 3 == 0:
            shot(page, f"{name}-t{n}")
        if filled or (count and not count.startswith("0/")):
            return True
        page.wait_for_timeout(12_000)
    return section_has_text(page) or not draft_count_text(page).startswith("0/")


def _login(page: Any) -> None:
    say("เข้าสู่ระบบ")
    page.goto(f"{BASE}/login")
    expect(page.get_by_test_id("login-form")).to_be_visible()
    type_slow(page.get_by_test_id("login-email"), EMAIL)
    pause(page, 800)
    type_slow(page.get_by_test_id("login-password"), PASSWORD)
    pause(page, 1_000)
    page.get_by_test_id("login-submit").click()
    expect(page.get_by_test_id("projects-page")).to_be_visible(timeout=20_000)
    pause(page, PAUSE_MS, "แดชบอร์ด — พักให้เห็นเมนู")
    shot(page, "00-dashboard")


def _run_chat(page: Any) -> None:
    say("=== 1/3 ถาม-ตอบ ===")
    page.get_by_test_id("nav-chat").click()
    expect(page.get_by_test_id("chat-shell")).to_be_visible()
    pause(page, PAUSE_MS, "หน้าถาม-ตอบ")
    page.get_by_test_id("chat-new-room").click()
    expect(page.get_by_test_id("chat-input")).to_be_visible(timeout=10_000)
    pause(page, 1_500)
    type_slow(
        page.get_by_test_id("chat-input"),
        "ผู้เสนอราคาต้องมีคุณสมบัติอะไรบ้าง ตาม พ.ร.บ. จัดซื้อจัดจ้าง 2560 อ้างมาตรา",
    )
    pause(page, 2_000, "ส่งคำถาม แล้วรอโมเดลทีละคำ — ไม่กดซ้ำ")
    page.get_by_test_id("chat-send").click()
    text = wait_assistant_long(page)
    if text is None:
        raise SystemExit("FAIL: โมเดลค้างตอนรอคำตอบแชท")
    if STUB.search(text):
        raise SystemExit("FAIL chat contains stub")
    chips = page.get_by_test_id("chat-msg-assistant").last.get_by_test_id("chat-citation")
    expect(chips.first).to_be_visible(timeout=30_000)
    chip_blob = " | ".join(chips.all_inner_texts()).lower()
    if "stub" in chip_blob:
        raise SystemExit(f"FAIL chat stub citation: {chip_blob}")
    say(f"citations: {chip_blob[:300]}")
    say(f"preview: {text[:220]}")
    pause(page, 8_000, "คงคำตอบบนจอให้อ่าน")
    shot(page, "01-chat")
    cooldown(page, "พักโมเดลหลังแชท ก่อนเข้าเครื่องมือร่าง")


def _fill_gaps(page: Any) -> None:
    if all_facts_filled(page):
        say("ช่องบังคับครบแล้ว ไม่ยิงแชทซ้ำ")
        return
    say("ยังขาดช่อง — ตอบทีละข้อ เว้นช่วง")
    for gap in GAPS:
        if all_facts_filled(page):
            break
        cooldown(page, "พักก่อนส่งคำตอบช่องถัดไป")
        page.get_by_test_id("chat-input").fill(gap)
        page.get_by_test_id("chat-send").click()
        if wait_assistant_long(page, timeout_ms=240_000) is None:
            say("คำตอบช่องนี้ช้า/ค้าง — ไปช่องถัดไป")


def _run_draft(page: Any) -> None:
    say("=== 2/3 ร่าง TOR ===")
    page.get_by_test_id("nav-projects").click()
    expect(page.get_by_test_id("projects-page")).to_be_visible()
    pause(page, 2_000)
    page.get_by_test_id("new-project").click()
    expect(page.get_by_test_id("new-project-dialog")).to_be_visible()
    type_slow(page.get_by_test_id("new-project-name"), f"โครงการทดสอบช้า {int(time.time())}")
    type_slow(page.get_by_test_id("new-project-ministry"), "กรมบัญชีกลาง")
    type_slow(page.get_by_test_id("new-project-budget"), "2500000")
    pause(page, 1_200)
    page.get_by_test_id("create-project-submit").click()
    expect(page.get_by_test_id("draft-page")).to_be_visible(timeout=20_000)
    expect(page.get_by_test_id("intake-paste")).to_be_visible()
    pause(page, PAUSE_MS, "ขั้นที่ 0 — วางข้อความโครงการ")
    page.get_by_test_id("intake-paste").fill(INTAKE)
    page.get_by_test_id("intake-upload").set_input_files(
        {
            "name": "pB0.txt",
            "mimeType": "text/plain",
            "buffer": (INTAKE + "\nไฟล์แนบ E2E").encode("utf-8"),
        }
    )
    expect(page.get_by_test_id("phase0-file-list")).to_contain_text("pB0.txt", timeout=30_000)
    pause(page, 3_000, "มีไฟล์แล้ว — กดวิเคราะห์ครั้งเดียว")
    shot(page, "02-draft-phase0")
    page.get_by_test_id("intake-start-analyze").click()
    confirm(page)
    analyzing = page.get_by_test_id("phase0-analyzing")
    if analyzing.count():
        say("กำลังวิเคราะห์ — รอจนจบ ไม่รีเฟรช")
        shot(page, "02b-analyzing")
    expect(page.get_by_test_id("phase1-coverage")).to_be_visible(timeout=300_000)
    pause(page, PAUSE_MS, "ขั้นที่ 1 ความครอบคลุม")
    shot(page, "03-draft-phase1")
    page.get_by_test_id("phase1-skip").click()
    expect(page.get_by_test_id("phase2-qa")).to_be_visible(timeout=25_000)
    pause(page, PAUSE_MS, "ขั้นที่ 2 ถาม-ตอบร่าง")
    _fill_gaps(page)
    expect(page.get_by_test_id("intake-confirm-ready")).to_be_enabled(timeout=60_000)
    shot(page, "04-draft-phase2")
    cooldown(page, "พักก่อนเข้าขั้นร่างเนื้อหา (กันโมเดลค้าง)")
    page.get_by_test_id("intake-confirm-ready").click()
    confirm(page)
    expect(page.get_by_test_id("phase3-draft")).to_be_visible(timeout=120_000)
    expect(page.get_by_test_id("draft-chat")).to_be_visible()
    pause(page, 8_000, "ขั้นที่ 3 — ดูว่าระบบเริ่มร่างเองหรือยัง ยังไม่กดซ้ำ")
    shot(page, "05-draft-phase3")
    progressed = watch_draft(page, 90, "05b-watch")
    if not progressed:
        say("ยังไม่มีหมวดจบ — กดร่างหมวด 1 ครั้งเดียว แล้วรอ")
        cooldown(page, "พักก่อนกดร่างหมวด 1")
        page.get_by_test_id("draft-ai-s1").click()
        progressed = watch_draft(page, 240, "06-s1")
    if not progressed and not section_has_text(page):
        raise SystemExit("FAIL: ร่างค้าง ไม่มีข้อความหมวด")
    say(f"สถานะร่าง {draft_count_text(page)} | ช่องมีข้อความ={section_has_text(page)}")
    body = page.get_by_test_id("phase3-draft").inner_text()
    if STUB.search(body):
        raise SystemExit("FAIL draft stub text")
    pause(page, 8_000, "คงหน้าจร่างให้อ่าน")
    shot(page, "06-draft-progress")
    cooldown(page, "พักโมเดลหลังร่าง ก่อนตรวจสอบ")


def _run_review(page: Any) -> None:
    say("=== 3/3 ตรวจสอบ TOR ===")
    page.get_by_test_id("nav-review").click()
    expect(page.get_by_test_id("review-page")).to_be_visible()
    pause(page, PAUSE_MS, "หน้าตรวจสอบ")
    shot(page, "07-review-start")
    page.locator("[data-testid=review-page] input[type=file]").first.set_input_files(
        {"name": "tor-draft.txt", "mimeType": "text/plain", "buffer": TOR.encode("utf-8")}
    )
    pause(page, 2_000)
    expect(page.get_by_test_id("review-extract")).to_be_enabled()
    page.get_by_test_id("review-extract").click()
    expect(page.get_by_test_id("review-extract-preview")).to_be_visible(timeout=180_000)
    pause(page, PAUSE_MS, "สกัดข้อความแล้ว — ยังไม่รันตรวจจนกว่าจะพักโมเดล")
    shot(page, "08-review-extract")
    cooldown(page, "พักก่อนรันตรวจ (ขั้นนี้ใช้โมเดล)")
    page.get_by_test_id("review-confirm-run").click()
    say("กำลังตรวจ — รอคะแนนบนจอ")
    expect(page.get_by_test_id("review-score")).to_be_visible(timeout=360_000)
    expect(page.get_by_test_id("review-result")).to_contain_text("คะแนนความพร้อม")
    review_text = page.get_by_test_id("review-page").inner_text()
    if STUB.search(review_text):
        raise SystemExit("FAIL review stub text")
    say(page.get_by_test_id("review-score").inner_text()[:220])
    pause(page, 10_000, "คงผลตรวจบนจอ")
    shot(page, "09-review-score")
    say("จบครบ 3 เครื่องมือ — เปิดหน้าต่างค้าง 20 วินาที")
    page.wait_for_timeout(20_000)


def run() -> None:
    say(f"เริ่มช้า ๆ  slowMo={SLOW_MO_MS}ms  cooldown={COOLDOWN_MS}ms")
    say(f"LM Studio ก่อนเริ่ม: {lm_studio_ok()}")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=SLOW_MO_MS,
            args=[
                "--new-window",
                "--window-position=80,30",
                "--window-size=1360,900",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
            ],
        )
        page = browser.new_page(viewport={"width": 1280, "height": 840}, locale="th-TH")
        page.set_default_timeout(90_000)
        _login(page)
        _run_chat(page)
        _run_draft(page)
        _run_review(page)
        browser.close()
        say("UI3_SLOW_OK")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    run()
