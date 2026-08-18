# 09 — BACKEND / FRONTEND DEVELOPMENT STRUCTURE
### ระบบ TOR Generator — โครงสร้างโปรเจกต์สำหรับทีมพัฒนา (Production)

> **โครงสร้างที่รันจริงอยู่ที่ `app/frontend` (Next.js 14) และ `app/backend` (FastAPI)**  
> ดู `16-BACKEND_ARCHITECTURE.md` และ `17-FRONTEND_ARCHITECTURE.md`  
> ต้นไม้นี้เป็นแผนจาก PoC (Vite / Express) ไม่ใช่เลย์เอาต์ Docker ปัจจุบัน และโฟลเดอร์ `frontend/` / `backend/` ที่ราก**ไม่มีในรีโป**

เอกสารนี้กำหนดโครงสร้างโฟลเดอร์/โมดูลสำหรับพัฒนาต่อจาก PoC (`06-UXUI-Mockup.html`) ไปสู่ระบบ Production จริง โดย **map ฟังก์ชันทุกตัวใน PoC ไปยังโมดูล Backend/Frontend ที่ควรจะเป็น** เพื่อให้ทีมพัฒนาไม่ต้องออกแบบตรรกะใหม่ทั้งหมด เพียงย้าย logic ที่พิสูจน์แล้วไปวางในโครงสร้างที่ scale ได้

**Tech Stack ที่แนะนำในบันทึกนี้** (แผนเดิม — ของจริงใช้ Next.js + FastAPI):

| Layer | แนะนำ | เหตุผล |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite | Ecosystem ใหญ่, TypeScript ช่วยลดบั๊กจากข้อมูลซับซ้อนของ TOR |
| State Management | Zustand หรือ Redux Toolkit | จำลอง `projects[]`/`currentUser` ของ PoC แบบมี structure |
| Backend | Node.js + Express/Fastify (หรือ Python + FastAPI) | เดิม logic เป็น JS อยู่แล้ว ย้ายมา Node.js ได้เกือบตรงตัว |
| OCR/NLP Worker | Node.js worker process แยก (หรือ Python ถ้าจะขยายเป็น ML ในอนาคต) | แยก CPU-heavy work ออกจาก API หลัก |
| Database | PostgreSQL | รองรับ JSONB สำหรับ `extracted fields` ที่โครงสร้างไม่ตายตัว |
| Vector Store | Qdrant หรือ pgvector extension | ตามที่ระบุใน PoC (Knowledge Base) |
| Queue | BullMQ (Redis-based) | เบาและง่ายสำหรับ workload ขนาดนี้ |

---

## สารบัญ

