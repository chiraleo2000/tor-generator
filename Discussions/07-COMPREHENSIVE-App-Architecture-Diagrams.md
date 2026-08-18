# 07 — COMPREHENSIVE App Architecture Diagrams
### ระบบ TOR Generator (ร่าง TOR + ตรวจสอบ TOR) — สถาปัตยกรรมเชิงลึกระดับ System / Component / Sequence / Deployment / Data Model

เอกสารนี้ต่อเนื่องจากเอกสาร 05 (Flow Diagrams) โดยลงรายละเอียดสถาปัตยกรรมให้ครอบคลุมมากขึ้นในระดับที่ใช้อ้างอิงสำหรับทีมพัฒนาจริง ครอบคลุมทั้งสถาปัตยกรรมของ **PoC ปัจจุบัน** (Client-only, Rule-based, ไม่มี LLM) และสถาปัตยกรรม **เป้าหมาย Production** ที่ต่อยอดจาก PoC

สอดคล้องกับเอกสาร 01 (โครงสร้าง TOR), 02 (ขั้นตอนการร่าง), 03 (ภาพรวมสถาปัตยกรรมเทคนิค) และ 04 (คู่มือ Implementation ของ Component)

---

## สารบัญ

1. [System Context Diagram (C4 Level 1)](#1-system-context-diagram-c4-level-1)
2. [Container Diagram (C4 Level 2)](#2-container-diagram-c4-level-2)
3. [Component Diagram — PoC ปัจจุบัน](#3-component-diagram--poc-ปัจจุบัน)
4. [Component Diagram — Production เป้าหมาย](#4-component-diagram--production-เป้าหมาย)
5. [Sequence Diagram: Login / Register](#5-sequence-diagram-login--register)
6. [Sequence Diagram: ร่าง TOR (Upload → OCR → NLP → Mapping)](#6-sequence-diagram-ร่าง-tor-upload--ocr--nlp--mapping)
7. [Sequence Diagram: ตรวจสอบ TOR (Rule-based Review Engine)](#7-sequence-diagram-ตรวจสอบ-tor-rule-based-review-engine)
8. [Deployment Diagram — Production](#8-deployment-diagram--production)
9. [Data Model / ER Diagram](#9-data-model--er-diagram)
10. [State Diagram: สถานะโครงการ TOR](#10-state-diagram-สถานะโครงการ-tor)
11. [Class/Module Diagram: Service Layer ของ PoC](#11-classmodule-diagram-service-layer-ของ-poc)

---

## 1. System Context Diagram (C4 Level 1)

ภาพรวมว่าระบบ TOR Generator มีปฏิสัมพันธ์กับใคร/อะไรบ้างในระดับสูงสุด

```mermaid
flowchart TB
    User(("ผู้ใช้งาน<br/>เจ้าหน้าที่พัสดุ/จัดซื้อ<br/>ภาครัฐ"))
    Approver(("ผู้อนุมัติ<br/>(หัวหน้างาน)"))
    System["🖥️ ระบบ TOR Generator<br/>(ร่าง TOR + ตรวจสอบ TOR)<br/>Rule-based, No LLM"]
    Legal[("แหล่งข้อมูลกฎหมาย/ระเบียบ<br/>พ.ร.บ. จัดซื้อจัดจ้าง 2560<br/>ระเบียบกระทรวงการคลัง")]
    KBSource[("คลังเอกสารองค์กร<br/>ประกาศราคากลาง/TOR ตัวอย่างเดิม")]
    OCRLibs["ไลบรารี OCR ภายนอก<br/>pdf.js / mammoth.js / Tesseract.js<br/>(โหลดผ่าน CDN)"]

    User -->|อัปโหลดเอกสาร, กรอกข้อมูล, สั่งร่าง/ตรวจ| System
    Approver -->|ทบทวน/อนุมัติ TOR| System
    System -->|อ้างอิงตรวจสอบความถูกต้อง| Legal
    System -->|ดึงมาแนะนำเนื้อหา| KBSource
    System -->|เรียกใช้สกัดข้อความ| OCRLibs
    System -->|ส่งออกไฟล์ TOR .html| User
```

**หมายเหตุ:** ใน PoC ปัจจุบัน "แหล่งข้อมูลกฎหมาย/ระเบียบ" และ "คลังเอกสารองค์กร" เป็นข้อมูลจำลอง (hardcoded array ในโค้ด) ที่อ้างอิงชื่อไฟล์จริงจากคลังเอกสารขององค์กร ส่วนใน Production จะเชื่อมต่อกับ Knowledge Base Service จริงตามที่ระบุในเอกสาร 08 (API Reference)

---

## 2. Container Diagram (C4 Level 2)

แสดง "container" หลักของระบบทั้งสถานะปัจจุบันและเป้าหมาย รวมในภาพเดียวเพื่อให้เห็น mapping การย้ายจาก PoC ไป Production

```mermaid
flowchart TB
    subgraph Current["🟡 PoC ปัจจุบัน — Single HTML File, Client-only"]
        direction TB
        C1["Browser Runtime<br/>(HTML+CSS+Vanilla JS)"]
        C2[("In-memory JS State<br/>ไม่มี Database จริง")]
        C1 <--> C2
    end

    subgraph Target["🟢 Production เป้าหมาย"]
        direction TB
        T1["Web SPA<br/>React/Vue + Router"]
        T2["API Gateway / BFF"]
        T3["Auth Service"]
        T4["Project + Draft Service"]
        T5["Review Service"]
        T6["Knowledge Base Service"]
        T7["OCR/NLP Worker<br/>(เริ่มจาก Rule-based เดิม)"]
        T8[("PostgreSQL")]
        T9[("Vector Store<br/>Qdrant/pgvector")]
        T10[("Object Storage<br/>ไฟล์ต้นฉบับ")]

        T1 --> T2
        T2 --> T3 & T4 & T5 & T6
        T4 & T5 --> T7
        T3 & T4 & T5 --> T8
        T6 --> T9
        T7 --> T10
    end

    Current -.->|"ย้าย Logic เดิม (Auth/Extraction/NLP/Review)<br/>ไปเป็น Backend Service"| Target
```

---

## 3. Component Diagram — PoC ปัจจุบัน

รายละเอียดของ Component ภายในไฟล์ `06-UXUI-Mockup.html` ตามฟังก์ชันจริงในโค้ด

```mermaid
flowchart TB
    subgraph UI["UI / View Layer"]
        AuthUI["Auth Screen<br/>(#authScreen)"]
        Dash["Dashboard<br/>renderDashboard()"]
        KBUI["Knowledge Base<br/>renderKbRaw/renderKbChunked"]
        DraftUI["ร่าง TOR<br/>renderPhaseFlow/renderPhaseContent"]
        ReviewUI["ตรวจสอบ TOR<br/>reviewFileSelected/runReviewCheck"]
        GuideUI["คู่มือ<br/>renderGuide"]
    end

    subgraph Services["Service Layer (จำลอง Backend เป็น JS Functions)"]
        AuthSvc["AuthService_login/register"]
        ProjSvc["ProjectService_create/get"]
        ExtractSvc["ExtractionService_extract<br/>(detectType→fromPDF/fromDocx/fromImage)"]
        NLPEng["NLPEngine_extractFields<br/>tokenize/jaccardSimilarity"]
        ReviewEng["ReviewEngine_run<br/>+ coverageCheck/budgetCheck/<br/>paymentCheck/fairnessCheck"]
    end

    subgraph Data["In-memory Data"]
        Users[("DB_USERS[]")]
        Projects[("projects[]")]
        KBRaw[("KB_RAW[] / KB_CHUNKED[]")]
        SectionKW[("SECTION_KEYWORDS{}")]
    end

    AuthUI --> AuthSvc --> Users
    Dash --> ProjSvc --> Projects
    KBUI --> KBRaw
    DraftUI --> ProjSvc
    DraftUI --> ExtractSvc --> NLPEng
    NLPEng --> Projects
    ReviewUI --> ExtractSvc
    ReviewUI --> ReviewEng
    ReviewEng --> SectionKW
    ReviewEng --> NLPEng
    GuideUI -.-> UI
```

---

## 4. Component Diagram — Production เป้าหมาย

```mermaid
flowchart TB
    subgraph FE["Frontend"]
        SPA["SPA (React/Vue)"]
        StateMgmt["State Management<br/>(Redux/Pinia/Zustand)"]
        SPA --> StateMgmt
    end

    subgraph BE["Backend Microservices"]
        AuthAPI["Auth Service<br/>JWT + bcrypt"]
        ProjAPI["Project/Draft Service"]
        ReviewAPI["Review Service"]
        KBAPI["Knowledge Base Service"]
        NLPWorker["NLP/OCR Worker<br/>(Queue-based)"]
        NotifSvc["Notification Service<br/>(อนุมัติ/แจ้งเตือน)"]
    end

    subgraph Infra["Infrastructure"]
        Queue["Message Queue<br/>(RabbitMQ/SQS)"]
        DB[("PostgreSQL")]
        Vector[("Qdrant/pgvector")]
        Storage[("Object Storage S3-compatible")]
        Cache[("Redis Cache")]
    end

    SPA -->|REST/GraphQL| AuthAPI & ProjAPI & ReviewAPI & KBAPI
    ProjAPI -->|enqueue OCR job| Queue --> NLPWorker
    ReviewAPI -->|enqueue review job| Queue
    NLPWorker --> Storage
    NLPWorker --> DB
    AuthAPI & ProjAPI & ReviewAPI --> DB
    KBAPI --> Vector
    ProjAPI --> NotifSvc
    AuthAPI --> Cache
```

---

## 5. Sequence Diagram: Login / Register

```mermaid
sequenceDiagram
    actor U as ผู้ใช้
    participant UI as Auth Screen
    participant Auth as AuthService_*
    participant DB as DB_USERS[] (Production: PostgreSQL)

    U->>UI: กรอกชื่อ/หน่วยงาน/อีเมล/รหัสผ่าน (Register)
    UI->>Auth: AuthService_register(name,org,email,password)
    Auth->>Auth: ตรวจสอบ email regex + password length>=6
    Auth->>DB: ตรวจสอบอีเมลซ้ำ
    alt อีเมลซ้ำ หรือข้อมูลไม่ถูกต้อง
        Auth-->>UI: {ok:false, error}
        UI-->>U: แสดง showAuthError()
    else ข้อมูลถูกต้อง
        Auth->>DB: บันทึกผู้ใช้ใหม่
        Auth-->>UI: {ok:true}
        UI-->>U: showAuthSuccess() → switchAuth('login')
        U->>UI: กรอกอีเมล/รหัสผ่าน (Login)
        UI->>Auth: AuthService_login(email,password)
        Auth->>DB: ค้นหาผู้ใช้ที่ตรงกัน
        Auth-->>UI: {ok:true, user}
        UI->>UI: currentUser = user, enterApp()
        UI-->>U: แสดง Dashboard
    end
```

---

## 6. Sequence Diagram: ร่าง TOR (Upload → OCR → NLP → Mapping)

```mermaid
sequenceDiagram
    actor U as ผู้ใช้
    participant P0 as Phase 0 UI
    participant Ext as ExtractionService_extract
    participant Lib as pdf.js / mammoth.js / Tesseract.js
    participant NLP as NLPEngine_extractFields
    participant Proj as projects[currentProjectId]
    participant P2 as Phase 2 Section Flow UI

    U->>P0: อัปโหลดไฟล์ (PDF/DOCX/Image)
    P0->>Ext: ExtractionService_extract(file)
    Ext->>Ext: detectType(file)
    Ext->>Lib: fromPDF() / fromDocx() / fromImage()
    alt สกัดสำเร็จ
        Lib-->>Ext: raw text
        Ext-->>P0: {ok:true, text}
        P0->>NLP: NLPEngine_extractFields(text)
        NLP-->>P0: {projectName, ministry, budget, timeline,<br/>problem, paymentPercents, evaluationMethod, paidupSuggest}
        P0->>Proj: pr.extracted = fields
        P0-->>U: แสดงผลจับคู่ matched/partial ต่อหมวด
        U->>P2: ไปยัง Phase 2 (ร่างเนื้อหา)
        P2->>Proj: อ่าน pr.extracted[mapField]
        P2-->>U: Pre-fill ฟอร์มแต่ละหมวดโดยอัตโนมัติ
    else สกัดล้มเหลว (เช่น CDN ไม่พร้อม/ไฟล์เสีย)
        Lib-->>Ext: throw error
        Ext-->>P0: {ok:false, error}
        P0-->>U: แสดงข้อความ "สกัดข้อความล้มเหลว" (Graceful degradation)<br/>ผู้ใช้กรอกข้อมูลเองได้ตามปกติ
    end
```

---

## 7. Sequence Diagram: ตรวจสอบ TOR (Rule-based Review Engine)

```mermaid
sequenceDiagram
    actor U as ผู้ใช้
    participant RUI as Review TOR UI
    participant Ext as ExtractionService_extract
    participant RE as ReviewEngine_run
    participant KW as SECTION_KEYWORDS
    participant NLP as NLPEngine_*

    U->>RUI: อัปโหลดไฟล์ TOR ที่สมบูรณ์
    RUI->>Ext: extract(file) → reviewFileText
    opt เพิ่มโครงการเปรียบเทียบ (Optional)
        U->>RUI: อัปโหลดไฟล์โครงการอ้างอิง
        RUI->>Ext: extract(file) ต่อโครงการ
        Ext-->>RUI: compareProjects[].text
    end
    U->>RUI: กดปุ่ม "เริ่มตรวจสอบ TOR"
    RUI->>RE: ReviewEngine_run(reviewFileText, compareProjects)
    RE->>KW: ตรวจ Keyword ครบ 10 หมวด → coveragePct
    RE->>NLP: NLPEngine_extractFields(text) → fields
    RE->>RE: ตรวจ Budget/ทุนจดทะเบียน (25% threshold)
    RE->>RE: ตรวจผลรวมงวดจ่ายเงิน (sumClose 100%)
    RE->>RE: ตรวจ Brand-lock Fairness (ยี่ห้อ vs หรือเทียบเท่า)
    RE->>RE: ตรวจการอ้างอิงกฎหมาย (Regex พ.ร.บ./ระเบียบ)
    opt มีโครงการเปรียบเทียบ
        RE->>NLP: jaccardSimilarity(text, compare.text) ต่อโครงการ
    end
    RE->>RE: คำนวณ Overall Score (Coverage50%+Legal15%+Budget15%+Payment20%)
    RE-->>RUI: HTML ผลตรวจสอบ 6 รายการ + คะแนนรวม
    RUI-->>U: แสดงผลตรวจสอบพร้อมคำแนะนำ
```

---

## 8. Deployment Diagram — Production

```mermaid
flowchart TB
    subgraph ClientDevice["🖥️ Client Device"]
        Browser["Web Browser<br/>SPA (Static Assets จาก CDN)"]
    end

    subgraph EdgeCDN["🌐 CDN / Edge"]
        CDN["Static Asset CDN<br/>(CloudFront/Cloudflare)"]
    end

    subgraph Cloud["☁️ Cloud Environment (เช่น AWS/Azure/GCP หรือ On-prem ภาครัฐ)"]
        subgraph LB["Load Balancer / API Gateway"]
            GW["Ingress / API Gateway<br/>+ TLS Termination"]
        end
        subgraph K8s["Container Orchestration (Kubernetes/ECS)"]
            AuthPod["Auth Service Pods"]
            ProjPod["Project/Draft Service Pods"]
            ReviewPod["Review Service Pods"]
            KBPod["Knowledge Base Service Pods"]
            WorkerPod["OCR/NLP Worker Pods<br/>(Autoscale ตามคิวงาน)"]
        end
        subgraph DataTier["Data Tier"]
            PG[("PostgreSQL<br/>Primary+Replica")]
            VDB[("Qdrant/pgvector<br/>Vector Store")]
            S3[("Object Storage<br/>ไฟล์เอกสารต้นฉบับ")]
            Redis[("Redis<br/>Session/Cache")]
        end
        MQ["Message Queue<br/>(RabbitMQ/SQS)"]
    end

    Browser --> CDN
    Browser -->|HTTPS API Calls| GW
    GW --> AuthPod & ProjPod & ReviewPod & KBPod
    ProjPod & ReviewPod --> MQ --> WorkerPod
    WorkerPod --> S3
    WorkerPod --> PG
    AuthPod --> Redis
    AuthPod & ProjPod & ReviewPod --> PG
    KBPod --> VDB
```

---

## 9. Data Model / ER Diagram

โครงสร้างข้อมูลเป้าหมายสำหรับ Production (แปลงจาก in-memory arrays ของ PoC)

```mermaid
erDiagram
    USERS {
        uuid id PK
        string name
        string organization
        string email
        string password_hash
        datetime created_at
    }
    PROJECTS {
        uuid id PK
        uuid owner_id FK
        string name
        string ministry
        bigint budget
        string status "draft | progress | done"
        int current_phase "0-4"
        datetime updated_at
    }
    PROJECT_SECTIONS {
        uuid id PK
        uuid project_id FK
        string section_key "s1..s10"
        string sub_key "4.1..4.14 (nullable)"
        text content
        boolean is_filled
    }
    EXTRACTED_FIELDS {
        uuid id PK
        uuid project_id FK
        string field_name
        text field_value
        string source_file
    }
    KB_DOCUMENTS {
        uuid id PK
        string category
        string filename
        string file_type
        boolean is_mandatory
        int size_kb
    }
    KB_CHUNKS {
        uuid id PK
        uuid document_id FK
        int chunk_index
        text chunk_text
        vector embedding
    }
    REVIEW_RESULTS {
        uuid id PK
        uuid project_id FK
        int coverage_pct
        boolean legal_ref_ok
        boolean budget_ok
        boolean payment_ok
        boolean fairness_ok
        int overall_score
        datetime checked_at
    }

    USERS ||--o{ PROJECTS : owns
    PROJECTS ||--o{ PROJECT_SECTIONS : contains
    PROJECTS ||--o{ EXTRACTED_FIELDS : has
    PROJECTS ||--o{ REVIEW_RESULTS : "reviewed as"
    KB_DOCUMENTS ||--o{ KB_CHUNKS : "chunked into"
```

---

## 10. State Diagram: สถานะโครงการ TOR

```mermaid
stateDiagram-v2
    [*] --> draft: สร้างโครงการใหม่
    draft --> draft: แก้ไข (editProject)
    draft --> progress: submitForApproval() / เริ่มประมวลผล
    progress --> progress: ระบบกำลังสร้าง (progressPct เพิ่มขึ้น)
    progress --> done: ประมวลผลเสร็จสมบูรณ์ (100%)
    done --> done: ปรับปรุง (viewProject + แก้ไขต่อ)
    done --> [*]: Export TOR (.html)

    note right of progress
        ขณะสถานะ "กำลังดำเนินการ"
        ปุ่มการกระทำจะถูก disable
        จนกว่าสร้างเสร็จ (ตาม feedback ผู้ใช้)
    end note
```

---

## 11. Class/Module Diagram: Service Layer ของ PoC

แสดงความสัมพันธ์ระหว่างฟังก์ชัน/โมดูลจริงในไฟล์ `06-UXUI-Mockup.html` ที่จะกลายเป็น Backend Service ใน Production (เทียบละเอียดกับ API ในเอกสาร 08)

```mermaid
classDiagram
    class AuthService {
        +register(name, org, email, password)
        +login(email, password)
        -DB_USERS[]
    }
    class ProjectService {
        +create(name, ministry, budget)
        +get(id)
        -projects[]
    }
    class ExtractionService {
        +detectType(file)
        +fromPDF(file)
        +fromDocx(file)
        +fromImage(file)
        +extract(file)
    }
    class NLPEngine {
        +extractFields(text)
        +tokenize(text)
        +jaccardSimilarity(textA, textB)
        -NLP_MINISTRY_KEYWORDS[]
        -NLP_STOP_KEYWORDS[]
    }
    class ReviewEngine {
        +run(text, compares)
        -coverageCheckHtml()
        -budgetCheckHtml()
        -paymentCheckHtml()
        -fairnessCheckHtml()
        -sumClose(arr, target)
        -SECTION_KEYWORDS : Map
    }

    ProjectService --> ExtractionService : ใช้ในการอัปโหลดเอกสารอ้างอิง
    ExtractionService --> NLPEngine : ส่งข้อความที่สกัดได้ไปวิเคราะห์
    ReviewEngine --> ExtractionService : สกัดข้อความจากไฟล์ที่ตรวจสอบ
    ReviewEngine --> NLPEngine : ใช้ extractFields + jaccardSimilarity
    AuthService ..> ProjectService : currentUser เชื่อมกับ owner ของโครงการ
```

---

## สรุปการต่อยอดจาก PoC สู่ Production

| องค์ประกอบใน PoC (Client-only) | บทบาทใน Production |
|---|---|
| `AuthService_*` + `DB_USERS[]` | Auth Service + PostgreSQL + JWT/bcrypt |
| `ProjectService_*` + `projects[]` | Project/Draft Service + PostgreSQL |
| `ExtractionService_*` (pdf.js/mammoth.js/Tesseract.js) | OCR/NLP Worker (Queue-based, scale ได้) — เริ่มจาก Rule-based เดิม ต่อยอดเป็น ML ได้ในอนาคต |
| `NLPEngine_*` (Regex/Keyword/Jaccard) | คงเป็น Rule-based Service เดิม หรือเสริมด้วย NLP Model แยกส่วน |
| `ReviewEngine_*` | Review Service (เรียกใช้ NLP Engine + Section Keyword Rules) |
| `KB_RAW[]` / `KB_CHUNKED[]` | Knowledge Base Service + Vector Store (Qdrant/pgvector) จริง |
| In-memory JS variables | PostgreSQL + Redis Cache |

---
*เอกสาร 07 — COMPREHENSIVE App Architecture Diagrams | สอดคล้องกับเอกสาร 01-06 | ระบบ Rule-based ทั้งหมด ไม่มีการเรียกใช้ LLM*
