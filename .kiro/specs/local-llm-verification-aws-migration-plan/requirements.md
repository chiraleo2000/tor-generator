# Requirements Document

## Introduction

งานนี้แบ่งเป็น **สามเฟส** ที่มีลำดับชัดเจนและมี "เกต" (gate) กั้น โดย **เฟส 1 และเฟส 2 เป็นงานวางแผนและจัดทำเอกสาร (planning & documentation) เท่านั้น** (ผลลัพธ์เป็นเนื้อหา Markdown ไม่มีการแก้ไขซอร์สโค้ด ไม่มีการติดตั้งโครงสร้างพื้นฐานคลาวด์จริง และไม่มีการดีพลอย AWS จริง) ส่วน **เฟส 3 เป็นงานแก้ไขซอร์สโค้ดจริง (real code changes)** เพื่อทำให้ระบบย่อยการร่าง (draft) และการตรวจ (review) มีความเสถียรและรองรับงานปริมาณมาก (large workloads)

ผลลัพธ์เอกสารของเฟส 1 และเฟส 2 จะถูก **รวมเป็นไฟล์ Markdown ฉบับเดียว (Combined_Report)** ที่เสนอไว้ที่ `Discussions/28-VERIFICATION-AND-MIGRATION.md` ซึ่งบรรจุทั้งส่วนรายงานผลการตรวจสอบ (Verification_Report) และส่วนแผนย้ายระบบ (Migration_Plan) ไว้ในไฟล์เดียว แทนการแยกเป็นสองไฟล์

1. **เฟสตรวจสอบบน Local LLM (Local Verification) — จัดทำเอกสาร:** ทดสอบกระบวนการทำงานทั้งหมดของแอปแบบครบวงจร (end-to-end) โดยรันบน Local LLM ก่อน ครอบคลุมสามเวิร์กโฟลว์หลัก (ร่าง TOR / ตรวจสอบ TOR / ถาม-ตอบฐานความรู้) การ seed คลังความรู้ (RAG) และบริการหลักใน Docker ทั้งหมดต้อง healthy จากนั้นบันทึกหลักฐานเป็นส่วนหนึ่งของ Combined_Report ตามรูปแบบเดียวกับ `Discussions/18-TEST_EVIDENCE.md`
2. **เฟสวางแผนย้ายขึ้น AWS (AWS Migration Plan) — จัดทำเอกสาร:** จัดทำแผนการปรับไปใช้บริการ AWS Cloud เป็นส่วนหนึ่งของ Combined_Report เท่านั้น (การจับคู่บริการ การเปลี่ยนค่าคอนฟิก/ตัวแปรสภาพแวดล้อม ขั้นตอนตัดระบบ (cutover) แผนย้อนกลับ (rollback) และความเสี่ยง) โดย **อ้างอิง** เอกสารเดิม `Discussions/20`, `24`, `25`, `26`, `27` แทนการทำซ้ำเนื้อหา และเฟสนี้จะถูก **บล็อก** จนกว่าเฟสตรวจสอบบน Local LLM จะผ่านและมีหลักฐานยืนยัน
3. **เฟสทำให้ระบบร่าง/ตรวจเสถียรและรองรับงานขนาดใหญ่ (Stability & Scale) — แก้ไขซอร์สโค้ดจริง:** ปรับปรุงโค้ดของระบบย่อยการร่างและการตรวจให้รองรับหลายอินสแตนซ์และงานที่ใช้เวลานาน อย่างน้อยครอบคลุมการย้ายสถานะงานร่างออกจากหน่วยความจำ (Draft_Job_Store) การบังคับการตรวจครบถ้วนฝั่งเซิร์ฟเวอร์ก่อนส่งตรวจ และความเสถียรของงานร่าง/ตรวจขนาดใหญ่ เฟสนี้อยู่ **หลังเกต (Verification_Gate)** เช่นเดียวกับเฟส 2

**Non-goals (นอกขอบเขต):** การดีพลอย AWS จริง, การจัดสรร (provision) โครงสร้างพื้นฐานคลาวด์, การย้ายข้อมูลจริงขึ้นคลาวด์ (การแก้ไขซอร์สโค้ดของแอปอยู่ในขอบเขตเฉพาะเฟส 3 เท่านั้น)

## Glossary

