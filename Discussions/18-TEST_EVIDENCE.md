# หลักฐานการทดสอบ — ผ่านทั้งหมด

วันที่ **21 สิงหาคม 2026** (รอบทดสอบเต็ม: coverage + headed Playwright แบบพิมพ์ช้าเหมือนผู้ใช้ + LM Studio จริง)  
สแตก Docker `tor-app` (postgres + mongo + neo4j + redis + minio) + LM Studio ที่ `http://127.0.0.1:1234`  
`GET http://localhost:4000/health` = `healthy` ทั้ง `postgres` `redis` `minio` `mongo` `neo4j`

เอกสารชุดปัจจุบันเรียง **13–20** (เพิ่ม `20-AWS_BEDROCK_SETUP.md`). หลักฐานภาพอยู่ใน `discussions/test-evidence/`

| โมเดล | ค่า |
|--------|-----|
| Chat (dev) | `google/gemma-4-e4b` |
| Embeddings (dev) | `text-embedding-embeddinggemma-300m` (768 มิติ) |
| Production แนะนำ | Amazon Bedrock (ดู `20-AWS_BEDROCK_SETUP.md`) |

ภาพถ่ายจาก Playwright แบบ **headed** (`slowMo` 400ms, พิมพ์ทีละตัวอักษร delay 70ms, เบราว์เซอร์โชว์บนจอ) หลังเคสผ่านแล้วเท่านั้น  
คู่มือผู้ใช้: `13-USER_GUIDELINE.md` · รายงานการทำงาน: `19-APPLICATION_OPERATING_REPORT.md`

---

## สรุปตัวเลข (รอบ 21 ส.ค. 2026 — full coverage + live LM Studio)

| ชุด | ผล | ความหมาย |
|-----|-----|----------|
| pytest ไม่รวม `live_llm` | **1500 ผ่าน**, 14 ถูกตัดด้วย marker | รวม fill-references · catalog `category`/`processing_status` · แนบแชท `category=other` · coverage **86%** |
| pytest `live_llm` | **14 ผ่าน** | 10 เดิม + 4 ใน `test_live_realistic_workflow.py` (ร่าง / แชท RAG / ตรวจ TOR / KB other) |
| Vitest `test:coverage` | **167 ผ่าน** / 39 ไฟล์ | statements **84.95%** · lines **87.09%** (รวม Phase0–4 draft components) |
| ESLint | สะอาด | `npm run lint` |
| Playwright E2E headed | **20 ผ่าน** | 17 เดิม + 3 ใน `realistic-flow.spec.ts` (ตรวจ TOR ไม่ mock · KB other upload/download/delete · Phase 0 ไม่ auto-analyze) |
| Playwright guide headed | **3 ผ่าน** | ภาพคู่มือใน `test-evidence/` |
| Playwright reports | **3 ผ่าน** | ภาพ htmlcov backend/frontend + รายงาน Playwright |

รวม backend **1514** · frontend unit **167** · UI headed **20** + guide **3** + reports **3**

### สิ่งที่ตรวจแบบใช้งานจริงในรอบนี้

- ล็อกอิน/สร้างโครงการ **พิมพ์ทีละตัว** ไม่ใช้ `.fill()` แบบยิงเร็ว
- ถาม-ตอบ `/chat`: พิมพ์คำถามงวดจ่าย แล้วรอคำตอบจาก Gemma
- แนบไฟล์เข้าคลังของฉันจริง (ingest + embeddings) แล้วถามโหมดของฉัน
- ร่าง TOR Phase 0: วางข้อความโครงการยาว → กด **เริ่มวิเคราะห์** (ไม่วิเคราะห์อัตโนมัติ) → รอ LM Studio จัดช่อง
- Phase 3: กด **ร่างด้วย AI** หมวด 1 แล้วรอผล Gemma ไม่ mock `/intake/analyze`
- `test_live_realistic_workflow.py`: HTTP ไป Docker :4000 + LM Studio จริง (fail ถ้าสแตก/โมเดลดับ)
- `realistic-flow.spec.ts`: ตรวจ TOR สกัดไฟล์จริงแล้วยืนยัน Rule Engine · KB หมวดข้อมูลอื่น ๆ อัปโหลด/ดาวน์โหลด/ลบ

---

## รายงาน Playwright — 20 เคสแอป (headed)

