# เช็กลิสต์อัดวิดีโอเดโม — สี่เครื่องมือ + ตั้งค่า AI

สคริปต์สั้นสำหรับผู้บรรยาย คลิกตาม `data-testid` จริงในแอป อย่าคิดปุ่มที่ไม่มีบนจอ

**สเปกอัตโนมัติ:** `app/frontend/e2e/demo-walkthrough.spec.ts`  
ชุดนี้ใช้ `skipUnlessLive` — **ข้ามเองเมื่อไม่ได้ตั้ง `E2E=1`** จึงไม่ทำให้ CI ที่ไม่มีสแตกคอมโพสล้ม  
รันเฉพาะสเปกนี้ (ห้ามรันทั้งชุด e2e ถ้าไม่ตั้งใจ):

```bash
cd app/frontend
# สแตก Compose + seed ต้องขึ้นอยู่แล้ว
npx playwright test e2e/demo-walkthrough.spec.ts
```

สเปกเปิดวิดีโอด้วย `test.use({ video: "on" })` ในไฟล์นี้เท่านั้น ไม่เปลี่ยนค่าวิดีโอของสเปกอื่น  
ไฟล์ `.webm` อยู่ที่ `app/frontend/test-results/` — **อย่า commit วิดีโอ** และอย่า commit `.env` / โทเคน

บัญชีเดโม: `E2E_EMAIL` / `E2E_PASSWORD` (เจ้าหน้าที่) และ `E2E_ADMIN_EMAIL` สำหรับตั้งค่า AI

---

## คลิป 1 — ร่าง TOR ขั้นที่ ๐ ถึง ๔

เข้าจากเมนูซ้าย **ร่าง TOR** (`nav-draft`) หน้า `/draft` จะพาไปโครงการล่าสุด หรือแสดง `draft-index` ถ้ายังไม่มีโครงการ — สร้างจากแดชบอร์ด (`nav-projects` → `new-project` → กรอกชื่อ หน่วยงาน วงเงิน ประเภทจ้างพัฒนา)

แถบขั้น: `phase-0` … `phase-4`

### ขั้นที่ ๐ เตรียมข้อมูล

**พูด:** วางความต้องการแล้วอัปโหลดไฟล์ประกอบ จากนั้นกดวิเคราะห์ — ระบบจัดเข้าช่อง ไม่ดึงกฎหมายอัตโนมัติในขั้นนี้

1. วางข้อความใน `intake-paste`
2. แนบไฟล์ที่ `intake-upload` — รายการขึ้นที่ `phase0-file-list`
3. กด `intake-start-analyze` แล้วยืนยัน `confirm-phase-ok`
4. รอ `phase0-analyzing` («อย่าปิดหน้านี้») จนเข้าขั้นที่ ๑

### ขั้นที่ ๑ ผลวิเคราะห์

**พูด:** นี่คือช่องที่ระบบจัดจากเอกสาร ข้อเท็จจริงบังคับต้องครบก่อนร่าง

1. ชี้ตาราง `phase1-coverage` และแถวเช่น `coverage-row-s1`
2. กด `phase1-skip` เพื่อไปขั้นที่ ๒

### ขั้นที่ ๒ สอบถามเพิ่ม

**พูด:** บอทถามช่องที่ยังขาด ตอบเป็นภาษาพูดได้

1. ชี้ `phase2-qa`, `phase2-fact-chips`, แชท `chat-input` / `chat-send`
2. เมื่อพร้อมกด `intake-confirm-ready` แล้วยืนยัน `confirm-phase-ok`

### ขั้นที่ ๓ ร่างเนื้อหา

**พูด:** ระบบร่างครบหมวดตามประเภทงาน เจ้าหน้าที่เปิดหมวดแก้ได้

1. รอ `phase3-draft`, `draft-chat`, `phase3-all-drafted` และ `draft-chat-count` เป็น 16/16
2. เปิดหมวดด้วย `section-card-s1` … `section-card-s6` ตามที่ต้องการโชว์

**ใบประมาณ (`cost-worksheet`)** — มีในหมวดวงเงิน (s6) ของขั้นที่ ๓:

1. กด `section-card-s6`
2. ถ้าขึ้นแผง ให้ชี้ `cost-worksheet` คำเตือน `cost-worksheet-disclaimer` («ไม่ใช่ราคากลาง»)
3. ช่อง: `cost-worksheet-license` (ค่าลิขสิทธิ์) · `cost-worksheet-labor` (ค่าแรง) · `cost-worksheet-maintenance` (ค่าบำรุงรักษา) · `cost-worksheet-training` (ค่าอบรม)
4. รวมที่ `cost-worksheet-total` — กด `cost-worksheet-save` ได้
5. ถ้าแผงไม่ขึ้นหลังเปิด s6 ให้พูดว่า **«ยังไม่ขึ้นหน้า»** แล้วไปต่อ — อย่าคิดปุ่มเอง

**ขอบเขตอบรม (`training-scope`)** — มีเมื่อเปิดหัวข้อย่อยอบรมในขอบเขตของงาน (ประเภทจ้างพัฒนา / จัดซื้อครุภัณฑ์):

