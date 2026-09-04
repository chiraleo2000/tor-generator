"""Sequential headed UI walk: chat -> draft TOR -> review TOR."""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

BASE = "http://localhost:3000"
EMAIL = "officer@example.go.th"
PASSWORD = "Passw0rd!"
EVIDENCE = Path(__file__).resolve().parents[3] / "Discussions" / "test-evidence"

INTAKE = "\n".join(
    [
        "ความเป็นมา (s1): กรมบัญชีกลางมีความจำเป็นต้องจัดซื้อระบบสารสนเทศบริหารสัญญาจัดซื้อจัดจ้าง",
        "เพื่อติดตามงวดจ่ายและการส่งมอบให้เป็นไปตาม พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560",
        "วัตถุประสงค์ (s2): เพื่อให้เจ้าหน้าที่พัสดุบริหารสัญญา ตรวจรับงาน และรายงานสถานะได้ครบถ้วนตามกฎหมาย",
        "ระยะเวลาดำเนินการ (s5): 180 วัน นับจากวันที่ลงนามในสัญญา",
        "วงเงินงบประมาณ (s6): 2,500,000 บาท (สองล้านห้าแสนบาทถ้วน) จากงบดำเนินงานประจำปี",
        "สถานที่ดำเนินการ (s7): กรมบัญชีกลาง ถนนพระรามที่ 6 แขวงพญาไท เขตพญาไท กรุงเทพมหานคร",
        "ขอบเขตงานหลัก (s4.1): วิเคราะห์ความต้องการ พัฒนาโมดูลบริหารสัญญา ทดสอบระบบ อบรมผู้ใช้ และส่งมอบคู่มือใช้งาน",
    ]
)

TOR_TEXT = "\n".join(
    [
        "1. ความเป็นมา",
        "โครงการจัดซื้อครุภัณฑ์คอมพิวเตอร์ของสำนักงานปลัดกระทรวง วงเงิน 5,000,000 บาท",
        "2. วัตถุประสงค์ เพื่อทดแทนครุภัณฑ์ตาม พ.ร.บ. การจัดซื้อจัดจ้าง พ.ศ. 2560",
        "ระยะเวลา 180 วัน สถานที่กรุงเทพมหานคร",
    ]
)


def shot(page: Page, name: str) -> Path:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"evidence {name}.png", flush=True)
    return path


def login(page: Page) -> None:
    page.goto(f"{BASE}/login")
    expect(page.get_by_test_id("login-form")).to_be_visible()
    page.get_by_test_id("login-email").fill(EMAIL)
    page.get_by_test_id("login-password").fill(PASSWORD)
    page.get_by_test_id("login-submit").click()
    expect(page.get_by_test_id("projects-page")).to_be_visible(timeout=20_000)
    expect(page).to_have_url(re.compile(r"/projects"))
    expect(page.get_by_test_id("login-error")).to_have_count(0)
    expect(page.get_by_text("กำลังโหลดข้อมูล...")).to_have_count(0, timeout=20_000)


def confirm_phase(page: Page) -> None:
    expect(page.get_by_test_id("confirm-phase-dialog")).to_be_visible()
    page.get_by_test_id("confirm-phase-ok").click()


def step_chat(page: Page) -> None:
    login(page)
    shot(page, "serial-00-dashboard")
    page.get_by_test_id("nav-chat").click()
    expect(page).to_have_url(re.compile(r"/chat"))
    expect(page.get_by_test_id("chat-shell")).to_be_visible()
    page.get_by_test_id("chat-new-room").click()
    box = page.get_by_test_id("chat-input")
    expect(box).to_be_visible(timeout=10_000)
    box.fill(
        "ถามจาก พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560 ผู้เสนอราคาต้องมีคุณสมบัติอะไรบ้าง อ้างมาตราให้ชัด"
    )
    page.get_by_test_id("chat-send").click()
    body = ""
    deadline = time.time() + 600
    while time.time() < deadline:
        last = page.get_by_test_id("chat-msg-assistant").last
        if last.count() == 0:
            page.wait_for_timeout(800)
            continue
        body = last.locator("p").first.inner_text().strip()
        if len(body) >= 80:
            break
        page.wait_for_timeout(1000)
    else:
        raise AssertionError(f"short chat answer: {len(body)} {body[:80]!r}")
    if any(bad in body for bad in ("ชิ้นจำลอง", "custom-rag-stub", "mcp-retrieve-stub")):
        raise AssertionError("chat used stub text")
    chips = page.get_by_test_id("chat-msg-assistant").last.get_by_test_id("chat-citation")
    expect(chips.first).to_be_visible(timeout=30_000)
    blob = " | ".join(chips.all_inner_texts()).lower()
    if "stub" in blob:
        raise AssertionError(f"stub citation: {blob}")
    shot(page, "serial-01-chat")
    print("CHAT_OK", flush=True)