รัน: `cd app/frontend && npm run test:e2e:headed` (1 worker, Chromium มองเห็นได้)  
Chromium, viewport 1440×900, ภาษา th-TH, ยิง `http://localhost:3000` · `HEADED=1` + `screenshot: on` + `slowMo: 400` + พิมพ์ทีละตัว 70ms

![รายงาน Playwright — 15 ผ่าน 0 ล้ม](test-evidence/15-playwright-report.png)

ด้านล่างอธิบายทีละเคสว่าตรวจอะไร และภาพที่บันทึกหลังผ่าน

---

## ขั้นที่ 1 — แขกถูกส่งไปเข้าสู่ระบบ

**ไฟล์เทสต์:** `landing.spec.ts` — *sends guests to login*

เปิด `/` ต้องไป `/login` และเห็นฟอร์มเข้าสู่ระบบ (การ์ดกรมทัพเรือ-น้ำเงิน ช่องอีเมล/รหัสผ่าน ปุ่มเข้าสู่ระบบ กล่อง Demo)

![เคส landing: หน้าเข้าสู่ระบบ](test-evidence/00-login.png)

---

## ขั้นที่ 2 — ฟอร์มสมัครสมาชิกเปิดได้

**ไฟล์เทสต์:** `landing.spec.ts` — *register form is reachable*  
**ภาพคู่มือ:** `guide-shots.spec.ts`

เปิด `/register` เห็นฟอร์ม **สมัครสมาชิก** และช่องชื่อ-นามสกุล

![เคส landing: สมัครสมาชิก](test-evidence/00b-register.png)

---

## ขั้นที่ 3 — ตรวจรหัสผ่านและล็อกอินเจ้าหน้าที่

**ไฟล์เทสต์:** `auth.spec.ts`

1. ไม่กรอกรหัสผ่าน → ข้อความข้อผิดพลาดมีคำว่า *รหัสผ่าน*
2. รหัสผิด `WrongPass1!` → แถบข้อผิดพลาดโชว์ ไม่เข้าแดชบอร์ด
3. บัญชี `officer@example.go.th` / `Passw0rd!` → URL เป็น `/projects` เห็น **รายการโครงการ TOR**
4. กดออกจากระบบ → กลับ `/login`

![เคส auth: แดชบอร์ดหลังล็อกอินสำเร็จ](test-evidence/01-login-dashboard.png)

---

## ขั้นที่ 4 — แดชบอร์ดและการ์ดสถานะ

**ไฟล์เทสต์:** `dashboard.spec.ts` + `wizard-flow.spec.ts` (บันทึกภาพก่อนสร้างโครงการ)

เห็นการ์ด **ร่าง (Draft)** / **กำลังดำเนินการ** / **เสร็จแล้ว** ตารางโครงการ วันที่ พ.ศ. ปุ่ม **+ สร้างโครงการ TOR ใหม่**

![เคส dashboard: ภาพรวมโครงการ](test-evidence/02-dashboard.png)

---

## ขั้นที่ 5 — ฟอร์มสร้างโครงการแล้วเข้า Phase 0

**ไฟล์เทสต์:** `dashboard.spec.ts` — *creates a project from the intake dialog*

1. กด `data-testid=new-project`
2. กล่อง **สร้างโครงการใหม่** เปิด (ข้อความ 5 Phase ไม่ใช่วิซาร์ด 8 ขั้น)
3. กรอกชื่อ `โครงการทดสอบ E2E` หน่วยงาน `กรมบัญชีกลาง` งบ `100000`
4. กดสร้าง → เห็น `draft-page` ภายใน 20 วินาที

![เคส dashboard: ฟอร์มสร้างโครงการ](test-evidence/02b-create-dialog.png)

---

## ขั้นที่ 6 — เดิน Phase 0 ถึง Phase 4

**ไฟล์เทสต์:** `wizard-flow.spec.ts` — *login, create project, walk Phase 0-4*  
**แชทร่าง:** `chat.spec.ts` — *Phase 0–1 is intake chat; upload then confirm-ready*

สร้างโครงการใหม่แล้วคลิกแถบ Phase ทีละขั้น ตรวจหัวข้อภาษาไทยของแต่ละขั้น  
แชทร่างต้องไม่มีข้อความ *โหลดห้องแชทไม่สำเร็จ*

### Phase 0 เตรียมข้อมูล

แชทโครงการ — ลากวางหลายไฟล์ได้ **ไม่ต้องเลือก 9 ประเภท** ต้นฉบับไป Mongo แล้วจัดเข้า s1–s13 / s4.1–s4.14

