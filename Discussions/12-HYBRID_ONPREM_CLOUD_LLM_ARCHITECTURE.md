# 12 — HYBRID ON-PREMISE / CLOUD LLM ARCHITECTURE
### ระบบ TOR Generator — สถาปัตยกรรม AI/LLM แบบ Hybrid (On-Premise / Cloud) พร้อม RAG และ Orchestration

เอกสารนี้ต่อยอดจากเอกสาร 07 (สถาปัตยกรรมของ PoC ที่เป็น Rule-based ล้วน ไม่มี LLM) โดยออกแบบสถาปัตยกรรมชั้นที่เพิ่มขึ้นมาสำหรับการใช้ **LLM + RAG ช่วยร่าง/ตรวจ TOR** ควบคู่กับ Rule Engine เดิม (ซึ่งยังคงทำงานเป็น **Deterministic Guardrail** ตรวจสอบผลลัพธ์จาก LLM เสมอ — ไม่ปล่อยให้ LLM ตัดสินใจเรื่องกฎหมาย/ตัวเลขเพียงลำพัง)

**หลักการออกแบบสำคัญ:** ระบบต้องรองรับ 3 รูปแบบการติดตั้งโดยไม่ต้องแก้โค้ดหลัก เปลี่ยนแค่ Environment Variable — **On-Premise Only** (ข้อมูลไม่ออกนอกองค์กรเลย เหมาะกับข้อมูลจัดซื้อจัดจ้างที่มีชั้นความลับ), **Cloud** (ใช้บริการ Managed เต็มรูปแบบเพื่อคุณภาพ/ความเร็วสูงสุด), และ **Hybrid** (เลือกได้ต่อ Component)

---

## สารบัญ