- **Verification_Author (ผู้จัดทำการตรวจสอบ):** ผู้รับผิดชอบรันการทดสอบบน Local LLM และบันทึกหลักฐาน — เป็นผู้กระทำ (actor) หลักของเฟส 1
- **Plan_Author (ผู้จัดทำแผน):** ผู้รับผิดชอบเขียนเอกสารแผนย้ายขึ้น AWS — เป็นผู้กระทำหลักของเฟส 2
- **Verification_Report (รายงานการตรวจสอบ):** ส่วนเนื้อหา Markdown ที่บันทึกหลักฐานผลการทดสอบบน Local LLM ตามรูปแบบ `Discussions/18-TEST_EVIDENCE.md` (เป็นส่วนหนึ่งของ Combined_Report)
- **Migration_Plan (แผนย้ายระบบ):** ส่วนเนื้อหา Markdown ที่บรรยายแนวทางและแผนการปรับไปใช้ AWS (เป็นส่วนหนึ่งของ Combined_Report)
- **Combined_Report (เอกสารรวม):** ไฟล์ Markdown ฉบับเดียวที่รวมทั้ง Verification_Report และ Migration_Plan (เสนอ `Discussions/28-VERIFICATION-AND-MIGRATION.md`)
- **Draft_Job_Store (ที่เก็บสถานะงานร่าง):** ที่เก็บสถานะงานร่าง ปัจจุบันเป็น in-memory (`_DRAFT_JOBS` ใน `app/api/v1/endpoints/draft_chat.py`) เป้าหมายย้ายไปที่เก็บนอกโปรเซส (Redis) เพื่อรองรับหลายอินสแตนซ์
- **Admission_Queue (คิวรับงาน):** คิว Redis ที่มีอยู่แล้ว (`llm:admit:*` ใน `app/llm_admission.py`) ใช้เป็นแบบอย่างการย้าย Draft_Job_Store
- **Local_LLM:** ผู้ให้บริการโมเดลภาษาแบบรันในเครื่อง ค่าเริ่มต้นคือ LM Studio ที่ `http://127.0.0.1:1234/v1` (จาก backend ใน Docker ใช้ `host.docker.internal`) โมเดลแชท `google/gemma-4-e4b` และ embeddings `text-embedding-embeddinggemma-300m` (768 มิติ) — ครอบคลุมทางเลือก local อื่น (ollama, llama_cpp, sglang) ด้วย
- **Core_Services (บริการหลัก):** บริการใน `docker-compose.yml` โปรเจกต์ `tor-app` ได้แก่ frontend (:3000), backend (:4000), Postgres+pgvector (:5432), Redis (:6379), MinIO (:9000/:9001), MongoDB (:27017), Neo4j (:7474/:7687)
- **Health_Endpoint:** `GET http://localhost:4000/health` ที่ตรวจสถานะ postgres, redis, minio, mongo, neo4j
- **Draft_Workflow (เวิร์กโฟลว์ร่าง TOR):** เส้นทางห้าขั้นที่ `/projects/{id}/draft` ตาม `Discussions/21-WORKFLOW_DRAFT_TOR.md`
- **Review_Workflow (เวิร์กโฟลว์ตรวจสอบ TOR):** เส้นทางที่ `/review` และขั้นที่ ๔ ในร่าง ตาม `Discussions/22-WORKFLOW_REVIEW_TOR.md`
- **KB_QA_Workflow (เวิร์กโฟลว์ถาม-ตอบฐานความรู้):** เส้นทางที่ `/chat` และ `/knowledge-base` ตาม `Discussions/23-WORKFLOW_KB_QA.md`
- **RAG_Seed (การ seed คลังความรู้):** การสร้างคลังกลางด้วย `python -m app.seed_raw_docs` (คลังที่แชทใช้จริง จาก PDF ใน `documents/sources/`) และคำสั่ง seed ที่เกี่ยวข้อง
- **Mandatory_Groups (กลุ่มบังคับ RAG):** `mandatory_handbook`, `mandatory_raw` และกลุ่ม `user` ต่อผู้ใช้
- **Test_Suites (ชุดทดสอบ):** pytest (มาร์กเกอร์ `not live_llm` และ `live_llm`), Vitest (frontend unit), Playwright (E2E)
- **Verification_Gate (เกตตรวจสอบ):** เงื่อนไขว่า Verification_Report ต้องแสดงผลผ่านครบก่อนที่ Migration_Plan จะถือว่าเริ่มได้
- **Reference_Docs (เอกสารอ้างอิง AWS):** `Discussions/20-AWS_BEDROCK_SETUP.md`, `24-AWS_CLOUD_OVERVIEW.md`, `25-AWS_SERVICE_CATALOG.md`, `26-AWS_INSTALL_AND_WIRING.md`, `27-AWS_CODE_AND_CUTOVER.md`

## Requirements

### Requirement 1: ยืนยันความพร้อมของสภาพแวดล้อม Local ก่อนตรวจสอบ

**User Story:** As a Verification_Author, I want ยืนยันว่าบริการหลักและ Local LLM พร้อมทำงาน, so that การทดสอบแบบครบวงจรวางอยู่บนฐานที่น่าเชื่อถือ

#### Acceptance Criteria

1. WHEN Verification_Author เริ่มเฟสตรวจสอบ, THE Verification_Report SHALL บันทึกผลการเรียก Health_Endpoint ภายใน 10 วินาที ที่แสดงสถานะ `healthy` ของบริการทั้งห้ารายการ ได้แก่ postgres, redis, minio, mongo และ neo4j
2. THE Verification_Report SHALL ระบุค่าผู้ให้บริการโมเดลที่ใช้เป็น Local_LLM พร้อมชื่อโมเดลแชทและโมเดล embeddings ที่ใช้จริงในรอบทดสอบ
3. IF บริการหลักใด ๆ ใน Core_Services รายงานสถานะไม่ใช่ `healthy`, THEN THE Verification_Report SHALL บันทึกชื่อบริการที่ไม่พร้อมทั้งหมด และบันทึกผลเฟสตรวจสอบเป็น "ไม่ผ่าน"
4. THE Verification_Report SHALL บันทึกว่าค่า `DEPLOYMENT_MODE` เท่ากับ `on_prem` และค่า `LLM_PROVIDER` เป็นหนึ่งในผู้ให้บริการ Local_LLM ได้แก่ lm_studio, ollama, llama_cpp หรือ sglang ในรอบทดสอบ
5. IF การเรียก Health_Endpoint ไม่ได้รับการตอบกลับภายใน 10 วินาที หรือไม่สามารถเชื่อมต่อได้, THEN THE Verification_Report SHALL บันทึกว่า Health_Endpoint ไม่สามารถเข้าถึงได้ และบันทึกผลเฟสตรวจสอบเป็น "ไม่ผ่าน"

### Requirement 2: seed คลังความรู้ RAG สำหรับการทดสอบ

**User Story:** As a Verification_Author, I want seed คลังความรู้ให้พร้อมก่อนทดสอบเวิร์กโฟลว์, so that การค้นแบบ RAG มีข้อมูลจริงให้ค้น

#### Acceptance Criteria