![เคส 5-phase: Phase 0 แชทอัปโหลดชุดใหญ่](test-evidence/03-phase-0-upload.png)

### Phase 1 ถามส่วนขาด

หัวข้อ *Phase 1: ถามส่วนขาดและยืนยันพร้อมร่าง* ตารางความครบถ้วน ปุ่มดึงอ้างอิงกฎหมาย ปุ่ม **พร้อมร่าง TOR แล้ว**

![เคส 5-phase: Phase 1 แชทถามส่วนขาด](test-evidence/04-phase-1-analysis.png)

หลังอัปโหลด/วางข้อความ (เคส `chat.spec.ts` ยิงวิเคราะห์จริงผ่าน LM Studio) ตารางมีแถวสถานะจากโมเดล แล้วรอ fill-references

![เคส intake: ตารางความครบถ้วนหลังแกะเอกสาร](test-evidence/04b-phase-1-coverage.png)

### Phase 2 ร่าง 13 หมวด

หัวข้อ *Phase 2: ร่างเนื้อหา TOR* หมวด 1 ขยายอยู่ มีปุ่ม **ร่างด้วย AI** และ **บันทึกหมวดนี้** หมวด HITL ติดคำว่าต้องให้เจ้าหน้าที่ยืนยัน

![เคส 5-phase: Phase 2](test-evidence/05-phase-2-draft.png)

### Phase 3 ทบทวน

หัวข้อ *Phase 3: ทบทวนและอนุมัติ* ความครบถ้วน 0/13 เมื่อยังไม่กรอก ปุ่มรัน Rule Engine และส่งขออนุมัติ

![เคส 5-phase: Phase 3](test-evidence/06-phase-3-review.png)

### Phase 4 เผยแพร่

หัวข้อ *Phase 4: เผยแพร่* ปุ่ม **ส่งออก Word** / **ส่งออก PDF** ข้อความว่า e-Bidding เป็นงานนอกแอป

![เคส 5-phase: Phase 4](test-evidence/07-phase-4-publish.png)

---

## ขั้นที่ 6b — ถาม-ตอบคลังความรู้

**ไฟล์เทสต์:** `chat.spec.ts` — *ถาม-ตอบ opens Open WebUI-like rooms*

เมนู **ถาม-ตอบ** เปิด `/chat` เห็นรายการห้อง ปุ่มห้องใหม่ กล่องพิมพ์ และชิปพรอมต์ (คุณสมบัติผู้เสนอราคา, งวดจ่าย, ค่าปรับ, ราคากลาง)  
ไม่ปนประวัติกับแชทร่างโครงการ

![เคส chat: หน้าถาม-ตอบ](test-evidence/13-kb-chat.png)

**ไฟล์เทสต์:** `chat.spec.ts` — *chat attach ingests into private KB list* (~1.1 นาที)

แนบไฟล์ `.txt` จริงเข้าคลังของฉัน (ingest + embeddings) เห็น `chat-attach-feedback` ข้อความ *เพิ่มเข้าคลังของฉันแล้ว* แล้วพิมพ์ถามโหมด **ของฉัน** รอคำตอบจาก Gemma

---

## ขั้นที่ 6c — ร่าง Phase 0 ต้องกดเริ่มต้นก่อน coverage

**ไฟล์เทสต์:** `chat.spec.ts` — *Phase 0–1 is intake chat; upload then confirm-ready*

Phase 0 มีปุ่ม **เริ่มต้น** (`intake-start-analyze`) ยังไม่มีตารางความครบ · อัปโหลดแล้วกดเริ่มต้นจึงเข้า Phase 1 · ไปสอบถามเพิ่ม Phase 2 · ยืนยันพร้อมร่าง Phase 3

![เคส intake: Phase 0 อัปโหลด](test-evidence/03-phase-0-upload.png)

![เคส intake: Phase 1 coverage](test-evidence/04b-phase-1-coverage.png)

---

## ขั้นที่ 7 — ร่างด้วย AI จริงผ่าน Gemma

**ไฟล์เทสต์:** `wizard-flow.spec.ts` — *Phase 2 AI draft uses LM Studio Gemma* (~7.0 นาที)