def step_draft(page: Page) -> None:
    login(page)
    page.get_by_test_id("nav-projects").click()
    expect(page.get_by_test_id("projects-page")).to_be_visible()
    page.get_by_test_id("new-project").click()
    expect(page.get_by_test_id("new-project-dialog")).to_be_visible()
    page.get_by_test_id("new-project-name").fill(f"โครงการทดสอบ UI {int(time.time())}")
    page.get_by_test_id("new-project-ministry").fill("กรมบัญชีกลาง")
    page.get_by_test_id("new-project-budget").fill("2500000")
    page.get_by_test_id("create-project-submit").click()
    expect(page.get_by_test_id("draft-page")).to_be_visible(timeout=20_000)
    expect(page.get_by_test_id("phase-0")).to_be_visible()
    page.get_by_test_id("intake-paste").fill(INTAKE)
    page.get_by_test_id("intake-upload").set_input_files(
        {
            "name": "pB0.txt",
            "mimeType": "text/plain",
            "buffer": (INTAKE + "\nไฟล์แนบประกอบการวิเคราะห์").encode("utf-8"),
        }
    )
    expect(page.get_by_test_id("phase0-file-list")).to_contain_text("pB0.txt", timeout=30_000)
    shot(page, "serial-02-draft-phase0")
    page.get_by_test_id("intake-start-analyze").click()
    confirm_phase(page)
    expect(page.get_by_test_id("phase1-coverage")).to_be_visible(timeout=240_000)
    shot(page, "serial-02-draft-phase1")
    page.get_by_test_id("phase1-skip").click()
    expect(page.get_by_test_id("phase2-qa")).to_be_visible(timeout=25_000)
    shot(page, "serial-02-draft-phase2")
    expect(page.get_by_test_id("intake-confirm-ready")).to_be_enabled(timeout=180_000)
    page.get_by_test_id("intake-confirm-ready").click()
    confirm_phase(page)
    expect(page.get_by_test_id("phase3-draft")).to_be_visible(timeout=90_000)
    expect(page.get_by_test_id("draft-chat")).to_be_visible()
    shot(page, "serial-02-draft-phase3-start")
    expect(page.get_by_test_id("phase3-all-drafted")).to_be_visible(timeout=3_600_000)
    expect(page.get_by_test_id("draft-chat-count")).to_have_text("13/13 หมวด")
    shot(page, "serial-02-draft-13")
    page.get_by_test_id("phase3-confirm").click()
    confirm_phase(page)
    shot(page, "serial-02-draft-done")
    print("DRAFT_OK", flush=True)


def step_review(page: Page) -> None:
    login(page)
    page.get_by_test_id("nav-review").click()
    expect(page.get_by_test_id("review-page")).to_be_visible()
    expect(page.get_by_test_id("review-stepper")).to_be_visible()
    shot(page, "serial-03-review-start")
    page.locator("[data-testid=review-page] input[type=file]").first.set_input_files(
        {
            "name": "tor-draft.txt",
            "mimeType": "text/plain",
            "buffer": TOR_TEXT.encode("utf-8"),
        }
    )
    expect(page.get_by_test_id("review-extract")).to_be_enabled()
    page.get_by_test_id("review-extract").click()
    expect(page.get_by_test_id("review-extract-preview")).to_be_visible(timeout=120_000)
    shot(page, "serial-04-review-extract")
    page.get_by_test_id("review-confirm-run").click()
    expect(page.get_by_test_id("review-score")).to_be_visible(timeout=240_000)
    expect(page.get_by_test_id("review-result")).to_contain_text("คะแนนความพร้อม")
    shot(page, "serial-05-review-score")
    print("REVIEW_OK", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=("chat", "draft", "review"))
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="chrome",
            headless=False,
            slow_mo=250,
            args=["--window-position=140,40", "--window-size=1280,860"],
        )
        page = browser.new_page(viewport={"width": 1280, "height": 800}, locale="th-TH")
        try:
            if args.step == "chat":
                step_chat(page)
            elif args.step == "draft":
                step_draft(page)
            else:
                step_review(page)
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