1. WHEN Verification_Author รันขั้นตอน RAG_Seed จนเสร็จ, THE Verification_Report SHALL บันทึกคำสั่ง seed ที่ใช้ครบถ้วน, สถานะการจบงาน (exit status สำเร็จ), และจำนวนเอกสารทั้งหมดที่ถูกนำเข้าคลังกลาง
2. THE Verification_Report SHALL ยืนยันว่าคลังกลางที่แชทใช้จริงถูกสร้างจากคำสั่ง `python -m app.seed_raw_docs` โดยรันจาก host (ไม่ใช่ภายใน container) และบันทึกเหตุผลของข้อจำกัดนี้ว่าการ bind-mount ชื่อไฟล์ภาษาไทยภายใน container ทำให้เกิด Errno 5
3. THE Verification_Report SHALL บันทึกจำนวนเอกสารพร้อมค้นในแต่ละกลุ่มบังคับหลังการ seed โดยยืนยันว่ากลุ่ม `mandatory_handbook` มีเอกสารพร้อมค้นอย่างน้อย 1 รายการ และกลุ่ม `mandatory_raw` มีเอกสารพร้อมค้นอย่างน้อย 1 รายการ
4. IF Neo4j ไม่พร้อมทำงานระหว่างการค้น, THEN THE Verification_Report SHALL บันทึกสถานะ `graph_degraded` และยืนยันว่าการตอบแชทยังทำงานได้จากชิ้นข้อความเวกเตอร์ โดยคำตอบอาจว่างเปล่าได้หากชิ้นข้อความไม่เพียงพอ
5. IF คำสั่ง seed จบด้วยสถานะล้มเหลว, THEN THE Verification_Report SHALL บันทึกสถานะล้มเหลว, ข้อความบ่งชี้สาเหตุที่คำสั่งคืนมา, และยืนยันว่าคลังกลางเดิม (ก่อนรัน seed) ไม่ถูกใช้เป็นข้อมูลทดสอบที่ผ่าน
6. WHEN Verification_Author เริ่มการทดสอบที่ต้องใช้คลังความรู้, THE Verification_Report SHALL แยกบันทึกวัตถุประสงค์ของแต่ละคำสั่ง seed โดยระบุว่า `seed_raw_docs` สร้างคลังกลาง RAG, `seed_db` สร้างข้อมูลเริ่มต้น, และ `seed_kb` ใช้สำหรับส่วนสกัดงานวิจัยเท่านั้น

### Requirement 3: ตรวจสอบเวิร์กโฟลว์ร่าง TOR แบบครบวงจรบน Local LLM

**User Story:** As a Verification_Author, I want ทดสอบเส้นทางร่าง TOR ห้าขั้นแบบครบวงจร, so that ยืนยันว่าการร่างด้วย Local LLM ทำงานถูกต้อง

#### Acceptance Criteria

1. WHEN Verification_Author รันเวิร์กโฟลว์ Draft_Workflow ครบเส้นทางขั้น ๐ ถึงขั้น ๔, THE Verification_Report SHALL บันทึกผลแบบ ผ่าน/ไม่ผ่าน ของแต่ละขั้นทั้งห้าขั้น ได้แก่ ขั้น ๐ การอัปโหลด/วางเอกสารและการเริ่มวิเคราะห์ ขั้น ๑ ตารางความครบ ๒๗ ช่อง (หมวด s1 ถึง s13 และหัวข้อย่อย s4.1 ถึง s4.14) ขั้น ๒ การเติมช่องผ่านแชท ขั้น ๓ การร่างครบ ๑๓ หมวดรวมหัวข้อย่อย s4.1 ถึง s4.14 และขั้น ๔ การทบทวนและส่งออก
2. WHEN ขั้นที่ ๔ รันการตรวจด้วยเครื่องยนต์กฎเสร็จสิ้น, THE Verification_Report SHALL บันทึกคะแนนคุณภาพเป็นค่าตัวเลข ๐ ถึง ๑๐๐ และผลการผ่านเกณฑ์ที่คะแนน ≥ ๗๐
3. WHEN การตรวจในโครงการขั้นที่ ๔ เสร็จสิ้น, THE Verification_Report SHALL บันทึกสถานะการตรวจเป็น `valid` หรือ ไม่ `valid`
4. WHEN การร่างครบ ๑๓ หมวดและเจ้าหน้าที่ส่งขออนุมัติ, THE Verification_Report SHALL บันทึกการเปลี่ยนสถานะโครงการเป็น `in_review`
5. WHEN ผู้ตรวจดำเนินการหลังโครงการอยู่ในสถานะ `in_review`, THE Verification_Report SHALL บันทึกผลการอนุมัติ (สถานะโครงการเปลี่ยนเป็น `approved`) หรือการส่งกลับ (สถานะโครงการเปลี่ยนเป็น `rejected`)
6. WHEN การส่งออกเอกสารเสร็จสิ้น, THE Verification_Report SHALL บันทึกผลการส่งออกไฟล์รูปแบบ DOCX และผลการส่งออกไฟล์รูปแบบ PDF แยกกันเป็นผลแบบ สำเร็จ/ไม่สำเร็จ พร้อมยืนยันการมีอยู่ของไฟล์แต่ละรูปแบบ
7. IF ขั้นตอนใดของ Draft_Workflow (ขั้น ๐ ถึงขั้น ๔) ล้มเหลว, THEN THE Verification_Report SHALL บันทึกหมายเลขขั้นที่ล้มเหลวพร้อมข้อความข้อผิดพลาดที่สังเกตได้ และบันทึกว่าสถานะโครงการคงเดิมโดยไม่เลื่อนไปขั้นถัดไป

### Requirement 4: ตรวจสอบเวิร์กโฟลว์ตรวจสอบ TOR แบบครบวงจรบน Local LLM