1. พิมพ์ข้อความโครงการยาวใน Phase 0 แล้วกดวิเคราะห์ (LM Studio จัดช่องจริง ไม่ mock)
2. รอ fill-references และเข้า Phase 2–3
3. กด `draft-ai-s1` (หมวดความเป็นมา)
4. รอจนปุ่มกลับมากดได้ (timeout 360 วินาที) และมีเนื้อหาในช่องร่าง
5. ต้องไม่มีข้อความ *ร่างด้วย AI ไม่สำเร็จ*

![เคส AI: หมวด 1 หลังกดร่างด้วย AI](test-evidence/08-phase-2-ai-draft.png)

---

## ขั้นที่ 8 — คู่มือในแอป

**ไฟล์เทสต์:** `webapp.spec.ts` — *help page tabs are usable*  
**ภาพแท็บอื่น:** `guide-shots.spec.ts`

คลิกแท็บภาพรวม / เข้าสู่ระบบ / แดชบอร์ด / ร่าง / ถาม-ตอบ / ฐานความรู้ / ตรวจสอบ / ผู้ดูแล / FAQ  
FAQ ต้องมี `google/gemma-4-e4b`, `text-embedding-embeddinggemma-300m`, `127.0.0.1:1234`

![คู่มือ — ภาพรวม](test-evidence/10a-help-overview.png)

![คู่มือ — เข้าสู่ระบบ](test-evidence/10g-help-login.png)

![คู่มือ — แดชบอร์ด](test-evidence/10b-help-dashboard.png)

![คู่มือ — ร่าง 5 Phase](test-evidence/10c-help-draft.png)

![คู่มือ — ถาม-ตอบ](test-evidence/10f-help-chat.png)

![คู่มือ — ตรวจสอบ](test-evidence/10d-help-review.png)

![คู่มือ — FAQ (เคสหลัก)](test-evidence/10-help-faq.png)

---

## ขั้นที่ 9 — ฐานความรู้ในเมนูหลัก

**ไฟล์เทสต์:** `webapp.spec.ts` — *knowledge base is in the main menu*

คลิก `nav-knowledge-base` URL `/knowledge-base` เห็นหัวข้อ **อัปโหลดเอกสารของฉัน** และ **เอกสารที่ผู้ใช้อัปโหลด (เฉพาะบัญชีนี้)**

![เคส webapp: ฐานความรู้ผู้ใช้](test-evidence/11-knowledge-base.png)

---

## ขั้นที่ 10 — ตรวจสอบ TOR สแตนด์อโลน

**ไฟล์เทสต์:** `webapp.spec.ts` — *standalone review page loads*

หน้า `/review` มีกล่องอัปโหลด รายการเอกสารอ้างอิงบังคับ และ stepper สามขั้น ปุ่ม **สกัดข้อความ** ยังกดไม่ได้จนกว่าจะมีไฟล์  
ลำดับจริง: เลือกไฟล์ → `POST /review/extract` ดูตัวอย่าง → **ยืนยันเริ่มตรวจสอบ** → Jaccard `compare-projects` → `POST /review/run` แล้วแสดงคะแนน/รายการพบ/ค่า Jaccard

**ไฟล์เทสต์เพิ่ม:** `webapp.spec.ts` — *standalone review extract then confirm run* (mock extract/run) เห็นตัวอย่างข้อความแล้วคะแนน 72/100

**ไฟล์เทสต์สด:** `realistic-flow.spec.ts` — อัปโหลด PDF/ข้อความจริง ไม่ `page.route()` extract/run แล้วรอคะแนนจาก Rule Engine; KB กด **ข้อมูลอื่น ๆ** อัปโหลด ดาวน์โหลด `download-mine-*` แล้วลบ; Phase 0 เห็นปุ่ม **เริ่มวิเคราะห์** โดยยังไม่เข้าตารางความครบ

![เคส webapp: ตรวจสอบ TOR](test-evidence/12-standalone-review.png)

![รายละเอียดการ์ดตรวจสอบ](test-evidence/12a-review-detail.png)

![KB ของฉันหลังอัปโหลดหมวดข้อมูลอื่น ๆ](test-evidence/11b-kb-mine-status.png)

---

## ขั้นที่ 10b — ผู้ตรวจสอบอนุมัติ/ส่งกลับ

**ภาพคู่มือ:** `guide-shots.spec.ts` (บัญชี `reviewer@example.go.th`)

โครงการสถานะ `in_review` แสดงปุ่ม **อนุมัติ** / **ส่งกลับ** เฉพาะ reviewer และ admin — เรียก `POST /projects/{id}/approve` หรือ `/reject`