1. เปิดปุ่มหัวข้อ «ขอบเขตของงาน» จนเห็น `scope-subsection-editor`
2. กดชิปหัวข้ออบรม (`scope-sub-training`)
3. ถ้าขึ้นแผง ให้ชี้ `training-scope` แล้วกรอก `training-scope-cohorts` · `training-scope-hours` · `training-scope-attendees` · `training-scope-documents`
4. ดูข้อความรวมที่ `training-scope-preview`
5. ถ้าแผงไม่ขึ้น ให้พูดว่า **«ยังไม่ขึ้นหน้า»**

ถ้าแชทร่างค้นผลิตภัณฑ์มาให้ จะมี `draft-search-results` และต้องกด `draft-search-confirm` ก่อนแทรก — อย่าแทรกโดยไม่อยืนยัน

จากนั้นกด `phase3-confirm` แล้วยืนยัน `confirm-phase-ok`

### ขั้นที่ ๔ ทบทวน — คะแนนสามด้าน

**พูด:** ขั้นนี้ตรวจร่างกับ พ.ร.บ. ระเบียบ และเอกสารขั้นที่ ๐ ได้คะแนนรายด้าน ไม่ใช่ศูนย์ทั้งแผงเมื่อร่างมีเนื้อหา

1. ชี้ `phase4-review`, ตัวอย่างรวม `phase4-merged-preview`, คะแนนรวมกฎ `phase4-rule-score`
2. แผงสามด้าน `review-part-scores`:
   - `review-part-legal` — ส่วนที่คาดว่าผิดกฎหมาย
   - `review-part-lock-in` — ความเสี่ยง lock specs (รวม Oracle/IVM)
   - `review-part-project` — ความเสี่ยงบริหารโครงการ
3. อ่านคะแนน 0–100 และคำอธิบายใต้แต่ละส่วน
4. กด `run-review` ถ้ายังไม่มีคะแนน — แชททบทวนใช้ `review-chat-input` / `review-chat-send`
5. ส่งออก `export-docx` / `export-pdf` ได้จาก `phase4-export` — **อย่ากด `phase4-submit` ตอนอัดถ้ายังไม่อยากปิดโครงการ**

---

## คลิป 2 — ตรวจสอบ TOR

เข้าจาก **ตรวจสอบ TOR** (`nav-review`) หน้า `/review` (`review-page`)

**พูด:** อัปโหลดไฟล์ TOR ภายนอก สกัดข้อความก่อน แล้วค่อยยืนยันให้กฎตรวจ — ผลด้านขวาเป็นคะแนนรวมกับสามด้านชุดเดียวกับขั้นที่ ๔

1. ขั้น `review-stepper`: เลือกไฟล์ → สกัดข้อความ → ผลการตรวจสอบ
2. วางไฟล์ในพื้นที่อัปโหลด แล้วกด `review-extract`
3. อ่านตัวอย่างที่ `review-extract-preview` แล้วกด `review-confirm-run`
4. รอ `review-score` และ `review-result` («คะแนนความพร้อม»)
5. ชี้ `review-part-scores` อีกครั้ง: `review-part-legal` · `review-part-lock-in` · `review-part-project`
6. กลุ่มข้อตรวจ `review-finding-buckets` (`review-legal-findings` / `review-risk-findings`)

---

## คลิป 3 — วิเคราะห์ TOR

เข้าจาก **วิเคราะห์ TOR** (`nav-analyze`) หน้า `/analyze` (`analyze-page`) — สลับสี่แผงในหน้า ไม่เปลี่ยนเครื่องมือ

**พูด:** วางร่างหรือเลือกโครงการ แล้วดูสามด้านบวกข้อเสนอแนะ แต่ละหมวดที่แก้มีแหล่งออนไลน์ 5–10 แหล่งประกอบ ระบบไม่เขียนทับร่างให้อัตโนมัติ

1. วางข้อความใน `analyze-text` หรือเลือกโครงการที่ `analyze-project`
2. กด `analyze-run` รอ `analyze-summary` (คะแนนรวม)
3. สลับแท็บซ้าย `analyze-panels`:
   - `analyze-tab-legal` → แผง `analyze-panel-legal`
   - `analyze-tab-lock_in` → แผง `analyze-panel-lock_in`
   - `analyze-tab-project` → แผง `analyze-panel-project`
   - `analyze-tab-recommendations` → แผง `analyze-panel-recommendations`
4. ในข้อเสนอแนะ ชี้จำนวนแหล่ง `analyze-source-count-…` และรายการ `analyze-sources-…` (เป้า 5–10 ต่อหมวดที่แก้ เมื่อเปิดค้นออนไลน์)
5. คัดลอกข้อความแนะนำด้วย `analyze-copy-…` ได้ — ระบบไม่วางลงร่างเอง
6. ถ้าค้นเว็บยังไม่เปิด จะบอกจำนวนแหล่งจริง หรือว่าง — ยังอ่านสามด้านจากข้อความได้

---

## คลิป 4 — ถาม-ตอบ