**User Story:** As a Verification_Author, I want ทดสอบเส้นทางตรวจสอบ TOR ทั้งหน้าล้วนและในโครงการ, so that ยืนยันว่าเครื่องยนต์กฎและเอเจนต์ทบทวนทำงานถูกต้องบน Local LLM

#### Acceptance Criteria

1. WHEN Verification_Author รัน Review_Workflow บนหน้า `/review`, THE Verification_Report SHALL บันทึกข้อความที่สกัดได้ (แสดงตัวอย่างไม่เกิน ๒๐,๐๐๐ ตัวอักษร) การยืนยันเริ่มตรวจ และคะแนนความพร้อม ๐–๑๐๐ พร้อมรายการข้อค้นพบที่ได้จากเครื่องยนต์กฎ โดยถือคะแนน ≥ ๗๐ เป็นโทนผ่านบนจอ
2. WHERE มีไฟล์เปรียบเทียบตั้งแต่ ๒ ถึง ๕ ฉบับ, THE Verification_Report SHALL บันทึกค่าความคล้ายแบบ Jaccard ในช่วง ๐.๐–๑.๐ ต่อคู่เอกสาร โดยถือค่า ≥ ๐.๕ เป็นโทนผ่านบนจอเท่านั้น (ไม่ใช่เกณฑ์ทางกฎหมาย)
3. IF เอพีไอเปรียบเทียบเอกสารไม่พร้อมให้บริการ (คืนสถานะ ๔๐๔/๔๐๕/๕๐๑), THEN THE Verification_Report SHALL บันทึกการใช้เส้นทางสำรองคำนวณความคล้ายในเบราว์เซอร์ และค่าความคล้ายที่ได้
4. WHEN Verification_Author รันการตรวจในขั้นที่ ๔ ของโครงการร่าง, THE Verification_Report SHALL บันทึกคะแนนคุณภาพ ๐–๑๐๐ รายการข้อค้นพบ ความเห็นรวม และข้อเสนอแนะจากเอเจนต์ทบทวนไม่เกิน ๒๐ ข้อ ในหมวดความสอดคล้องกฎหมาย/ความชัดเจน/ความครบถ้วน/ความสม่ำเสมอ
5. IF เอเจนต์ทบทวนคืนค่า JSON ที่แจงไม่สำเร็จ, THEN THE Verification_Report SHALL บันทึกการใช้เส้นทางสำรอง (fallback) และคืนผลจากเครื่องยนต์กฎโดยไม่สูญเสียคะแนนและข้อค้นพบที่คำนวณได้แล้ว

### Requirement 5: ตรวจสอบเวิร์กโฟลว์ถาม-ตอบฐานความรู้แบบครบวงจรบน Local LLM

**User Story:** As a Verification_Author, I want ทดสอบการถาม-ตอบและการจัดการฐานความรู้, so that ยืนยันว่า RAG และการสตรีมคำตอบด้วย Local LLM ทำงานถูกต้อง

#### Acceptance Criteria

1. WHEN Verification_Author ส่งคำถามภาษาไทยที่ `/chat` ด้วยขอบเขตค้น `both`, THE Verification_Report SHALL บันทึกว่าได้รับสตรีมคำตอบที่จบด้วยเหตุการณ์ `done` และมีชิปอ้างอิง (citation) อย่างน้อย ๑ รายการที่ระบุชื่อไฟล์ต้นฉบับจากคลังกลางหรือเอกสารของผู้ใช้
2. IF สตรีมคำตอบสิ้นสุดด้วยเหตุการณ์ `error` หรือคำตอบไม่มีชิปอ้างอิงเลย, THEN THE Verification_Report SHALL บันทึกผลว่าไม่ผ่านพร้อมเหตุการณ์ที่ได้รับและข้อความสถานะที่ระบบแสดง
3. WHEN Verification_Author แนบไฟล์ PDF, DOCX หรือ TXT ขนาดไม่เกิน ๒๐ MB เข้าคลังส่วนตัวจากแชท, THE Verification_Report SHALL บันทึกว่าไฟล์ถูก ingest เข้าหมวด «ข้อมูลอื่น ๆ» (category=other) จนถึงสถานะ «ใช้กับ RAG ได้» และเมื่อถามในขอบเขตค้น `mine` แล้วได้คำตอบที่มีชิปอ้างอิงระบุไฟล์นั้น
4. IF Verification_Author แนบไฟล์ที่ไม่ใช่ PDF/DOCX/TXT หรือมีขนาดเกิน ๒๐ MB จากแชท, THEN THE Verification_Report SHALL บันทึกว่าระบบปฏิเสธไฟล์นั้นและไม่มีการ ingest เข้าคลังส่วนตัว
5. WHEN Verification_Author อัปโหลด ดาวน์โหลด (ผ่าน `GET /api/v1/knowledge-base/mine/{id}/file`) และลบไฟล์ของตนที่หน้า `/knowledge-base`, THE Verification_Report SHALL บันทึกผลของแต่ละการกระทำแยกกันและบันทึกผลของแต่ละการกระทำทันทีที่เสร็จสิ้น (ไม่ต้องรอให้ครบทั้งสามการกระทำ) ว่า อัปโหลดแล้วไฟล์ปรากฏในหมวด «เอกสารของฉัน» ดาวน์โหลดแล้วได้ไฟล์เดิม และลบแล้วไฟล์หายจากรายการ
6. IF ผู้ใช้พยายามค้นด้วยขอบเขต `mine` ต่อไฟล์ที่มี `owner_id` ของผู้ใช้อื่น, THEN THE Verification_Report SHALL ยืนยันว่าไฟล์นั้นไม่ปรากฏในผลค้นตามการควบคุมสิทธิ์ (ACL) และผลค้นที่ไม่มีไฟล์ของตนจะคืนค่าว่างแทนการรั่วไฟล์ของผู้อื่น

