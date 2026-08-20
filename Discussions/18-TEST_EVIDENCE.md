# หลักฐานการทดสอบ — ผ่านทั้งหมด

วันที่ **20 สิงหาคม 2026** (รอบแก้ `repo_root` corpus · Amazon/Bedrock + SGLang + Custom RAG · SonarLint · unit + live_llm + E2E headed)  
สแตก Docker `tor-app` (postgres + mongo + neo4j + redis + minio) + LM Studio ที่ `http://127.0.0.1:1234`  
`GET http://localhost:4000/health` = `healthy` ทั้ง `postgres` `redis` `minio` `mongo` `neo4j`

เอกสารชุดปัจจุบันเรียง **13–20** (เพิ่ม `20-AWS_BEDROCK_SETUP.md`). หลักฐานภาพอยู่ใน `discussions/test-evidence/`

| โมเดล | ค่า |
|--------|-----|
| Chat (dev) | `google/gemma-4-e4b` |
| Embeddings (dev) | `text-embedding-embeddinggemma-300m` (768 มิติ) |
| Production แนะนำ | Amazon Bedrock (ดู `20-AWS_BEDROCK_SETUP.md`) |

ภาพถ่ายจาก Playwright แบบ **headed** (`slowMo` 250ms) หลังเคสผ่านแล้วเท่านั้น  
คู่มือผู้ใช้: `13-USER_GUIDELINE.md` · รายงานการทำงาน: `19-APPLICATION_OPERATING_REPORT.md`

---

## สรุปตัวเลข (รอบ 20 ส.ค. 2026 — คืน)

| ชุด | ผล | ความหมาย |
|-----|-----|----------|
| pytest ไม่รวม `live_llm` | **1451 ผ่าน**, **0 ข้าม**, 10 ไม่รวมในรอบนี้แล้วรันแยก · coverage **~84%** | แก้ `corpus.repo_root()` ให้เจอ `documents/sources` → เคส PDF บังคับไม่ skip อีก |
| pytest `live_llm` | **10 ผ่าน** (~1m12s) | LM Studio Gemma 4 + EmbeddingGemma ที่ :1234 |
| Vitest `npm run test:coverage` | **128 ผ่าน** / 30 ไฟล์ · Statements **88.93%** · Lines **90.17%** | Admin AI SGLang/Custom RAG · Bedrock-first |
| Playwright (แอป, 1 worker, **headed**) | **15 ผ่าน** / 0 ล้ม (~2.4 นาที รวม Phase 2 AI) | `npm run test:e2e:headed` — Chromium มองเห็นได้ |
| SonarLint (ไฟล์ที่แตะ) | แก้ S5332 / S6772 / S7744 | Docker-internal HTTP → NOSONAR · checkbox · chat-sse |

### สาเหตุที่เคย “1 ข้าม”

`test_live_mandatory_folders_when_present` ข้ามเมื่อ `list_mandatory_sources()` ว่าง — เพราะ `repo_root()` ใช้ `parents[3]` ชี้ไปโฟลเดอร์ `app/` แทน root ของ repo (PDF จริงอยู่ที่ `documents/sources/` แต่ path ผิด)  
แก้แล้ว: เดินหา parent ที่มี `documents/sources` → พบ **27** ไฟล์บังคับ · เคสนี้ **ผ่าน** ไม่ skip

### สิ่งที่ตรวจเพิ่มในรอบนี้

- Admin → Amazon Bedrock เป็นตัวเลือก production แนะนำ · SGLang / Custom RAG ในฟอร์ม
- FAQ ช่วยเหลือระบุ `google/gemma-4-e4b` + `text-embedding-embeddinggemma-300m` + `127.0.0.1:1234`
- Redis LLM admission + SSE `queued`/`started` + UI รอคิว
- `index.html` (จำลอง GitHub Pages) ปรับให้ตรงแอป: Bedrock-first, SGLang, Custom RAG, FAQ/ตัวเลขเทสต์
- Phase 2 AI draft ผ่านด้วย LM Studio Gemma (~1.8 นาที)

---

## รายงาน Playwright — 15 เคสแอป (headed)

รัน: `cd app/frontend && npm run test:e2e:headed` (1 worker, Chromium มองเห็นได้)  
Chromium, viewport 1440×900, ภาษา th-TH, ยิง `http://localhost:3000` · `HEADED=1` + `screenshot: on` + `slowMo: 250`

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

หลังอัปโหลด (เคส `chat.spec.ts` ที่ mock API) ตารางมีแถว `filled` และปุ่มยืนยันพร้อมร่าง

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

---

## ขั้นที่ 7 — ร่างด้วย AI จริงผ่าน Gemma

**ไฟล์เทสต์:** `wizard-flow.spec.ts` — *Phase 2 AI draft uses LM Studio Gemma* (~35 วินาที)

1. เข้า Phase 2
2. กด `draft-ai-s1` (หมวดความเป็นมา)
3. รอจนปุ่มกลับมากดได้ (timeout 180 วินาที)
4. ต้องไม่มีข้อความ *ร่างด้วย AI ไม่สำเร็จ*

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

หน้า `/review` มีกล่องอัปโหลด รายการเอกสารอ้างอิงบังคับ ปุ่ม **เริ่มตรวจสอบ TOR** ยังกดไม่ได้จนกว่าจะมีไฟล์  
ลำดับจริงเมื่อกดเริ่ม: extract ไฟล์หลัก → extract คู่เทียบ → Jaccard `compare-projects` → `POST /review/run` แล้วแสดงคะแนน/รายการพบ/ค่า Jaccard

![เคส webapp: ตรวจสอบ TOR](test-evidence/12-standalone-review.png)

![รายละเอียดการ์ดตรวจสอบ](test-evidence/12a-review-detail.png)

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

Backend `coverage.py`: **85%** (9527 statements, 1398 miss) — ลดจาก 87% เพราะโมดูล RAG/Graph/Mongo/`knowledge_base.mine` ที่เพิ่มในรอบนี้

![Coverage backend 87%](test-evidence/13-backend-coverage.png)

Frontend Istanbul/v8: statements **89.8%** (660/735), lines **91.4%** (602/659) — รวมหน้า `/knowledge-base`

![Coverage frontend 91.39%](test-evidence/14-frontend-coverage.png)

---

## คำสั่งที่รันในรอบนี้

จาก `app/backend`:

```bash
python -m pytest tests -q --tb=short --cov=app --cov-report=term --cov-report=html
```

ผลที่ยืนยันแยกชุด: รอบเต็มบนโฮสต์ Python 3.14 ได้ **1378 ผ่าน** (รวม `test_live_lm_studio.py` เมื่อ `lms server` ฟังพอร์ต 1234 และโมเดล Gemma + EmbeddingGemma โหลดแล้ว)

จาก `app/frontend`:

```bash
npm run test:coverage
npm run test:e2e:headed
npm run test:e2e:guide
npm run test:e2e:reports
```

หลังแก้ UI ต้อง `docker compose -p tor-app --env-file .env up -d --build frontend backend mongo neo4j` ก่อนรัน Playwright เพราะเทสต์ยิงคอนเทนเนอร์ที่พอร์ต 3000

ติดตั้ง: `14-INSTALLATION.md`  
คู่มือผู้ใช้: `13-USER_GUIDELINE.md`