1. [Frontend Project Structure](#1-frontend-project-structure)
2. [Backend Project Structure](#2-backend-project-structure)
3. [ตาราง Mapping: PoC Function → Production Module](#3-ตาราง-mapping-poc-function--production-module)
4. [Shared Types / Contracts](#4-shared-types--contracts)
5. [Monorepo Layout (แนะนำ)](#5-monorepo-layout-แนะนำ)

---

## 1. Frontend Project Structure

```
frontend/
├── src/
│   ├── pages/                        # เทียบเท่า .page ใน PoC (nav('pageId'))
│   │   ├── AuthPage/
│   │   │   ├── LoginForm.tsx         # ← #loginPanel, handleLogin()
│   │   │   ├── RegisterForm.tsx      # ← #registerPanel, handleRegister()
│   │   │   └── AuthPage.tsx          # ← #authScreen, switchAuth()
│   │   ├── DashboardPage/
│   │   │   ├── ProjectTable.tsx      # ← renderDashboard(), #projectsTableBody
│   │   │   ├── StatCards.tsx         # ← 3 stat cards (ร่าง/กำลังดำเนินการ/เสร็จแล้ว)
│   │   │   └── DashboardPage.tsx
│   │   ├── KnowledgeBasePage/
│   │   │   ├── KbRawSection.tsx      # ← renderKbRaw(), KB_RAW[]
│   │   │   ├── KbChunkedSection.tsx  # ← renderKbChunked(), KB_CHUNKED[]
│   │   │   ├── KbUploadDropzone.tsx  # ← kbUpload(), kbDrop()
│   │   │   └── KnowledgeBasePage.tsx
│   │   ├── DraftTorPage/
│   │   │   ├── PhaseFlowNav.tsx      # ← renderPhaseFlow(), setPhase()
│   │   │   ├── Phase0Upload.tsx      # ← renderPhase0(), p0Files()
│   │   │   ├── Phase1Analysis.tsx    # ← renderPhase1()
│   │   │   ├── Phase2SectionFlow.tsx # ← renderSectionFlow(), toggleSub()
│   │   │   ├── Phase3Approval.tsx    # ← renderPhase3()
│   │   │   ├── Phase4Publish.tsx     # ← renderPhase4(), exportTor()
│   │   │   └── DraftTorPage.tsx      # ← renderDraftPage()
│   │   ├── ReviewTorPage/
│   │   │   ├── ReviewUploadPanel.tsx # ← reviewFileSelected()
│   │   │   ├── CompareProjectsList.tsx # ← addCompareProject()
│   │   │   ├── ReviewResultPanel.tsx # ← runReviewCheck() แสดงผลลัพธ์
│   │   │   └── ReviewTorPage.tsx
│   │   └── GuidePage/
│   │       ├── GuideTabs.tsx         # ← setGuideTab()
│   │       └── GuidePage.tsx         # ← renderGuide()
│   │
│   ├── components/                   # UI ที่ใช้ร่วมกันหลายหน้า
│   │   ├── layout/Sidebar.tsx        # ← .menu-item, highlightMenu()
│   │   ├── layout/TopBar.tsx
│   │   ├── common/Modal.tsx          # ← openModal()/closeModal()
│   │   ├── common/StatusPill.tsx     # ← .status-pill (draft/progress/done)
│   │   └── common/ProgressBar.tsx    # ← .progress-bar
│   │
│   ├── services/                     # API client layer (เรียก Backend REST API)
│   │   ├── authService.ts            # ← เรียก /auth/* (ดูเอกสาร 08)
│   │   ├── projectService.ts         # ← เรียก /projects/*
│   │   ├── extractionService.ts      # ← เรียก /projects/{id}/extraction
│   │   ├── kbService.ts              # ← เรียก /kb/*
│   │   ├── reviewService.ts          # ← เรียก /review/*
│   │   └── apiClient.ts              # axios/fetch wrapper + auth header injection
│   │
│   ├── store/                        # State management (แทน in-memory JS vars ของ PoC)
│   │   ├── authStore.ts              # ← currentUser
│   │   ├── projectStore.ts           # ← projects[], currentProjectId, currentPhase
│   │   └── kbStore.ts                # ← kbUserFiles[]
│   │
│   ├── hooks/
│   │   ├── useFileUpload.ts          # drag&drop handler (จาก kbDrop/reviewDrop)
│   │   └── usePolling.ts             # ← setInterval progress simulation ของ PoC
│   │
│   ├── types/                        # TypeScript interfaces (ดูหัวข้อ 4)
│   ├── utils/
│   │   └── formatters.ts             # toLocaleString, date formatting ฯลฯ
│   ├── App.tsx
│   └── main.tsx
├── public/
├── package.json
└── vite.config.ts
```

---

## 2. Backend Project Structure

```
backend/
├── src/
│   ├── routes/                       # กำหนด REST endpoints (ดูเอกสาร 08 ทุก path)
│   │   ├── auth.routes.ts
│   │   ├── projects.routes.ts
│   │   ├── kb.routes.ts
│   │   ├── review.routes.ts
│   │   └── export.routes.ts
│   │
│   ├── controllers/                  # รับ request → เรียก service → ตอบกลับ
│   │   ├── auth.controller.ts
│   │   ├── projects.controller.ts
│   │   ├── kb.controller.ts
│   │   └── review.controller.ts
│   │
│   ├── services/                     # ★ Business Logic — ย้ายตรงจาก PoC เกือบ 1:1
│   │   ├── auth.service.ts           # ← AuthService_register/login
│   │   ├── project.service.ts        # ← ProjectService_create/get
│   │   ├── extraction/
│   │   │   ├── extraction.service.ts # ← ExtractionService_extract (dispatcher)
│   │   │   ├── pdf.extractor.ts      # ← ExtractionService_fromPDF (pdf-parse/pdfjs-dist)
│   │   │   ├── docx.extractor.ts     # ← ExtractionService_fromDocx (mammoth npm package)
│   │   │   └── image.extractor.ts    # ← ExtractionService_fromImage (tesseract.js/node-tesseract-ocr)
│   │   ├── nlp/
│   │   │   ├── nlp-engine.service.ts # ← NLPEngine_extractFields (Regex+Keyword — คงเดิมทุกจุด)
│   │   │   ├── tokenizer.ts          # ← NLPEngine_tokenize
│   │   │   ├── jaccard.ts            # ← NLPEngine_jaccardSimilarity
│   │   │   └── keyword-dictionaries.ts # ← NLP_MINISTRY_KEYWORDS, SECTION_KEYWORDS, NLP_STOP_KEYWORDS
│   │   ├── review/
│   │   │   ├── review-engine.service.ts # ← ReviewEngine_run (orchestrator)
│   │   │   ├── checks/
│   │   │   │   ├── coverage.check.ts    # ← coverageCheckHtml logic
│   │   │   │   ├── budget.check.ts      # ← budgetCheckHtml logic
│   │   │   │   ├── payment.check.ts     # ← paymentCheckHtml + sumClose()
│   │   │   │   └── fairness.check.ts    # ← fairnessCheckHtml logic
│   │   │   └── scoring.ts               # ← overall score formula
│   │   ├── kb.service.ts             # ← KB_RAW/KB_CHUNKED + chunking logic (Math.ceil(len/500))
│   │   └── export.service.ts         # ← exportTor() → server-side render .html/.docx/.pdf
│   │
│   ├── workers/                      # Background job processors (BullMQ)
│   │   ├── extraction.worker.ts      # รับงาน OCR หนักๆ ออกจาก request/response cycle
│   │   └── review.worker.ts
│   │
│   ├── models/                       # ORM models (Prisma/TypeORM) — ดู ER diagram เอกสาร 07
│   │   ├── user.model.ts
│   │   ├── project.model.ts
│   │   ├── projectSection.model.ts
│   │   ├── extractedField.model.ts
│   │   ├── kbDocument.model.ts
│   │   ├── kbChunk.model.ts
│   │   └── reviewResult.model.ts
│   │
│   ├── middleware/
│   │   ├── auth.middleware.ts        # ตรวจ JWT Bearer token
│   │   ├── rateLimit.middleware.ts
│   │   ├── fileUpload.middleware.ts  # multer/busboy config (20MB limit)
│   │   └── errorHandler.middleware.ts # ← มาตรฐาน Error Envelope (เอกสาร 08 หัวข้อ 8)
│   │
│   ├── config/
│   │   ├── db.ts
│   │   ├── redis.ts
│   │   └── vectorStore.ts            # Qdrant/pgvector client
│   │
│   └── app.ts
├── prisma/schema.prisma               # หรือ migrations/ ถ้าใช้ TypeORM
├── package.json
└── Dockerfile
```

---

## 3. ตาราง Mapping: PoC Function → Production Module

| ฟังก์ชัน/ตัวแปรใน PoC | ไฟล์ Production (Backend) | ไฟล์ Production (Frontend) |
|---|---|---|
| `AuthService_register/login` | `services/auth.service.ts` | `services/authService.ts` |
| `DB_USERS[]` | `models/user.model.ts` (PostgreSQL) | `store/authStore.ts` |
| `ProjectService_create/get` | `services/project.service.ts` | `services/projectService.ts` |
| `projects[]` | `models/project.model.ts` | `store/projectStore.ts` |
| `ExtractionService_extract` | `services/extraction/extraction.service.ts` | `services/extractionService.ts` |
| `ExtractionService_fromPDF` | `services/extraction/pdf.extractor.ts` | — (เรียกผ่าน API) |
| `ExtractionService_fromDocx` | `services/extraction/docx.extractor.ts` | — |
| `ExtractionService_fromImage` | `services/extraction/image.extractor.ts` | — |
| `NLPEngine_extractFields` | `services/nlp/nlp-engine.service.ts` | — |
| `NLPEngine_jaccardSimilarity` | `services/nlp/jaccard.ts` | — |
| `SECTION_KEYWORDS` | `services/nlp/keyword-dictionaries.ts` | — |
| `ReviewEngine_run` | `services/review/review-engine.service.ts` | `services/reviewService.ts` (เรียก API) |
| `renderDashboard()` | — | `pages/DashboardPage/*` |
| `renderPhaseFlow/renderPhaseContent` | — | `pages/DraftTorPage/*` |
| `renderKbRaw/renderKbChunked` | `services/kb.service.ts` | `pages/KnowledgeBasePage/*` |
| `exportTor()` | `services/export.service.ts` | `pages/DraftTorPage/Phase4Publish.tsx` |
| `openModal/closeModal` | — | `components/common/Modal.tsx` |

---

## 4. Shared Types / Contracts

แนะนำให้สร้าง shared package (`packages/shared-types/`) ในโครงสร้าง monorepo เพื่อให้ Frontend/Backend ใช้ type เดียวกัน ลดความเสี่ยง field ไม่ตรงกัน:

```typescript
// packages/shared-types/src/project.ts
export type ProjectStatus = 'draft' | 'progress' | 'done';

export interface ExtractedFields {
  projectName?: string;
  ministry?: string;
  budget?: number;
  timeline?: string;
  problem?: string;
  paymentPercents?: number[];
  paymentPercentsText?: string;
  evaluationMethod?: string;
  paidupSuggest?: string;
}

export interface Project {
  id: string;
  name: string;
  ministry: string;
  budget: number;
  status: ProjectStatus;
  currentPhase: 0 | 1 | 2 | 3 | 4;
  progressPct?: number;
  extracted?: ExtractedFields;
  sectionProgress: Record<string, boolean>;
  updatedAt: string;
}

export interface ReviewCheckResult {
  id: 'sectionCoverage' | 'paidupCapital' | 'paymentSchedule' | 'brandFairness' | 'legalReference' | 'comparisonSimilarity';
  status: 'pass' | 'warn' | 'fail' | 'info';
  message: string;
  [key: string]: unknown;
}
```

---

## 5. Monorepo Layout (แนะนำ)

```
tor-generator/
├── apps/
│   ├── frontend/        # โครงสร้างตามหัวข้อ 1
│   └── backend/         # โครงสร้างตามหัวข้อ 2
├── packages/
│   └── shared-types/    # ตามหัวข้อ 4
├── infra/
│   ├── docker-compose.yml     # local dev: postgres, redis, qdrant, backend, frontend
│   └── k8s/                   # deployment manifests (อ้างอิง Deployment Diagram เอกสาร 07)
├── docs/                 # เอกสาร 01-11 ทั้งหมดเก็บไว้ที่นี่
├── package.json          # npm workspaces / pnpm workspace
└── turbo.json             # (ถ้าใช้ Turborepo สำหรับ build caching)
```

**ข้อแนะนำการย้ายจาก PoC:** เนื่องจากตรรกะ Regex/Keyword/Jaccard ใน PoC เป็น pure function ที่ไม่พึ่งพา DOM สามารถ **copy-paste เกือบทั้งหมด** จาก `<script>` ในไฟล์ `06-UXUI-Mockup.html` ไปวางใน `services/nlp/*.ts` ได้ทันที เพียงเปลี่ยนจาก DOM manipulation เป็น return value/JSON — เป็นข้อดีของการออกแบบ PoC แบบ Rule-based ที่ไม่ผูกกับ UI

---
*เอกสาร 09 — Backend/Frontend Development Structure | Mapping ทุกฟังก์ชันจาก PoC สู่โครงสร้าง Production | สอดคล้องกับเอกสาร 07 (Architecture) และ 08 (API Reference)*