### Requirement 6: รันชุดทดสอบอัตโนมัติที่มีอยู่และบันทึกผล

**User Story:** As a Verification_Author, I want รันชุดทดสอบที่มีอยู่กับ Local LLM, so that มีหลักฐานเชิงปริมาณประกอบการตรวจครบวงจร

#### Acceptance Criteria

1. WHEN Verification_Author รัน Test_Suites เสร็จสิ้น, THE Verification_Report SHALL บันทึกจำนวนเคสที่ผ่าน (passed) ข้าม (skipped) และล้มเหลว (failed) เป็นค่าจำนวนเต็มแยกตามแต่ละชุด ได้แก่ pytest ชุด `not live_llm` pytest ชุด `live_llm` Vitest และ Playwright
2. WHEN Verification_Author รัน Test_Suites เสร็จสิ้น, THE Verification_Report SHALL บันทึกค่าความครอบคลุมโค้ด (coverage) เป็นเปอร์เซ็นต์ (0 ถึง 100) แยกตามแหล่งที่มา คือ pytest และ Vitest
3. THE Verification_Report SHALL ระบุว่าชุด `live_llm` ของ pytest และเคส Playwright เชื่อมต่อกับ Local_LLM จริง โดยบันทึกหลักฐานที่สังเกตได้ว่าชุดทดสอบถูกกำหนดค่าให้เชื่อมต่อกับ LM Studio ที่พอร์ต 1234 (และสำหรับ Playwright คือ Docker ที่พอร์ต 3000) โดยไม่ใช้ค่าจำลอง (mock) แม้การเชื่อมต่อจริงอาจไม่สำเร็จ
4. IF เคสทดสอบใดล้มเหลว, THEN THE Verification_Report SHALL บันทึกชื่อชุดทดสอบ ชื่อเคส และสาเหตุที่สังเกตได้จากผลลัพธ์การรัน
5. IF ชุดทดสอบใดไม่สามารถเริ่มรันหรือรันไม่เสร็จสิ้น, THEN THE Verification_Report SHALL บันทึกชื่อชุดทดสอบนั้นพร้อมสถานะว่ารันไม่สำเร็จและสาเหตุที่สังเกตได้

### Requirement 7: จัดทำรายงานหลักฐานการตรวจสอบเป็น Markdown

**User Story:** As a Verification_Author, I want รวบรวมหลักฐานทั้งหมดเป็นรายงาน Markdown, so that ผลการตรวจครบวงจรถูกบันทึกอย่างตรวจสอบย้อนกลับได้

#### Acceptance Criteria

1. THE Verification_Report SHALL เป็นไฟล์ Markdown ที่มีหัวข้อครบทุกส่วนตามโครงของ `Discussions/18-TEST_EVIDENCE.md` ได้แก่ ส่วนหัวระบุวันที่และสภาพแวดล้อม, ส่วนตารางสรุปตัวเลข, ส่วนอธิบายรายเคสพร้อมภาพ และส่วนสรุป Coverage
2. THE Verification_Report SHALL ระบุวันที่ทดสอบในรูปแบบ วัน–เดือน–พ.ศ. (เช่น 25 สิงหาคม 2026), เวอร์ชันแอป `v0.2.4` และสภาพแวดล้อมที่ใช้ ได้แก่ สแตก Docker `tor-app` และ Local_LLM ที่ระบุ endpoint
3. THE Verification_Report SHALL สรุปผลของทั้งสามเวิร์กโฟลว์และชุดทดสอบเป็นตารางที่มีอย่างน้อยคอลัมน์ ชื่อรายการ, สถานะ (ค่าใดค่าหนึ่งใน ผ่าน / ไม่ผ่าน / ข้าม) และจำนวนที่ผ่าน โดยชุดที่มีค่าครอบคลุมโค้ดต้องระบุเปอร์เซ็นต์ Coverage
4. IF รายการเวิร์กโฟลว์หรือชุดทดสอบใดไม่มีผลลัพธ์หรือถูกข้าม, THEN THE Verification_Report SHALL แสดงหมายเหตุระบุเหตุผลในแถวนั้นของตาราง โดยหมายเหตุดังกล่าวอาจปรากฏร่วมกับสถานะใดก็ได้ ไม่จำกัดเฉพาะสถานะ ข้าม
5. WHERE มีภาพหลักฐานประกอบ, THE Verification_Report SHALL อ้างอิงไฟล์ภาพในโฟลเดอร์ `Discussions/test-evidence/` โดยทุกลิงก์ที่อ้างอิงต้องชี้ไปยังไฟล์ภาพที่มีอยู่จริงในโฟลเดอร์ดังกล่าว

### Requirement 8: เกตกั้นก่อนเริ่มแผนย้ายขึ้น AWS

> **หมายเหตุ:** Verification_Gate ในข้อกำหนดนี้เป็นเกตกั้นก่อน **ทั้งส่วนแผนย้ายระบบ (Migration_Plan) ในเฟส 2 และงานแก้ไขซอร์สโค้ดในเฟส 3 (Req 11-13)** กล่าวคือ ทั้งสองงานที่อยู่หลังเกตจะเริ่มได้ก็ต่อเมื่อ Verification_Report แสดงผลผ่านครบตามเงื่อนไขที่ระบุด้านล่าง

**User Story:** As a Plan_Author, I want ให้แผนย้ายขึ้น AWS เริ่มได้ก็ต่อเมื่อการตรวจสอบ Local ผ่าน, so that ไม่วางแผนย้ายระบบบนฐานที่ยังไม่ยืนยัน