![แดชบอร์ดผู้ตรวจสอบ](test-evidence/02c-reviewer-dashboard.png)

รหัสผ่านผิดบนหน้าเข้าสู่ระบบ:

![รหัสผ่านผิด](test-evidence/00c-login-error.png)

หมวด HITL เมื่อขยายหมวด 3 มีปุ่ม **เจ้าหน้าที่ยืนยันแล้ว**:

![HITL หมวดคุณสมบัติ](test-evidence/05b-hitl-confirm.png)

แท็บคู่มือฐานความรู้และผู้ดูแล:

![คู่มือ — ฐานความรู้](test-evidence/10e-help-kb.png)

![คู่มือ — ผู้ดูแล](test-evidence/10h-help-admin.png)

---

## ขั้นที่ 11 — หน้าผู้ดูแล (แม่แบบ, KB, ผู้ใช้, AI)

**ไฟล์เทสต์:** `admin.spec.ts` — *templates, knowledge base, users, and AI settings load*  
**ภาพแต่ละหน้า:** `guide-shots.spec.ts`

ล็อกอิน `admin@example.go.th` แล้วเดินเมนูผู้ดูแล

![แอดมิน — แม่แบบ](test-evidence/16-admin-templates.png)

![แอดมิน — ฐานความรู้ (จัดการ)](test-evidence/17-admin-kb.png)

![แอดมิน — ผู้ใช้ระบบ](test-evidence/18-admin-users.png)

โหมดในเครื่อง: `#ai-mode=on_prem` แชท `google/gemma-4-e4b` embeddings `text-embedding-embeddinggemma-300m` คลัง `pgvector`  
กดทดสอบการเชื่อมต่อ ต้องเห็นข้อความมีคำว่า *เชื่อมต่อ*  
สลับโหมดคลาวด์: รายการมี claude/openai/gemini **ไม่มี** `lm_studio` ช่องคีย์ Claude/OpenAI/Gemini โชว์ (รวม Bedrock / Azure Foundry / OpenAI-compatible)

![แอดมิน — ping LM Studio สำเร็จ](test-evidence/09-admin-ai-lm-studio.png)

![แอดมิน — ฟอร์มโหมดในเครื่อง](test-evidence/09a-admin-ai-local.png)

![แอดมิน — โหมดคลาวด์ (ไม่มี LM Studio)](test-evidence/09b-admin-ai-cloud.png)

---

## Coverage HTML

เสิร์ฟ `app/backend/htmlcov` ที่พอร์ต **8765**, `app/frontend/coverage` ที่ **8766**, `app/frontend/playwright-report` ที่ **8767** แล้วรัน `npm run test:e2e:reports`

Backend `coverage.py`: **86%** (10025 statements, 1410 miss) จากรัน `pytest -m "not live_llm" --cov=app`

![Coverage backend 84%](test-evidence/13-backend-coverage.png)

Frontend Istanbul/v8: statements **84.95%** (994/1170), lines **87.09%** (918/1054) — include ชุด `src/lib` + stores + draft Phase0–4 + `/review` + KB page

![Coverage frontend 86.51%](test-evidence/14-frontend-coverage.png)

---

## คำสั่งที่รันในรอบนี้

จาก `app/backend`:

```bash
python -m pytest tests -q --tb=short --cov=app --cov-report=term --cov-report=html
```

ผลที่ยืนยันแยกชุดบนโฮสต์ Python 3.14: `pytest -m "not live_llm"` **1500 ผ่าน** (ครอบคลุม **86%**) และ `pytest -m live_llm` **14 ผ่าน** เมื่อ LM Studio ฟังพอร์ต 1234 (Gemma + EmbeddingGemma) รวม `test_live_realistic_workflow.py`

จาก `app/frontend`:

```bash
npm run test:unit
npm run lint
npm run test:e2e:headed
npm run test:e2e:guide
```

Vitest **145 ผ่าน** / 34 ไฟล์ · ESLint สะอาด · headed **17 ผ่าน** (~14.0 นาที) · guide **3 ผ่าน** · reports **3 ผ่าน**

หลังแก้ UI ต้อง `docker compose -p tor-app --env-file .env up -d --build frontend backend` ก่อนรัน Playwright เพราะเทสต์ยิงคอนเทนเนอร์ที่พอร์ต 3000

ติดตั้ง: `14-INSTALLATION.md`  
คู่มือผู้ใช้: `13-USER_GUIDELINE.md`