1. [Deployment Profiles — 3 รูปแบบการติดตั้ง](#1-deployment-profiles--3-รูปแบบการติดตั้ง)
2. [Technology Decision Matrix](#2-technology-decision-matrix)
3. [Provider Abstraction Layer (Strategy Pattern)](#3-provider-abstraction-layer-strategy-pattern)
4. [LangGraph Orchestration — AI-Assisted TOR Drafting Workflow](#4-langgraph-orchestration--ai-assisted-tor-drafting-workflow)
5. [Sequence Diagrams: การเรียกใช้ LLM แต่ละแบบ](#5-sequence-diagrams-การเรียกใช้-llm-แต่ละแบบ)
6. [Embedding & RAG Retrieval Pipeline](#6-embedding--rag-retrieval-pipeline)
7. [Deployment Topology Diagrams](#7-deployment-topology-diagrams)
8. [User Journey ข้าม Deployment Mode](#8-user-journey-ข้าม-deployment-mode)
9. [Tool Stack Mindmap](#9-tool-stack-mindmap)
10. [Roadmap การพัฒนา (Gantt)](#10-roadmap-การพัฒนา-gantt)
11. [Configuration Reference](#11-configuration-reference)
12. [Cost / Latency / Privacy Comparison](#12-cost--latency--privacy-comparison)
13. [Security & Compliance Notes](#13-security--compliance-notes)

---

## 1. Deployment Profiles — 3 รูปแบบการติดตั้ง

| Profile | เมื่อไรควรใช้ | LLM | Embedding | Vector Store |
|---|---|---|---|---|
| **On-Premise Only** | ข้อมูลจัดซื้อจัดจ้างชั้นความลับสูง / นโยบาย Data Residency ของหน่วยงาน / ไม่มีอินเทอร์เน็ตออกนอกองค์กร | LM Studio: OpenThaiChinda-4B หรือ Qwen3.5-8B (Q4_K_M) | Qwen3-Embedding-4B (local) | Qdrant self-hosted หรือ PostgreSQL+pgvector self-hosted |
| **Cloud** | ต้องการคุณภาพ/ความเร็วสูงสุด มีงบประมาณ API และข้อมูลอนุญาตให้ประมวลผลบน Cloud ได้ | Claude Sonnet API (พร้อม Prompt Caching) | OpenAI Embedding (text-embedding-3-large/small) | Qdrant Cloud หรือ PostgreSQL+pgvector (RDS/managed) |
| **Hybrid** | ต้องการยืดหยุ่นต่อ Component เช่น Extraction/Rule Engine รันในองค์กร แต่ LLM Drafting เรียก Cloud เมื่อได้รับอนุญาต | สลับได้ต่อ Project/ต่อ Request | สลับได้ | สลับได้ (แนะนำ sync ข้อมูลระหว่าง 2 ฝั่งด้วย batch job) |

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#dbeafe','primaryTextColor':'#1e3a8a','primaryBorderColor':'#1e3a8a','lineColor':'#c41e3a','secondaryColor':'#fed7aa','secondaryTextColor':'#92400e','tertiaryColor':'#f9fafb'}}}%%
flowchart LR
    Req["ผู้ใช้/โครงการ"] --> Mode{"DEPLOYMENT_MODE"}
    Mode -->|on_prem| OP["On-Premise Only<br/>LM Studio + Qwen3-Embedding-4B<br/>+ Qdrant/pgvector self-hosted"]:::onprem
    Mode -->|cloud| CL["Cloud<br/>Claude Sonnet API + OpenAI Embedding<br/>+ Qdrant Cloud/pgvector managed"]:::cloud
    Mode -->|hybrid| HY["Hybrid<br/>เลือก Provider ต่อ Component"]:::hybrid
    HY -.-> OP
    HY -.-> CL

    classDef onprem fill:#dcfce7,stroke:#15803d,color:#166534,stroke-width:2px
    classDef cloud fill:#dbeafe,stroke:#1e3a8a,color:#1e3a8a,stroke-width:2px
    classDef hybrid fill:#fed7aa,stroke:#f59e0b,color:#92400e,stroke-width:2px
```

---

## 2. Technology Decision Matrix

### 2.1 LLM: ต้นทุน vs ความเป็นส่วนตัวของข้อมูล

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'quadrant1Fill':'#dbeafe','quadrant2Fill':'#dcfce7','quadrant3Fill':'#f9fafb','quadrant4Fill':'#fed7aa'}}}%%
quadrantChart
    title เลือก LLM ตาม Cost vs Data Privacy
    x-axis "ต้นทุนต่ำ" --> "ต้นทุนสูง"
    y-axis "Privacy ต่ำ" --> "Privacy สูง"
    quadrant-1 "คุณภาพสูง ข้อมูลออกนอกองค์กร"
    quadrant-2 "จุดสมดุลที่ดี"
    quadrant-3 "ควรหลีกเลี่ยง"
    quadrant-4 "จ่ายแพงเพื่อ Cloud"
    "Claude Sonnet API (+Cache)": [0.62, 0.22]
    "Qwen3.5-8B Q4_K_M (LM Studio)": [0.25, 0.80]
    "OpenThaiChinda-4B (LM Studio)": [0.16, 0.95]
```

### 2.2 Vector Store: Qdrant vs PostgreSQL+pgvector

| ประเด็น | Qdrant | PostgreSQL + pgvector |
|---|---|---|
| ความเร็วค้นหาที่ Scale ใหญ่ (>1M vectors) | ดีกว่า (HNSW แบบ native, filter เร็ว) | ดีพอสำหรับ < 1-5M vectors |
| ความซับซ้อนในการ Operate | ต้องดูแลระบบเพิ่ม 1 ตัว | ใช้ Postgres ที่มีอยู่แล้ว ลด Ops overhead |
| เหมาะกับ On-Premise ขนาดเล็ก | ได้ (self-hosted single binary/Docker) | เหมาะมาก (หน่วยงานส่วนใหญ่มี PostgreSQL อยู่แล้ว) |
| เหมาะกับ Cloud ขนาดใหญ่ | เหมาะมาก (Qdrant Cloud managed) | เหมาะ (RDS/Aurora + pgvector extension) |
| Backup/DR ร่วมกับข้อมูลอื่น | แยกระบบ backup | Backup รวมกับข้อมูล Transactional เดิมได้ |
| **คำแนะนำ** | เลือกเมื่อ KB ใหญ่มาก (หลายแสนเอกสาร) หรือมี Cloud Budget | เลือกเป็นค่าเริ่มต้น (Default) — ลด Ops และ KB ของระบบนี้ (~586 chunks) ยังเล็กมาก |

> ระบบออกแบบให้ใช้ **VectorStoreProvider interface เดียว** (ดูหัวข้อ 3) จึงสลับสองตัวนี้ได้โดยไม่กระทบ Business Logic — แนะนำเริ่มจาก pgvector (ลดจำนวนระบบที่ต้องดูแล) แล้วย้ายไป Qdrant เมื่อ Knowledge Base โตเกิน ~1 ล้าน chunk

### 2.3 Embedding: Local vs Cloud

| ประเด็น | Qwen3-Embedding-4B (Local) | OpenAI text-embedding-3 (Cloud) |
|---|---|---|
| ข้อมูลออกนอกองค์กร | ไม่ออก | ออก (ส่งไป OpenAI) |
| รองรับภาษาไทย | ดี (Multilingual, เทรนรวมภาษาไทย) | ดี (Multilingual) |
| ต้นทุนต่อการใช้งาน | ค่าไฟ/GPU เท่านั้น (Sunk cost) | จ่ายตาม token (~$0.00002-0.00013/1K token) |
| Latency | ขึ้นกับ GPU องค์กร | เร็วและสม่ำเสมอ (Cloud infra) |
| ต้อง Sync Dimension กับ Vector Store | ต้องกำหนด schema ให้ตรงตอน migrate ข้าม provider | เช่นเดียวกัน |

---

## 3. Provider Abstraction Layer (Strategy Pattern)

ออกแบบเป็น 3 Interface หลัก โดยใช้ **LangChain's base classes เป็นสัญญา (contract)** เพราะ LangChain มี adapter ให้ทั้ง Claude (`ChatAnthropic`), Local model ผ่าน LM Studio (`ChatOpenAI` ชี้ไปที่ base_url ของ LM Studio ซึ่งเปิด endpoint แบบ OpenAI-compatible), OpenAI Embedding (`OpenAIEmbeddings`), และ Vector Store ทั้ง Qdrant (`QdrantVectorStore`)/pgvector (`PGVector`) อยู่แล้ว — ไม่ต้องเขียน adapter เองทั้งหมด

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#f9fafb','primaryTextColor':'#1f2937','primaryBorderColor':'#1e3a8a','lineColor':'#c41e3a'}}}%%
classDiagram
    class LLMProvider {
        <<interface>>
        +invoke(messages, tools) LLMResponse
        +stream(messages) Iterator
    }
    class ClaudeSonnetProvider {
        -apiKey
        -cachePrompt bool
        +invoke() : ใช้ ChatAnthropic + cache_control breakpoints
    }
    class LocalLMStudioProvider {
        -baseUrl "http://localhost:1234/v1"
        -model "openthai-chinda-4b" | "qwen3.5-8b-q4_k_m"
        +invoke() : ใช้ ChatOpenAI ชี้ base_url ไป LM Studio
    }
    LLMProvider <|.. ClaudeSonnetProvider
    LLMProvider <|.. LocalLMStudioProvider

    class EmbeddingProvider {
        <<interface>>
        +embedQuery(text) vector
        +embedDocuments(texts) vector[]
    }
    class OpenAIEmbeddingProvider {
        -model "text-embedding-3-large"
    }
    class Qwen3LocalEmbeddingProvider {
        -baseUrl "http://localhost:1234/v1"
        -model "qwen3-embedding-4b"
    }
    EmbeddingProvider <|.. OpenAIEmbeddingProvider
    EmbeddingProvider <|.. Qwen3LocalEmbeddingProvider

    class VectorStoreProvider {
        <<interface>>
        +upsert(id, vector, metadata)
        +search(vector, topK, filter) results[]
    }
    class QdrantProvider {
        -url
        -collection "tor_kb"
    }
    class PgVectorProvider {
        -connectionString
        -table "kb_chunks"
    }
    VectorStoreProvider <|.. QdrantProvider
    VectorStoreProvider <|.. PgVectorProvider

    class ProviderFactory {
        +getLLM(mode) LLMProvider
        +getEmbedding(mode) EmbeddingProvider
        +getVectorStore(mode) VectorStoreProvider
    }
    ProviderFactory --> LLMProvider
    ProviderFactory --> EmbeddingProvider
    ProviderFactory --> VectorStoreProvider
```

**หลักการ:** โค้ดฝั่ง Business Logic (LangGraph nodes) เรียกผ่าน `ProviderFactory.getLLM(process.env.DEPLOYMENT_MODE)` เท่านั้น ไม่ import provider ที่เจาะจงตรงๆ — ทำให้สลับ Provider เป็น **1 บรรทัด config** ไม่ต้องแก้ตรรกะ

---

## 4. LangGraph Orchestration — AI-Assisted TOR Drafting Workflow

ใช้ **LangGraph StateGraph** ควบคุมลำดับขั้นตอนแบบมีเงื่อนไข/วนซ้ำ/หยุดรอมนุษย์ (Human-in-the-loop) — จุดสำคัญคือ **Rule Engine เดิม (จากเอกสาร 07) ทำหน้าที่เป็น Guardrail Node ที่ตรวจผลลัพธ์จาก LLM ก่อนส่งต่อเสมอ** ถ้าไม่ผ่านจะวนกลับไปให้ LLM แก้ไขพร้อม feedback ที่เป็นรูปธรรม (ไม่ใช่แค่ "ผิด" แต่บอกว่าผิดกฎไหน)

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#dbeafe','primaryTextColor':'#1e3a8a','primaryBorderColor':'#1e3a8a','lineColor':'#c41e3a','tertiaryColor':'#fef3e2'}}}%%
stateDiagram-v2
    [*] --> ExtractNode
    ExtractNode: 📥 Extract Node<br/>OCR เดิมจาก PoC — Deterministic
    ExtractNode --> RetrieveNode

    RetrieveNode: 🔎 Retrieve Node<br/>RAG จาก Qdrant/pgvector<br/>Embedding: Qwen3/OpenAI
    RetrieveNode --> LLMDraftNode

    LLMDraftNode: 🤖 LLM Draft Node<br/>Claude Sonnet (cloud) หรือ<br/>LM Studio Local (on-prem)
    LLMDraftNode --> RuleGuardrailNode

    RuleGuardrailNode: ⚖️ Rule Guardrail Node<br/>ReviewEngine เดิม — Deterministic<br/>ตรวจ Budget/Payment%/กฎหมาย/Fairness

    state GuardrailChoice <<choice>>
    state RetryChoice <<choice>>
    RuleGuardrailNode --> GuardrailChoice
    GuardrailChoice --> HumanReviewNode : ผ่านกฎ (score ≥ threshold)
    GuardrailChoice --> RetryChoice : ไม่ผ่าน
    RetryChoice --> LLMDraftNode : วนซ้ำ ≤3 ครั้ง (ส่ง feedback กลับ)
    RetryChoice --> HumanReviewNode : เกิน 3 ครั้ง (ส่งให้คนตัดสินพร้อม flag)

    HumanReviewNode: 👤 Human Review Node<br/>เจ้าหน้าที่ยืนยัน/แก้ไขเนื้อหา
    HumanReviewNode --> ApprovedNode : อนุมัติ
    HumanReviewNode --> LLMDraftNode : ขอให้ร่างใหม่

    ApprovedNode: ✅ Finalize & Export
    ApprovedNode --> [*]
```

**เหตุผลของการออกแบบนี้:** ป้องกัน LLM Hallucination ในเนื้อหาที่มีผลทางกฎหมาย/การเงิน (เช่น สัดส่วนเงินประกัน, การอ้างอิง พ.ร.บ.) โดยให้ Rule Engine ที่ deterministic และผ่านการทดสอบแล้ว (เอกสาร 06/07) เป็นผู้ตัดสินสุดท้ายก่อนถึงมนุษย์ — LLM มีหน้าที่แค่ "ช่วยร่างให้เร็วขึ้น" ไม่ใช่ "ตัดสินความถูกต้อง"

---

## 5. Sequence Diagrams: การเรียกใช้ LLM แต่ละแบบ

### 5.1 Cloud: Claude Sonnet API พร้อม Prompt Caching

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'actorBkg':'#1e3a8a','actorTextColor':'#ffffff','actorBorderColor':'#0f2340','signalColor':'#374151','signalTextColor':'#1f2937','noteBkgColor':'#fef3e2','noteBorderColor':'#f59e0b','noteTextColor':'#92400e'}}}%%
sequenceDiagram
    participant LG as LangGraph Node
    participant LC as LangChain ChatAnthropic
    participant Cache as Anthropic Prompt Cache
    participant API as Claude Sonnet API

    LG->>LC: invoke(system=KB_context+TOR_rules, messages=[...])
    LC->>API: POST /v1/messages<br/>system blocks มี cache_control:{type:"ephemeral"}
    Note over API,Cache: KB Context (มักซ้ำทุก request<br/>ของโครงการเดียวกัน) ถูก cache
    alt Cache Hit (เรียกครั้งที่ 2+ ในโครงการเดียวกัน)
        API->>Cache: ตรวจ cache ของ system block
        Cache-->>API: hit — ไม่ต้องประมวลผล prompt ซ้ำ
        API-->>LC: ตอบเร็วขึ้น + ค่าใช้จ่าย token ลด ~90%
    else Cache Miss (ครั้งแรก)
        API->>API: ประมวลผล prompt ทั้งหมด + เขียน cache (TTL 5 นาที)
        API-->>LC: คำตอบ + usage.cache_creation_input_tokens
    end
    LC-->>LG: LLMResponse (เนื้อหาร่าง TOR หมวดที่ขอ)
```

### 5.2 On-Premise: LM Studio (OpenThaiChinda-4B / Qwen3.5-8B Q4_K_M)

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'actorBkg':'#15803d','actorTextColor':'#ffffff','actorBorderColor':'#166534','signalColor':'#374151','signalTextColor':'#1f2937'}}}%%
sequenceDiagram
    participant LG as LangGraph Node
    participant LC as LangChain ChatOpenAI<br/>(base_url=LM Studio)
    participant LMS as LM Studio Server<br/>(localhost:1234)
    participant GPU as GPU องค์กร<br/>(Qwen3.5-8B Q4_K_M /<br/>OpenThaiChinda-4B)

    LG->>LC: invoke(system=KB_context+TOR_rules, messages=[...])
    LC->>LMS: POST /v1/chat/completions (OpenAI-compatible)
    LMS->>GPU: โหลด weight (ครั้งแรก) + inference
    GPU-->>LMS: token stream
    LMS-->>LC: response (ไม่มีข้อมูลออกนอกเครือข่ายองค์กรเลย)
    LC-->>LG: LLMResponse
    Note over LG,GPU: ไม่มีค่าใช้จ่าย API ต่อ request<br/>Latency ขึ้นกับสเปค GPU/CPU ขององค์กร
```

### 5.3 RAG Retrieval (ใช้ร่วมกันทั้ง 2 โหมด — สลับ Provider ผ่าน Factory)

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'actorBkg':'#f59e0b','actorTextColor':'#ffffff','actorBorderColor':'#92400e'}}}%%
sequenceDiagram
    participant RN as RetrieveNode (LangGraph)
    participant EF as ProviderFactory.getEmbedding()
    participant VF as ProviderFactory.getVectorStore()

    RN->>EF: embedQuery("ขอบเขตงาน e-Payment กรมสรรพากร")
    alt DEPLOYMENT_MODE=on_prem
        EF->>EF: ใช้ Qwen3-Embedding-4B (LM Studio /v1/embeddings)
    else DEPLOYMENT_MODE=cloud
        EF->>EF: ใช้ OpenAI text-embedding-3-large
    end
    EF-->>RN: query vector (dim ตาม provider)
    RN->>VF: search(vector, topK=5, filter={category:"scope_of_work"})
    alt Vector Store = Qdrant
        VF->>VF: Qdrant HNSW search
    else Vector Store = pgvector
        VF->>VF: PostgreSQL "<->" operator (cosine distance)
    end
    VF-->>RN: top-5 chunks พร้อม metadata แหล่งที่มา
    RN->>RN: ประกอบ Context สำหรับ LLM Draft Node
```

---

## 6. Embedding & RAG Retrieval Pipeline

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#dbeafe','primaryTextColor':'#1e3a8a','primaryBorderColor':'#1e3a8a','lineColor':'#c41e3a'}}}%%
flowchart TB
    Doc[("เอกสาร KB<br/>586 chunks ปัจจุบัน")] --> Chunk["Text Chunking<br/>(~500 chars/chunk เดิมจาก PoC)"]
    Chunk --> Route{"DEPLOYMENT_MODE"}
    Route -->|on_prem| E1["Qwen3-Embedding-4B<br/>(Local, ผ่าน LM Studio)"]:::onprem
    Route -->|cloud| E2["OpenAI text-embedding-3<br/>(Cloud API)"]:::cloud
    E1 --> VS{"VECTOR_STORE"}
    E2 --> VS
    VS -->|qdrant| Q[("Qdrant Collection<br/>tor_kb")]:::onprem
    VS -->|pgvector| P[("PostgreSQL + pgvector<br/>kb_chunks table")]:::cloud
    Q --> Retrieve["RAG Retrieval<br/>(cosine similarity topK)"]
    P --> Retrieve
    Retrieve --> LLM["LLM Draft Node<br/>(Claude / Local)"]

    classDef onprem fill:#dcfce7,stroke:#15803d,color:#166534,stroke-width:2px
    classDef cloud fill:#dbeafe,stroke:#1e3a8a,color:#1e3a8a,stroke-width:2px
```

---

## 7. Deployment Topology Diagrams

### 7.1 On-Premise Only

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#dcfce7','primaryTextColor':'#166534','primaryBorderColor':'#15803d','lineColor':'#15803d'}}}%%
flowchart TB
    subgraph DC["🏢 Data Center ขององค์กร (ไม่มีข้อมูลออกอินเทอร์เน็ต)"]
        FE["Web SPA (Internal Network)"]
        BE["Backend API + LangGraph Orchestrator"]
        LMS["LM Studio Server<br/>OpenThaiChinda-4B / Qwen3.5-8B Q4_K_M<br/>+ Qwen3-Embedding-4B"]
        VDB[("Qdrant หรือ PostgreSQL+pgvector<br/>Self-hosted")]
        PG[("PostgreSQL<br/>Users/Projects")]
        S3[("On-prem Object Storage<br/>(MinIO)")]
    end
    FE --> BE
    BE --> LMS
    BE --> VDB
    BE --> PG
    BE --> S3
```

### 7.2 Cloud

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#dbeafe','primaryTextColor':'#1e3a8a','primaryBorderColor':'#1e3a8a','lineColor':'#1e3a8a'}}}%%
flowchart TB
    FE["Web SPA (CDN)"] --> GW["API Gateway"]
    subgraph CloudEnv["☁️ Cloud Environment"]
        GW --> BE["Backend API + LangGraph Orchestrator"]
        BE -->|"HTTPS + Prompt Cache"| Claude["Claude Sonnet API"]
        BE --> OpenAIEmb["OpenAI Embedding API"]
        BE --> VDB[("Qdrant Cloud หรือ<br/>PostgreSQL+pgvector Managed (RDS)")]
        BE --> PG[("Managed PostgreSQL")]
        BE --> S3[("S3-compatible Object Storage")]
    end
```

### 7.3 Hybrid

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#fed7aa','primaryTextColor':'#92400e','primaryBorderColor':'#f59e0b','lineColor':'#c41e3a'}}}%%
flowchart TB
    FE["Web SPA"] --> BE["Backend API + LangGraph Orchestrator<br/>+ ProviderFactory"]
    subgraph OnPremSide["🏢 On-Premise"]
        BE -->|"ข้อมูลดิบ/OCR/Rule Engine"| LMS["LM Studio (Fallback/ข้อมูลลับ)"]
        BE --> VDBLocal[("pgvector Local<br/>(ข้อมูลลับ)")]
    end
    subgraph CloudSide["☁️ Cloud"]
        BE -->|"ร่างเนื้อหาที่อนุญาตให้ประมวลผลนอกองค์กร"| Claude["Claude Sonnet API"]
        BE --> VDBCloud[("Qdrant Cloud<br/>(ข้อมูลสาธารณะ/กฎหมาย)")]
    end
    BE -.->|"Sync แบบ Batch Job รายวัน"| VDBLocal
    BE -.->|"Sync แบบ Batch Job รายวัน"| VDBCloud
```

---

## 8. User Journey ข้าม Deployment Mode

```mermaid
journey
    title ผู้ใช้ร่าง TOR ด้วยความช่วยเหลือของ AI (Hybrid Mode)
    section เตรียมข้อมูล
      อัปโหลดเอกสารอ้างอิง: 5: ผู้ใช้
      ระบบ OCR สกัดข้อความ (Rule-based เดิม): 4: ระบบ
    section AI ช่วยร่าง
      ระบบค้นหา Context จาก KB (RAG): 4: ระบบ
      LLM ร่างเนื้อหาแต่ละหมวด: 5: ระบบ, LLM
      Rule Engine ตรวจสอบผลลัพธ์ LLM: 4: ระบบ
    section ตรวจทานโดยมนุษย์
      เจ้าหน้าที่ทบทวนเนื้อหาที่ AI ร่าง: 5: ผู้ใช้
      แก้ไข/อนุมัติ: 5: ผู้ใช้
    section เผยแพร่
      Export เอกสาร TOR: 5: ผู้ใช้
```

---

## 9. Tool Stack Mindmap

```mermaid
mindmap
  root((TOR Generator<br/>Hybrid AI Stack))
    Orchestration
      LangChain
        Chains/Retrievers
        Provider Adapters
      LangGraph
        StateGraph
        Human-in-the-loop
    LLM
      Cloud
        Claude Sonnet API
        Prompt Caching
      On-Premise
        LM Studio
        OpenThaiChinda-4B
        Qwen3.5-8B Q4_K_M
    Embedding
      Cloud
        OpenAI text-embedding-3
      On-Premise
        Qwen3-Embedding-4B
    Vector Store
      Qdrant
      PostgreSQL + pgvector
    Guardrail
      Rule Engine เดิม
        Coverage Check
        Budget/Payment Check
        Fairness Check
        Legal Reference Check
```

---

## 10. Roadmap การพัฒนา (Gantt)

```mermaid
gantt
    title Roadmap: Rule-based PoC สู่ Hybrid AI Production
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d
    section Phase 1 - เสร็จแล้ว
    Rule-based PoC + OCR/NLP        :done, p1, 2026-07-01, 2026-08-13
    section Phase 2 - RAG Foundation
    ตั้งค่า Qdrant/pgvector + Embedding Pipeline   :active, p2a, 2026-08-14, 14d
    Chunk KB จริง + ทดสอบ Retrieval Quality        :p2b, after p2a, 10d
    section Phase 3 - LLM Orchestration
    Provider Abstraction Layer (LangChain)         :p3a, after p2b, 10d
    LangGraph Workflow + Guardrail Integration     :p3b, after p3a, 14d
    section Phase 4 - Hybrid Deployment
    Deploy On-Premise (LM Studio + pgvector)       :p4a, after p3b, 10d
    Deploy Cloud (Claude API + Qdrant Cloud)       :p4b, after p3b, 10d
    ทดสอบสลับ Provider แบบ Config-driven            :p4c, after p4a, 7d
    section Phase 5 - Production Hardening
    Security Review + Load Test                    :p5, after p4c, 14d
```

---

## 11. Configuration Reference

```bash
# ===== ตัวเลือกหลัก =====
DEPLOYMENT_MODE=on_prem            # on_prem | cloud | hybrid

# ===== LLM Provider =====
LLM_PROVIDER=local                 # claude | local
CLAUDE_API_KEY=sk-ant-xxxxx
CLAUDE_MODEL=claude-sonnet-4-5
CLAUDE_PROMPT_CACHE_ENABLED=true

LMSTUDIO_BASE_URL=http://gpu-server.internal:1234/v1
LMSTUDIO_MODEL=qwen3.5-8b-instruct-q4_k_m   # หรือ openthai-chinda-4b

# ===== Embedding Provider =====
EMBEDDING_PROVIDER=local           # openai | local
OPENAI_API_KEY=sk-xxxxx
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
LOCAL_EMBEDDING_MODEL=qwen3-embedding-4b
LOCAL_EMBEDDING_BASE_URL=http://gpu-server.internal:1234/v1

# ===== Vector Store =====
VECTOR_STORE=pgvector              # qdrant | pgvector
QDRANT_URL=http://qdrant.internal:6333
QDRANT_COLLECTION=tor_kb
PGVECTOR_CONNECTION_STRING=postgresql://user:pass@localhost:5432/tor_generator
PGVECTOR_TABLE=kb_chunks

# ===== LangGraph =====
LANGGRAPH_MAX_RETRY_LOOPS=3        # จำนวนครั้งสูงสุดที่ LLM แก้ไขตาม Rule Guardrail ก่อนส่งมนุษย์
LANGGRAPH_CHECKPOINT_STORE=postgres # ใช้ PostgreSQL เก็บ state สำหรับ human-in-the-loop resume
```

---

## 12. Cost / Latency / Privacy Comparison

| ปัจจัย | On-Premise Only | Cloud |
|---|---|---|
| ต้นทุนต่อ Request | ค่าไฟ/GPU (Sunk Cost, คงที่) | จ่ายตาม token (ผันแปร แต่ลดได้ด้วย Prompt Caching ~90%) |
| Latency | ขึ้นกับสเปค GPU องค์กร (อาจช้ากว่าถ้า GPU ไม่พอ) | เร็วและสม่ำเสมอ |
| คุณภาพงานเขียน/ภาษาไทย | ดี (โมเดลเฉพาะทาง เช่น OpenThaiChinda) แต่ต่ำกว่า Claude Sonnet โดยรวม | สูงสุดในกลุ่มที่ทดสอบ |
| Data Sovereignty | ข้อมูลไม่ออกนอกองค์กรเลย ✅ | ข้อมูลส่งไป Anthropic/OpenAI (ต้องตรวจ Data Processing Agreement) |
| ความพร้อมใช้งาน (Availability) | ขึ้นกับ Infra องค์กรเอง | SLA จากผู้ให้บริการ Cloud |
| ความเหมาะสมกับ TOR ชั้นความลับสูง | ✅ แนะนำ | ควรพิจารณา Data Classification ก่อน |

---

## 13. Security & Compliance Notes

- **On-Premise:** ควร air-gap เครือข่ายที่รัน LM Studio จากอินเทอร์เน็ตสาธารณะถ้าเป็นไปได้ (allow-list เฉพาะ update ที่จำเป็น) และเข้ารหัส Volume ที่เก็บ model weights/ฐานข้อมูล
- **Cloud:** ตรวจสอบ Data Processing Agreement (DPA) ของ Anthropic/OpenAI ว่าตรงกับระเบียบข้อมูลภาครัฐ (เช่น พ.ร.บ.คุ้มครองข้อมูลส่วนบุคคล 2562) และเปิดใช้ **Zero Data Retention** หรือ enterprise tier ที่ไม่ใช้ข้อมูลไป train โมเดล ถ้ามีให้เลือก
- **Prompt Caching (Claude):** cache เก็บที่ฝั่ง Anthropic ชั่วคราว (TTL สั้น ~5 นาทีตามค่า default ของ API) — ควรตรวจนโยบายการเก็บข้อมูลของ Anthropic ก่อนนำเนื้อหาที่มีข้อมูลอ่อนไหวมาก (เช่น ราคากลางที่ยังไม่ประกาศ) ไปใส่ใน prompt ที่ cache
- **Rule Guardrail เป็นทั้ง Safety และ Compliance Control** — ทุกเนื้อหาที่ LLM ร่าง (ไม่ว่า Cloud หรือ Local) ต้องผ่าน `RuleGuardrailNode` เดิมจากเอกสาร 06/07 เสมอก่อนถึงมนุษย์ ป้องกันกรณี LLM สร้างตัวเลข/ข้อความที่ขัดกฎหมายจัดซื้อจัดจ้าง
- **Audit Log:** บันทึกทุกครั้งที่ LLM ถูกเรียก (provider, model, prompt hash, output hash, guardrail result) เพื่อรองรับการตรวจสอบภายหลัง — สำคัญมากสำหรับหน่วยงานราชการ

---
*เอกสาร 12 — Hybrid On-Premise/Cloud LLM Architecture | ต่อยอดจากเอกสาร 06/07 (Rule-based PoC) ด้วย LangChain + LangGraph Orchestration | Rule Engine เดิมยังคงเป็น Guardrail บังคับเสมอ ไม่ว่าจะใช้ LLM ตัวใด*