#### Acceptance Criteria

1. WHILE Verification_Report ยังมีรายการใดในตารางสรุปที่มีสถานะ ไม่ผ่าน, รอผล หรือยังไม่ตรวจ, THE Migration_Plan SHALL ระบุสถานะว่าถูกบล็อกไว้ในส่วนต้นของเอกสารและไม่เริ่มขั้นตอนย้ายระบบ
2. WHEN ทุกรายการในตารางสรุปของ Verification_Report มีสถานะ ผ่าน, THE Migration_Plan SHALL บันทึกการอ้างอิงถึง Verification_Report ที่ผ่าน โดยระบุชื่อไฟล์และวันที่ของรายงานนั้นเป็นเงื่อนไขเปิดเกต ทั้งนี้ หากการบันทึกการอ้างอิงล้มเหลว เกตยังถือว่าเปิดได้ตราบที่ Verification_Report มีสถานะผ่านครบ
3. THE Migration_Plan SHALL ระบุเงื่อนไข Verification_Gate อย่างชัดเจนไว้ในส่วนต้นของเอกสาร โดยนิยามว่า "ผ่านครบ" หมายถึงไม่มีรายการใดในตารางสรุปที่มีสถานะ ไม่ผ่าน รอผล หรือยังไม่ตรวจ
4. IF ไม่มี Verification_Report หรือไม่สามารถเข้าถึงได้, THEN THE Migration_Plan SHALL ถือว่าเกตยังไม่เปิดและระบุสถานะถูกบล็อก

### Requirement 9: จัดทำแผนย้ายขึ้น AWS เป็นเอกสาร Markdown โดยอ้างอิงเอกสารเดิม

**User Story:** As a Plan_Author, I want เขียนแผนย้ายขึ้น AWS ที่ครบถ้วนแต่ไม่ทำซ้ำเอกสารเดิม, so that แผนสอดคล้องกับแนวทางที่มีอยู่และดูแลรักษาง่าย

#### Acceptance Criteria

1. THE Migration_Plan SHALL เป็นไฟล์ Markdown (`.md`) ที่บรรยายแนวทางและแผนการเท่านั้น โดยไม่รวมการแก้ไขซอร์สโค้ดจริง (ไม่มี code diff/patch) และไม่รวมคำสั่งจัดสรรโครงสร้างพื้นฐานจริง (ไม่มีการ provision/deploy ทรัพยากร AWS)
2. THE Migration_Plan SHALL อ้างอิง Reference_Docs (Discussions/20, 24, 25, 26, 27 และ `app/infra/aws/env.cloud.example`) ด้วยลิงก์หรือชื่อไฟล์สำหรับรายละเอียดที่มีอยู่แล้ว แทนการทำซ้ำเนื้อหา
3. THE Migration_Plan SHALL ระบุการจับคู่บริการจากสแตกปัจจุบันไปยังบริการ AWS อย่างน้อยครอบคลุม MinIO ไป S3, Postgres+pgvector ไป RDS หรือ Aurora PostgreSQL, Redis ไป ElastiCache, backend ไป ECS Fargate ที่ใช้ IAM task role และ Local_LLM ไป Amazon Bedrock
4. THE Migration_Plan SHALL ระบุการเปลี่ยนค่าตัวแปรสภาพแวดล้อมสำหรับโหมดคลาวด์ อย่างน้อยครอบคลุม `DEPLOYMENT_MODE=cloud`, `LLM_PROVIDER=bedrock`, `EMBEDDING_PROVIDER=bedrock` และระบุอย่างชัดเจนว่าในโหมด production ห้ามตั้ง `EMBEDDING_PROVIDER=local` และต้องปล่อย `AWS_ACCESS_KEY_ID` กับ `AWS_SECRET_ACCESS_KEY` ให้ว่างเพื่อใช้ IAM task role ของ ECS
5. THE Migration_Plan SHALL ระบุค่าเริ่มต้นของ Bedrock ที่ใช้อ้างอิง ได้แก่ region `ap-southeast-1`, โมเดลแชท `anthropic.claude-3-5-sonnet-20241022-v2:0` (`BEDROCK_MODEL_ID`) และ embeddings `amazon.titan-embed-text-v2:0` (`BEDROCK_EMBEDDING_MODEL_ID`)

### Requirement 10: ระบุขั้นตอนตัดระบบ แผนย้อนกลับ และความเสี่ยงในแผน

**User Story:** As a Plan_Author, I want ให้แผนครอบคลุมการตัดระบบ การย้อนกลับ และความเสี่ยง, so that การย้ายระบบในอนาคตทำได้อย่างควบคุมได้

#### Acceptance Criteria

