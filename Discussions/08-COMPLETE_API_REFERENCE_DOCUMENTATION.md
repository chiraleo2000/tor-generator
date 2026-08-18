# 08 — COMPLETE API REFERENCE DOCUMENTATION
### ระบบ TOR Generator (ร่าง TOR + ตรวจสอบ TOR) — REST API สำหรับ Production

> **เอกสารนี้เป็นสัญญา API จากยุค PoC (Rule-based ไม่มี LLM)**  
> แอปที่รันอยู่ตอนนี้มี LLM + RAG แล้ว: FastAPI ที่ `http://localhost:4000/api/v1` ดูเส้นทางปัจจุบันใน `16-BACKEND_ARCHITECTURE.md` และตารางท้ายไฟล์นี้ (หมวด 10)

เอกสารด้านล่างกำหนดสัญญา (contract) ของ REST API ที่แปลงมาจากตรรกะ Rule-based ที่พิสูจน์แล้วใน PoC (`06-UXUI-Mockup.html`) เพื่อให้อ่านประวัติการออกแบบได้ — **อย่าใช้ข้อความ “ไม่มี LLM” เป็นข้อเท็จจริงของระบบ Docker ปัจจุบัน**

---

## สารบัญ

1. [ภาพรวมและ Conventions](#1-ภาพรวมและ-conventions)
2. [Authentication API](#2-authentication-api)
3. [Projects API](#3-projects-api)
4. [Draft TOR — Sections & Extraction API](#4-draft-tor--sections--extraction-api)
5. [Knowledge Base API](#5-knowledge-base-api)
6. [Review TOR — Rule Engine API](#6-review-tor--rule-engine-api)
7. [Export API](#7-export-api)
8. [Error Codes Reference](#8-error-codes-reference)
9. [Rate Limiting & Versioning](#9-rate-limiting--versioning)
10. [เส้นทางที่เพิ่มในแอปที่รันอยู่](#10-เส้นทางที่เพิ่มในแอปที่รันอยู่)

---

## 1. ภาพรวมและ Conventions

| หัวข้อ | รายละเอียด |
|---|---|
| Base URL | `https://api.tor-generator.go.th/api/v1` |
| Protocol | HTTPS only |
| Auth | `Authorization: Bearer <JWT>` (ยกเว้น `/auth/register`, `/auth/login`) |
| Content-Type | `application/json` (ยกเว้น endpoint ที่รับไฟล์ → `multipart/form-data`) |
| Date Format | ISO 8601 (`2026-08-13T10:00:00Z`) |
| Character Encoding | UTF-8 (รองรับภาษาไทยเต็มรูปแบบ) |

### Response Envelope มาตรฐาน

```json
{
  "ok": true,
  "data": { },
  "meta": { "requestId": "req_8f3a2b", "timestamp": "2026-08-13T10:00:00Z" }
}
```

### Error Envelope มาตรฐาน

```json
{
  "ok": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "อีเมลนี้ถูกใช้สมัครแล้ว",
    "field": "email"
  },
  "meta": { "requestId": "req_8f3a2b", "timestamp": "2026-08-13T10:00:00Z" }
}
```

---

## 2. Authentication API

อ้างอิงจาก `AuthService_register` / `AuthService_login` ใน PoC — ใน Production จะเสริม bcrypt password hashing และ JWT session ตามที่ระบุในเอกสาร 07 (Sequence Diagram: Login/Register)

### 2.1 POST /auth/register

สมัครสมาชิกใหม่ — เทียบเท่า `AuthService_register(name, org, email, password)`

**Request Body**
```json
{
  "name": "ผู้ใช้ทดสอบ",
  "organization": "กรมสรรพากร",
  "email": "user@rd.go.th",
  "password": "securepass123",
  "passwordConfirm": "securepass123"
}
```

**Validation Rules (Rule-based — เหมือน PoC ทุกจุด)**
- `email` ต้องตรง regex `^[^\s@]+@[^\s@]+\.[^\s@]+$`
- `password` ยาวอย่างน้อย 6 ตัวอักษร
- `password === passwordConfirm`
- `email` ต้องไม่ซ้ำกับผู้ใช้ที่มีอยู่แล้ว

**Response 201**
```json
{
  "ok": true,
  "data": {
    "userId": "usr_7a1c9e",
    "email": "user@rd.go.th",
    "message": "สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ"
  }
}
```

**Response 409 (อีเมลซ้ำ)**
```json
{ "ok": false, "error": { "code": "EMAIL_TAKEN", "message": "อีเมลนี้ถูกใช้สมัครแล้ว", "field": "email" } }
```

---

### 2.2 POST /auth/login

เข้าสู่ระบบ — เทียบเท่า `AuthService_login(email, password)`

**Request Body**
```json
{ "email": "demo@example.com", "password": "demo123" }
```

**Response 200**
```json
{
  "ok": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "expiresIn": 86400,
    "user": { "id": "usr_demo01", "name": "ผู้ใช้ทดสอบ", "organization": "กรมตัวอย่าง", "email": "demo@example.com" }
  }
}
```

**Response 401**
```json
{ "ok": false, "error": { "code": "INVALID_CREDENTIALS", "message": "อีเมลหรือรหัสผ่านไม่ถูกต้อง" } }
```

---

### 2.3 POST /auth/logout
`Authorization: Bearer <token>` → invalidate session (Redis). **Response 200** `{"ok":true,"data":{}}`

### 2.4 GET /auth/me
คืนข้อมูลผู้ใช้ปัจจุบัน (เทียบเท่า `currentUser` ใน PoC)

**Response 200**
```json
{ "ok": true, "data": { "id": "usr_demo01", "name": "ผู้ใช้ทดสอบ", "organization": "กรมตัวอย่าง", "email": "demo@example.com" } }
```

---

## 3. Projects API

อ้างอิงจาก `ProjectService_create` / `ProjectService_get` และ `projects[]` array ใน PoC

### 3.1 GET /projects

รายการโครงการทั้งหมดของผู้ใช้ (เทียบเท่า `renderDashboard()`)

**Query params:** `status` (draft|progress|done, optional), `page`, `pageSize`

**Response 200**
```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "id": "p1",
        "name": "จ้างบำรุงรักษาระบบ National e-Payment ปีงบประมาณ 2570",
        "ministry": "กรมสรรพากร",
        "budget": 93004500,
        "status": "draft",
        "currentPhase": 2,
        "progressPct": null,
        "updatedAt": "2026-01-15T00:00:00Z"
      },
      {
        "id": "p2",
        "name": "จ้างบำรุงรักษาระบบและข้อมูลด้านการป้องกันและบรรเทาสาธารณภัย",
        "ministry": "กรมป้องกันและบรรเทาสาธารณภัย (ปภ.)",
        "budget": 5000000,
        "status": "progress",
        "currentPhase": 2,
        "progressPct": 62,
        "updatedAt": "2026-01-14T00:00:00Z"
      }
    ],
    "total": 3
  }
}
```

### 3.2 POST /projects

สร้างโครงการใหม่ — เทียบเท่า `createNewProject()` → `ProjectService_create()`

**Request Body**
```json
{ "name": "โครงการใหม่", "ministry": "", "budget": null }
```

**Response 201**
```json
{ "ok": true, "data": { "id": "p4", "status": "draft", "currentPhase": 0 } }
```

### 3.3 GET /projects/{id}

รายละเอียดโครงการ — เทียบเท่า `ProjectService_get(id)` รวม `extracted` fields ที่ได้จาก NLP

**Response 200**
```json
{
  "ok": true,
  "data": {
    "id": "p1",
    "name": "จ้างบำรุงรักษาระบบ National e-Payment ปีงบประมาณ 2570",
    "ministry": "กรมสรรพากร",
    "budget": 93004500,
    "status": "draft",
    "currentPhase": 2,
    "extracted": {
      "projectName": "จ้างบำรุงรักษาระบบ National e-Payment",
      "ministry": "กรมสรรพากร",
      "budget": 93004500,
      "timeline": "ระยะเวลาดำเนินการ 365 วัน",
      "paidupSuggest": "ไม่น้อยกว่า 23,251,125 บาท (25% ของงบประมาณที่สกัดได้)"
    },
    "sectionProgress": { "s1": true, "s2": true, "s3": false, "s4": false }
  }
}
```

### 3.4 PATCH /projects/{id}
อัปเดตข้อมูลโครงการ (ชื่อ/หน่วยงาน/งบประมาณ/สถานะ) — body เป็น partial object ของ field ที่จะแก้

### 3.5 DELETE /projects/{id}
ลบโครงการ (soft-delete แนะนำสำหรับ audit trail ภาครัฐ)

### 3.6 POST /projects/{id}/submit

ส่งเข้าสู่กระบวนการสร้าง (draft → progress) — เทียบเท่า `submitForApproval()` ที่ trigger การจำลอง progress bar ใน PoC; ใน Production จะ enqueue งานจริงไปยัง OCR/NLP Worker

**Response 202**
```json
{ "ok": true, "data": { "id": "p1", "status": "progress", "jobId": "job_44f1" } }
```

---

## 4. Draft TOR — Sections & Extraction API

อ้างอิงจาก `renderPhase0` ถึง `renderPhase4`, `p0Files()`, `renderSectionFlow()`, `NLPEngine_extractFields`

### 4.1 POST /projects/{id}/extraction

อัปโหลดเอกสารอ้างอิงของโครงการ (Phase 0) — เทียบเท่า `p0Files(event)` → `ExtractionService_extract` → `NLPEngine_extractFields`

**Request:** `multipart/form-data`, field `file` (PDF/DOCX/รูปภาพ, ≤ 20MB)

**ตรรกะ Rule-based ที่ทำงานฝั่ง Backend (เหมือน PoC เป๊ะ):**
1. `detectType(file)` — ตรวจ MIME/extension → `pdf` / `docx` / `image`
2. เรียก extractor ตามประเภท: `pdf.js` (server-side ผ่าน `pdfjs-dist` หรือ `pdf-parse`), `mammoth` (npm package เดียวกับ mammoth.js), OCR ภาพผ่าน `tesseract.js`/Tesseract binary
3. ส่งข้อความที่สกัดได้เข้า `NLPEngine_extractFields(text)` — regex + keyword dictionary ล้วนๆ ไม่มี ML

**Response 200**
```json
{
  "ok": true,
  "data": {
    "fileName": "sample_tor_document.pdf",
    "extractionStatus": "success",
    "extracted": {
      "projectName": "จัดซื้อจัดจ้างระบบ e-Payment กรมสรรพากร",
      "ministry": "กรมสรรพากร",
      "budget": 5000000,
      "timeline": "ระยะเวลาดำเนินการ 180 วัน",
      "problem": "ปัญหาที่พบคือระบบเดิมล้าสมัยและไม่รองรับการทำธุรกรรมออนไลน์",
      "paymentPercents": [30, 40, 30],
      "paymentPercentsText": "พบสัดส่วนงวดจ่ายเงินในเอกสาร: 30%, 40%, 30%",
      "evaluationMethod": "เกณฑ์ราคา (Price)",
      "paidupSuggest": "ไม่น้อยกว่า 1,250,000 บาท (25% ของงบประมาณที่สกัดได้)"
    }
  }
}
```

**Response 200 (สกัดล้มเหลวบางส่วน — Graceful Degradation เหมือน PoC)**
```json
{
  "ok": true,
  "data": {
    "fileName": "scan_broken.png",
    "extractionStatus": "partial_failure",
    "extractionError": "สกัดข้อความล้มเหลว: OCR timeout",
    "extracted": {}
  }
}
```

### 4.2 GET /projects/{id}/sections

รายการ 10 หมวดหลัก + สถานะกรอกข้อมูล + tag การจับคู่กับ `extracted` — เทียบเท่า `renderSectionFlow()`

**Response 200**
```json
{
  "ok": true,
  "data": {
    "sections": [
      { "key": "s1", "title": "ความเป็นมา (Background)", "filled": true, "matchStatus": "matched", "mappedField": "problem" },
      { "key": "s4", "title": "ขอบเขตของงาน (Scope of Work)", "filled": false, "big": true,
        "subs": [
          { "key": "4.1", "title": "สรุปภาพรวมของเดิม" },
          { "key": "4.2", "title": "ลักษณะระบบเดิม (As-Is)" }
        ]
      }
    ]
  }
}
```

### 4.3 PUT /projects/{id}/sections/{sectionKey}

บันทึกเนื้อหาของหมวด (ผู้ใช้แก้ไข/ยืนยันเนื้อหาที่ระบบเติมให้อัตโนมัติ) — เทียบเท่า `saveDraft()`

**Request Body**
```json
{ "content": "ระบบเดิมล้าสมัยและไม่รองรับการทำธุรกรรมออนไลน์ได้อย่างมีประสิทธิภาพ...", "filled": true }
```

**Response 200** `{ "ok": true, "data": { "sectionKey": "s1", "filled": true } }`

### 4.4 GET /projects/{id}/export

ดูรายละเอียดใน [หัวข้อ 7. Export API](#7-export-api)

---

## 5. Knowledge Base API

อ้างอิงจาก `KB_RAW[]`, `KB_CHUNKED[]`, `kbUpload()`, `handleKbFiles()`, `deleteUserFile()`

### 5.1 GET /kb/raw

เอกสารดิบตามหมวด (บังคับตามกฎหมาย + ระบบกลาง) — เทียบเท่า `renderKbRaw()`

**Response 200**
```json
{
  "ok": true,
  "data": {
    "categories": [
      { "category": "กฎหมายจัดซื้อจัดจ้าง", "files": [
        { "name": "พรบ.จัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ_2560.pdf", "sizeKb": 842, "isMandatory": true }
      ]}
    ]
  }
}
```

### 5.2 GET /kb/chunked

เอกสารที่ Chunk แล้วเก็บใน Vector Store — เทียบเท่า `renderKbChunked()`; ใน Production คือผลลัพธ์จริงจากการ query Qdrant/pgvector

**Response 200**
```json
{
  "ok": true,
  "data": {
    "totalChunks": 586,
    "categories": [
      { "category": "definitions", "fileCount": 20, "chunkCount": 166 },
      { "category": "procurement_methods", "fileCount": 10, "chunkCount": 99 },
      { "category": "guarantee", "fileCount": 5, "chunkCount": 23 }
    ]
  }
}
```

### 5.3 POST /kb/user-files

อัปโหลดไฟล์เข้าคลังความรู้ส่วนบุคคล/โครงการ (เงื่อนไขเฉพาะ ร่างเอกสารประกวดราคา ฯลฯ) — เทียบเท่า `handleKbFiles(files)`

**Request:** `multipart/form-data`, field `files[]`, field `fileType` (เช่น `เงื่อนไขเฉพาะ`, `ประกาศราคากลาง`, `requirement ลูกค้า`)

**Response 201**
```json
{ "ok": true, "data": { "id": "kbf_991", "name": "เงื่อนไขพิเศษ_โครงการABC.docx", "chunkCount": 12, "fileType": "เงื่อนไขเฉพาะ" } }
```

### 5.4 DELETE /kb/user-files/{id}
ลบไฟล์ผู้ใช้ออกจากคลังความรู้ — เทียบเท่า `deleteUserFile(i)` (พร้อม modal ยืนยันฝั่ง UI)

---

## 6. Review TOR — Rule Engine API

อ้างอิงจาก `reviewFileSelected()`, `addCompareProject()`, `runReviewCheck()`, `ReviewEngine_run()`

### 6.1 POST /review/extract

อัปโหลดไฟล์ TOR ที่ต้องการตรวจสอบ — เทียบเท่า `showReviewFile()`

**Request:** `multipart/form-data`, field `file`

**Response 200**
```json
{ "ok": true, "data": { "reviewFileId": "rvf_331", "extractionStatus": "success", "textLength": 8420 } }
```

### 6.2 POST /review/compare-projects

เพิ่มโครงการเปรียบเทียบ (Optional) — เทียบเท่า `addCompareProject()` + `handleCompareFile()`

**Request Body**
```json
{ "reviewFileId": "rvf_331", "compares": [ { "name": "โครงการ ปภ. 2569", "fileRef": "cmpfile_88" } ] }
```

### 6.3 POST /review/run

รันการตรวจสอบแบบ Rule-based ทั้งหมด — เทียบเท่า `runReviewCheck()` → `ReviewEngine_run(text, compares)`

**Request Body**
```json
{ "reviewFileId": "rvf_331" }
```

**Response 200 — โครงสร้าง JSON ที่แทน HTML string ของ PoC (แปลงเป็น structured data สำหรับ frontend render เอง)**
```json
{
  "ok": true,
  "data": {
    "checks": [
      { "id": "sectionCoverage", "status": "fail", "found": 0, "total": 10, "pct": 0,
        "message": "โครงสร้าง TOR — พบ 0/10 หมวดที่บังคับ (0%)" },
      { "id": "paidupCapital", "status": "fail", "paidup": 1000000, "budget": 5000000, "ratio": 0.20,
        "message": "Paid-up Capital: 1,000,000 บาท (20.0% ของงบ) — ต่ำกว่าเกณฑ์ขั้นต่ำ 25%" },
      { "id": "paymentSchedule", "status": "pass", "percents": [30, 40, 30], "sum": 100,
        "message": "งวดการจ่ายเงินที่พบ: 30%, 40%, 30% (รวม 100%)" },
      { "id": "brandFairness", "status": "pass",
        "message": "ระบุยี่ห้อ/รุ่นพร้อมเงื่อนไข \"หรือเทียบเท่า\"" },
      { "id": "legalReference", "status": "pass",
        "message": "พบการอ้างอิง พ.ร.บ./ระเบียบกระทรวงการคลังในเอกสาร" },
      { "id": "comparisonSimilarity", "status": "info", "comparisons": [
        { "name": "โครงการ ปภ. 2569", "similarityPct": 47 }
      ]}
    ],
    "overallScore": 40,
    "scoreFormula": "coverage*0.5 + legalRef(15) + budgetClarity(15) + payment(20)"
  }
}
```

### 6.4 GET /review/{reviewFileId}/results
ดึงผลตรวจสอบที่รันไปแล้ว (สำหรับดูย้อนหลัง/แนบกับโครงการ)

---

## 7. Export API

อ้างอิงจาก `exportTor()`

### 7.1 GET /projects/{id}/export

ส่งออกเอกสาร TOR ฉบับสมบูรณ์

**Query params:** `format` = `html` (default, เหมือน PoC) | `docx` | `pdf` (Production เพิ่มเติม)

**Response 200** — `Content-Type: text/html` หรือ `application/pdf`/`application/vnd.openxmlformats-officedocument.wordprocessingml.document` พร้อม header `Content-Disposition: attachment; filename="TOR_p1_2026-08-13.html"`

---

## 8. Error Codes Reference

| Code | HTTP Status | ความหมาย |
|---|---|---|
| `VALIDATION_ERROR` | 400 | ข้อมูลที่ส่งมาไม่ผ่านการตรวจสอบ (เช่น email format, password length) |
| `UNAUTHORIZED` | 401 | ไม่มี token หรือ token ไม่ถูกต้อง/หมดอายุ |
| `INVALID_CREDENTIALS` | 401 | อีเมล/รหัสผ่านไม่ถูกต้อง |
| `FORBIDDEN` | 403 | ไม่มีสิทธิ์เข้าถึงโครงการนี้ |
| `EMAIL_TAKEN` | 409 | อีเมลถูกใช้สมัครแล้ว |
| `NOT_FOUND` | 404 | ไม่พบโครงการ/ไฟล์/ผลตรวจสอบที่ระบุ |
| `UNSUPPORTED_FILE_TYPE` | 415 | ไม่รองรับประเภทไฟล์ (รองรับ PDF/DOCX/รูปภาพเท่านั้น) |
| `EXTRACTION_FAILED` | 200 (ok:true, partial) | สกัดข้อความล้มเหลว — Graceful Degradation ไม่ throw 500 |
| `FILE_TOO_LARGE` | 413 | ไฟล์เกินขนาดที่กำหนด (20MB) |
| `RATE_LIMITED` | 429 | เรียก API เกินอัตราที่กำหนด |
| `INTERNAL_ERROR` | 500 | ข้อผิดพลาดที่ไม่คาดคิดฝั่งเซิร์ฟเวอร์ |

---

## 9. Rate Limiting & Versioning

- **Rate Limit:** 100 requests/นาที ต่อ user token (endpoint อัปโหลดไฟล์: 10 requests/นาที เนื่องจากใช้ CPU สูงสำหรับ OCR)
- **Versioning:** ใช้ path-based versioning (`/api/v1/...`) — เมื่อมีการเปลี่ยนแปลงที่ breaking change จะออก `/api/v2/` โดยคง `/api/v1/` ไว้อย่างน้อย 6 เดือน
- **Idempotency:** endpoint ที่สร้างข้อมูล (POST) รองรับ header `Idempotency-Key` เพื่อป้องกันการสร้างซ้ำจาก retry

---

## 10. เส้นทางที่เพิ่มในแอปที่รันอยู่

Base URL จริง: `http://localhost:4000/api/v1` (เบราว์เซอร์เรียกผ่าน `/api/v1` ที่พอร์ต 3000)  
Auth: cookie `tor_access_token` หรือ `Authorization: Bearer`

| กลุ่ม | เส้นทาง | ใช้ทำอะไร |
|--------|---------|-----------|
| สุขภาพ | `GET /health` | `postgres` `redis` `minio` `mongo` `neo4j` |
| แชทคลังความรู้ | `GET/POST /chat/rooms` | ห้อง `kind=kb` หรือ `draft_intake` |
| | `GET/PATCH/DELETE /chat/rooms/{id}` | รายการ เปลี่ยนชื่อ ลบ |
| | `GET /chat/rooms/{id}/messages` | ประวัติห้อง |
| | `POST /chat/rooms/{id}/messages` | SSE ถาม-ตอบ + citations |
| | `POST /chat/rooms/{id}/attachments` | แนบไฟล์เข้า Mongo GridFS (`scope: user`) |
| | `GET /chat/prompts` | ชิปพรอมต์ตาม `kind` |
| Intake Phase 0–1 | `POST /projects/{id}/intake/upload` | อัปโหลดชุดใหญ่ ไม่เลือก 9 ประเภท |
| | `POST /projects/{id}/intake/analyze` | จัดเข้า s1–s13 / s4.1–s4.14 |
| | `GET /projects/{id}/intake/coverage` | ตาราง filled / gap / reference_only |
| | `POST /projects/{id}/intake/fill-reference` | ดึงอ้างอิงกฎหมายลงช่องว่าง |
| | `POST /projects/{id}/intake/confirm-ready` | ตั้ง `ready_to_compose` แล้วเข้า Phase 2 |
| | `POST /projects/{id}/intake/chat` | SSE แชทร่างโครงการ |
| ร่าง | `POST /projects/{id}/draft-section` | เอเจนต์หมวด + เขียน `content` และ `ai_draft` |
| ผู้ดูแล AI | `GET/PUT /admin/ai-settings` | Local / Cloud / Hybrid มีผลทันที |
| | `POST /admin/ai-settings/test` | ping LM Studio หรือรายการโมเดลคลาวด์ |

รายละเอียดชั้นภายใน: `16-BACKEND_ARCHITECTURE.md`

---
*เอกสาร 08 — Complete API Reference Documentation | หมวด 1–9 เป็นสัญญา PoC | หมวด 10 คือเส้นทางของแอป Docker ปัจจุบัน*