เข้าจาก **ถาม-ตอบ** (`nav-chat`) หน้า `/chat` (`chat-page` / `chat-shell`)

**พูด:** คำตอบเปิดด้วยประโยคที่ตอบคำถามทันที โครงยืดตามคำถาม ไม่บังคับหัวข้อสามชื่อแบบเดิม ท้ายคำตอบมีแหล่งคลัง (RAG) และแหล่งออนไลน์คู่กัน

1. กด `chat-new-room`
2. พิมพ์คำถามชัดใน `chat-input` เช่น วงเงินวิธีเฉพาะเจาะจงตาม พ.ร.บ. 2560 แล้วกด `chat-send`
3. รอ `chat-msg-assistant` — อ่านย่อหน้าแรกว่าตรงคำถาม
4. ชี้แหล่งคลังที่ `chat-source-bar` / `chat-citation`
5. ชี้บล็อก **แหล่งออนไลน์** ที่ `chat-online-sources` (5–10 เมื่อค้นได้)
6. **อย่าพูดว่ามีหัวข้อตายตัว «สรุปคำตอบ / หลักที่เกี่ยวข้อง / ข้อควรระวัง»** — โครงเปลี่ยนตามคำถาม

---

## คลิป 5 — การตั้งค่า AI (ไม่โชว์โทเคน)

เข้าด้วยบัญชีผู้ดูแล → **การตั้งค่า AI** (`nav-admin-ai-settings`) หน้า `admin-ai-settings-page`

**พูด:** หน้านี้สลับโหมดและผู้ให้บริการ โทเคนไม่ขึ้นตัวอักษรปกติ — ช่องคีย์เป็นรหัสผ่าน อย่าคลิกโฟกัสช่องคีย์ตอนอัด

1. ชี้โหมด `#ai-mode` โมเดลแชท `#ai-llm` ฝังเวกเตอร์ `#ai-embed` คลัง `#vector-store`
2. ถ้าเป็น Bedrock ชี้ `#bedrock-model` / ภูมิภาคได้ — **อย่าเลื่อนไป Anthropic/OpenAI/Gemini** เพราะจะเปิดช่องคีย์
3. **ห้าม** พิมพ์ วาง หรือเปิดตาดู `#anthropic-key` `#openai-key` `#gemini-key` `#aws-key` `#aws-secret` `#azure-key` `#compat-key` `#custom-rag-key`
4. คีย์ค้นเว็บไม่ขึ้นหน้านี้ — อย่าเปิด `.env` บนจอ
5. กด `ai-settings-test` ได้ถ้าต้องการโชว์สถานะ `ai-settings-status` — อย่ากดบันทึกถ้าไม่ได้ตั้งใจเปลี่ยนเครื่องเดโม

---

## รายการ test id ที่ผู้บรรยายกด

### เมนูซ้าย

| id | ป้าย |
| --- | --- |
| `nav-draft` | ร่าง TOR |
| `nav-review` | ตรวจสอบ TOR |
| `nav-chat` | ถาม-ตอบ |
| `nav-analyze` | วิเคราะห์ TOR |
| `nav-projects` | แดชบอร์ด (สร้างโครงการ) |
| `nav-admin-ai-settings` | การตั้งค่า AI (แอดมิน) |

### ร่าง TOR

`phase-0` `phase-1` `phase-2` `phase-3` `phase-4` · `intake-paste` `intake-upload` `intake-start-analyze` `confirm-phase-ok` · `phase1-coverage` `phase1-skip` `coverage-row-s1` · `phase2-qa` `chat-input` `chat-send` `intake-confirm-ready` · `phase3-draft` `section-card-s6` `cost-worksheet` `cost-worksheet-license` `cost-worksheet-labor` `cost-worksheet-maintenance` `cost-worksheet-training` `cost-worksheet-save` · `scope-subsection-editor` `scope-sub-training` `training-scope` `training-scope-cohorts` `training-scope-hours` `training-scope-attendees` `training-scope-documents` · `phase3-confirm` · `phase4-review` `review-part-scores` `review-part-legal` `review-part-lock-in` `review-part-project` `run-review` `review-chat-input` `review-chat-send` `export-docx` `export-pdf`

### ตรวจสอบ TOR

`review-page` `review-stepper` `review-extract` `review-extract-preview` `review-confirm-run` `review-score` `review-result` `review-part-scores` `review-part-legal` `review-part-lock-in` `review-part-project`

### วิเคราะห์ TOR

`analyze-page` `analyze-text` `analyze-project` `analyze-run` `analyze-summary` `analyze-panels` `analyze-tab-legal` `analyze-tab-lock_in` `analyze-tab-project` `analyze-tab-recommendations` `analyze-panel-legal` `analyze-panel-lock_in` `analyze-panel-project` `analyze-panel-recommendations`

### ถาม-ตอบ

`chat-page` `chat-shell` `chat-new-room` `chat-input` `chat-send` `chat-msg-assistant` `chat-source-bar` `chat-citation` `chat-online-sources`

### ตั้งค่า AI

`admin-ai-settings-page` `ai-settings-test` `ai-settings-status` — อย่าโฟกัสช่องคีย์