1. THE Migration_Plan SHALL ระบุลำดับขั้นตอนการตัดระบบเข้า AWS (cutover) เป็นรายการที่เรียงลำดับด้วยเลขลำดับต่อเนื่อง โดยแต่ละขั้นตอนต้องระบุอย่างน้อย: การกระทำที่ต้องทำ ผู้รับผิดชอบ เงื่อนไขก่อนเริ่ม (precondition) และเกณฑ์การตรวจสอบว่าสำเร็จ (verification)
2. THE Migration_Plan SHALL ระบุแผนย้อนกลับ (rollback) ที่ประกอบด้วยเงื่อนไขที่ใช้ตัดสินใจย้อนกลับ (rollback trigger) สถานะเป้าหมายที่ระบบต้องกลับไปหลังย้อนกลับ และลำดับขั้นตอนการย้อนกลับที่เรียงลำดับด้วยเลขลำดับเริ่มจาก 1 และใช้ลำดับแยกจากขั้นตอน cutover
3. IF การตัดระบบ (cutover) ไม่ผ่านเกณฑ์การตรวจสอบตามที่ระบุในขั้นตอน cutover, THEN THE Migration_Plan SHALL ระบุให้ดำเนินการตามแผนย้อนกลับ (rollback) เพื่อคืนระบบสู่สถานะเป้าหมายที่กำหนดไว้
4. THE Migration_Plan SHALL ระบุความเสี่ยงที่ทราบอย่างน้อย 2 รายการ โดยแต่ละรายการต้องระบุ: คำอธิบายความเสี่ยง ผลกระทบ และแนวทางบรรเทาพร้อมผู้รับผิดชอบ และต้องครอบคลุมอย่างน้อยประเด็นการ seed embeddings ใหม่เมื่อเปลี่ยนไปใช้ Bedrock Titan (เนื่องจากมิติเวกเตอร์ของ Titan ต่างจาก EmbeddingGemma ที่มี 768 มิติ) และประเด็นคิวร่างที่ต้องจำกัด backend service ให้ desiredCount เท่ากับ 1 จนกว่าจะย้ายสถานะ job ออกนอกโปรเซส
5. THE Migration_Plan SHALL ระบุแนวทางรองรับการย้าย Neo4j GraphRAG ไปยัง Neptune โดยอ้างอิงแนวทางที่ระบุไว้ใน Reference_Docs 25 และ 27 อย่างเจาะจง

### Requirement 11: ย้ายสถานะงานร่างออกจากหน่วยความจำเพื่อรองรับหลายอินสแตนซ์

**User Story:** As a maintainer, I want ย้ายสถานะงานร่างไปเก็บนอกโปรเซส, so that ระบบร่างรองรับการสเกลแนวนอนและไม่สูญงานเมื่อรีสตาร์ต

#### Acceptance Criteria

1. WHEN งานร่างถูกสร้างผ่าน draft-chat/start, THE system SHALL บันทึกสถานะงานลงใน Draft_Job_Store (Redis) เป็นระเบียนที่ระบุด้วย project_id โดยมีฟิลด์ status (หนึ่งในค่า queued/running/done/failed), drafted_count (จำนวนเต็ม 0 ถึง total), total (จำนวนหัวข้อทั้งหมด) และ updated_at (เวลาที่ปรับปรุงล่าสุด) และ SHALL ตั้งอายุหมดสภาพ (TTL) ของระเบียน 600 วินาที
2. WHEN สถานะงานร่างเปลี่ยน (queued→running, running→done, running→failed หรือเมื่อ drafted_count เพิ่มขึ้น), THE system SHALL ปรับปรุงระเบียนใน Draft_Job_Store พร้อมค่า updated_at ปัจจุบัน ภายใน 5 วินาทีหลังการเปลี่ยนแปลง
3. WHEN ผู้ใช้เรียก draft-chat/status จากอินสแตนซ์ใด ๆ (รวมถึงอินสแตนซ์อื่นที่ไม่ได้เริ่มงาน), THE system SHALL คืนสถานะงานร่าง (status, drafted_count, total) ที่อ่านจาก Draft_Job_Store โดยตรงกับค่าที่บันทึกไว้ล่าสุด (updated_at ล่าสุด)
4. IF backend รีสตาร์ตหรือหยุดทำงานระหว่างงานร่างมีสถานะ running และระเบียนไม่ถูกปรับปรุง (updated_at ไม่เปลี่ยน) นานเกิน 600 วินาที, THEN THE system SHALL รายงานสถานะงานนั้นเป็น failed แทนการคงค่า running ค้างไว้หรือหายไปเงียบ ๆ และ SHALL คงค่า drafted_count เดิมของงานที่ทำสำเร็จไปแล้วไว้
5. IF Draft_Job_Store (Redis) ไม่พร้อมใช้งานหรืออ่าน/เขียนล้มเหลว, THEN THE system SHALL ถอยกลับไปทำงานแบบอินสแตนซ์เดียวโดยติดตามสถานะงานในหน่วยความจำของโปรเซสเดิม และ SHALL ดำเนินการร่างต่อได้โดยไม่ทำให้การร่างล้มเหลวทั้งหมด (degrade gracefully)
6. THE system SHALL รักษาความเข้ากันได้กับสัญญา SSE เดิม (progress, section_done, subsection_done, all_done) โดย payload และลำดับเหตุการณ์ที่ frontend รับ ต้องไม่เปลี่ยนจากพฤติกรรมเดิม

### Requirement 12: บังคับการตรวจครบถ้วนฝั่งเซิร์ฟเวอร์ก่อนส่งตรวจ

**User Story:** As a reviewer, I want ให้เซิร์ฟเวอร์ตรวจความครบก่อนรับ submit, so that ไม่มีโครงการที่ยังร่างไม่ครบเข้าสู่การตรวจ

#### Acceptance Criteria

1. WHEN officer เรียก endpoint submit โครงการ (POST /projects/{id}/submit), THE system SHALL ตรวจฝั่งเซิร์ฟเวอร์ว่าครบทั้ง 13 หมวด (s1-s13) ก่อนเปลี่ยนสถานะเป็น in_review โดยถือว่าแต่ละหมวด "ครบ" เมื่อมีเนื้อหาหลัก (content) หรือ (เฉพาะ s4) มีหัวข้อย่อยที่กรอกแล้วอย่างน้อยหนึ่งหัวข้อในช่วง s4.1-s4.14 ตามกฎ isSectionFilled
2. WHEN โครงการครบทั้ง 13 หมวดและมีสถานะเป็น draft หรือ rejected, THE system SHALL เปลี่ยนสถานะเป็น in_review และตอบกลับผลสำเร็จตามรูปแบบ response เดิม
3. IF โครงการยังร่างไม่ครบ 13 หมวด, THEN THE system SHALL ปฏิเสธ submit ด้วย error ฝั่งเซิร์ฟเวอร์ (HTTP 4xx) ที่มีข้อความระบุรายการหมวดที่ยังขาด (section_key และ sub_key ที่เกี่ยวข้อง) และคงสถานะโครงการเดิมไว้ไม่เปลี่ยนแปลง
4. IF โครงการมีสถานะอื่นที่ไม่ใช่ draft หรือ rejected, THEN THE system SHALL ปฏิเสธ submit ด้วย error ฝั่งเซิร์ฟเวอร์ (HTTP 4xx) และคงสถานะโครงการเดิมไว้ไม่เปลี่ยนแปลง
5. WHEN server-side validation ปฏิเสธ submit, THE system SHALL ไม่เปลี่ยนสถานะโครงการและไม่บันทึกเหตุการณ์ submit โดยการตรวจความครบถ้วนต้องบังคับใช้ที่ endpoint ฝั่งเซิร์ฟเวอร์เสมอไม่ว่าฝั่ง UI จะส่งค่ามาอย่างไร

### Requirement 13: ความเสถียรของงานร่าง/ตรวจขนาดใหญ่และงานที่ใช้เวลานาน

**User Story:** As an officer, I want ให้การร่างเอกสารขนาดใหญ่ทำงานจนจบอย่างเสถียร, so that งานร่างยาวไม่ค้างหรือหลุดกลางคัน

#### Acceptance Criteria

1. WHILE งานร่าง 13 หมวดกำลังทำงาน (ใช้เวลาได้ถึง 60 นาที), THE system SHALL ทำงานร่างต่อเนื่องเป็น background task จนครบทั้ง 13 หมวด แม้การเชื่อมต่อ SSE ของ client จะหลุด โดยบันทึกสถานะความคืบหน้าราย section ลงที่จัดเก็บถาวรทุกครั้งที่หมวดหนึ่งเสร็จ
2. WHEN client เชื่อมต่อ SSE ใหม่ระหว่างงานร่างยังทำงาน, THE system SHALL ส่งสถานะความคืบหน้าล่าสุดที่บันทึกไว้ (จำนวนหมวดที่เสร็จและหมวดที่กำลังทำงาน) กลับให้ client ภายใน 4 วินาที เพื่อให้ติดตามต่อได้โดยไม่เริ่มงานใหม่
3. IF การเรียกโมเดลของหมวดใดล้มเหลวหรือใช้เวลาเกิน 1800 วินาทีต่อหมวด, THEN THE system SHALL บันทึกสถานะความล้มเหลวระดับหมวดนั้นเป็น failed พร้อมข้อบ่งชี้สาเหตุ และดำเนินการหมวดถัดไปต่อทันทีโดยไม่ทำให้ทั้งงานหยุดค้าง
4. IF มีการเรียกเริ่มงานร่างสำหรับ project_id เดียวกันขณะที่งานร่างเดิมยังทำงานอยู่ (ยังไม่ถึงสถานะ done หรือ failed), THEN THE system SHALL ไม่สร้างงานร่างใหม่ แต่คืน reference ของงานที่กำลังทำงานอยู่เดิม (idempotent start)
5. THE Combined_Report SHALL บันทึกหลักฐานการทดสอบโหลดของการร่างและการตรวจที่ครอบคลุมอย่างน้อย: review pack ขนาดสูงสุด 200,000 อักขระ, paste ขนาดสูงสุด 500,000 อักขระ, และงานร่างที่ทำงานพร้อมกันอย่างน้อย 3 งานต่างโครงการ พร้อมผลลัพธ์ที่สังเกตได้ (สถานะสำเร็จ/ล้มเหลว และเวลาที่ใช้ต่องาน)

### Requirement 14: รวมรายงานตรวจสอบและแผนย้ายระบบเป็นเอกสารเดียว

**User Story:** As a stakeholder, I want เอกสารฉบับเดียวที่รวมผลตรวจสอบและแผนย้ายระบบ, so that ติดตามภาพรวมได้ในที่เดียว

#### Acceptance Criteria

1. THE Combined_Report SHALL เป็นไฟล์ Markdown ฉบับเดียว (เสนอ `Discussions/28-VERIFICATION-AND-MIGRATION.md`) ที่มีครบทั้งสี่ส่วนเรียงตามลำดับ: (A) ส่วนผลการตรวจสอบบน Local LLM, (B) ส่วนคั่น Verification_Gate, (C) ส่วนแผนย้ายขึ้น AWS, และ (D) ส่วนสรุปงานความเสถียร/สเกล
2. THE Combined_Report SHALL วางส่วนคั่น Verification_Gate (B) ไว้หลังส่วนตรวจสอบ (A) และก่อนส่วนแผนย้ายระบบ (C) เสมอ
3. THE Combined_Report SHALL มีส่วนสรุปงานแก้โค้ดเพื่อความเสถียร/สเกล (D) ที่อ้างอิงผลการทดสอบที่เกี่ยวข้องกับ Req 11, 12 และ 13 โดยผูกกับผลการตรวจสอบในส่วน (A)
4. WHERE เดิมกำหนดให้แยกเป็นสองไฟล์ (Verification_Report และ Migration_Plan), THE Combined_Report SHALL แทนที่โครงสองไฟล์นั้นด้วยไฟล์เดียวที่มีสองส่วนหลัก (ส่วนตรวจสอบและส่วนแผนย้ายระบบ)
5. IF ส่วนใดในสี่ส่วน (A/B/C/D) ยังไม่มีเนื้อหา, THEN THE Combined_Report SHALL แสดงหัวข้อของส่วนนั้นพร้อมสถานะ "ยังไม่จัดทำ" แทนการละเว้นหัวข้อทั้งหมด
