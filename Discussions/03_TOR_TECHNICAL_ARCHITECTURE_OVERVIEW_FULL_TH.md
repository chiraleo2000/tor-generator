# ระบบสร้าง TOR อัตโนมัติ - สถาปัตยกรรมและเทคโนโลยี
## ส่วนที่ 03: ภาพรวมเทคนิคทั้งระบบ

---

## 📑 สารบัญ
1. [วิสัยทัศน์และเป้าหมายของระบบ](#วิสัยทัศน์และเป้าหมายของระบบ)
2. [สถาปัตยกรรมระบบแบบลำดับ 6 ชั้น](#สถาปัตยกรรมระบบแบบลำดับ-6-ชั้น)
3. [เลือกเทคโนโลยีและเหตุผล](#เลือกเทคโนโลยีและเหตุผล)
4. [กลวิธีการทำงานของระบบ LLM](#กลวิธีการทำงานของระบบ-llm)
5. [ตัวแทน AI ที่เชี่ยวชาญ 20 ตัว](#ตัวแทน-ai-ที่เชี่ยวชาญ-20-ตัว)
6. [การเก็บรักษาข้อมูลและระบบค้นหา](#การเก็บรักษาข้อมูลและระบบค้นหา)
7. [วิธีการปรับใช้ระบบ](#วิธีการปรับใช้ระบบ)

---

## 🎯 วิสัยทัศน์และเป้าหมายของระบบ

### ประเด็นปัญหาที่ต้องแก้ไข

ปัญหาปัจจุบันที่เจ้าหน้าที่ภาครัฐเผชิญ:

**ปัญหาที่ 1: ใช้เวลานาน**
- การสร้าง TOR ฉบับหนึ่งใช้เวลา 3-6 สัปดาห์
- เจ้าหน้าที่ต้องทำงานนอกเวลาเพื่อตรวจสอบและปรับแต่ง
- ลาเช่นการออกจากอำนาจในการซื้อขายได้ชะลอตัวลง
- ผลกระทบต่อเศรษฐกิจ: ความล่าช้าในการประมูล = ความล่าช้าในการสาธารณูปโภค

**ปัญหาที่ 2: ข้อผิดพลาดและความไม่สอดคล้อง**
- บาง TOR ไม่เป็นไปตามกฎหมายการจัดซื้อจัดจ้าง พ.ศ. 2560
- ข้อกำหนดไม่ชัดเจน → ผู้ขายสงสัย → ผู้เสนองานไม่มาเข้าร่วมประมูล
- ส่วนต่าง ๆ ของ TOR ไม่สัมพันธ์กัน เช่น:
  - งบประมาณ 100 ล้านบาท แต่ขอให้เสร็จใน 3 เดือน (เป็นไปไม่ได้)
  - ระบุคุณสมบัติที่บริษัทธรรมชาติไม่มี (เช่น ต้องใช้ Mainframe ขณะที่ระบบต้องการ Cloud)
- ข้อผิดพลาดด้านภาษาและการเขียน → ต้องแกไขหลายครั้ง

**ปัญหาที่ 3: ไม่มีมาตรฐานและตัวอย่าง**
- แต่ละกระทรวงมีวิธีเขียน TOR ที่แตกต่างกัน
- ไม่มีแบบเรียน (template) ที่ถูกต้องสำหรับภาครัฐไทย
- เจ้าหน้าที่ใหม่ต้องเรียนรู้โดยพยายาม (learning by doing)
- ความสูญเสีย: เวลา ต้นทุน ความซ้ำซ้อน

### วิสัยทัศน์ของระบบใหม่

```
ระบบสร้าง TOR อัตโนมัติด้วย AI จะช่วยให้:

✅ เจ้าหน้าที่ภาครัฐ
   ├─ สร้าง TOR ได้เร็วขึ้น 10 เท่า (จาก 3-6 สัปดาห์ → 30-45 นาที)
   ├─ ลดข้อผิดพลาดลง 80% (ด้วยการตรวจสอบอัตโนมัติ)
   ├─ มั่นใจว่า TOR ถูกกฎหมายและเหมาะสม
   └─ ใช้เวลาในการพิจารณาความเหมาะสมแทนการพิมพ์และแก้ไข

✅ หน่วยงานภาครัฐ
   ├─ ประมูลได้เร็วขึ้น → ได้สิ่งของ/บริการเร็วขึ้น
   ├─ มีผู้เสนองานมากขึ้น (เพราะ TOR ชัดเจน)
   ├─ ประหยัดงบประมาณ (โดยการแข่งขันที่ยุติธรรม)
   └─ มีฟังก์ชันการจัดซื้อจัดจ้างที่ดีขึ้น

✅ ผู้เสนองาน (ผู้ขาย)
   ├─ เข้าใจความต้องการได้ชัดเจน (TOR ชัดเจน)
   ├─ ลดการเสนองานที่ไม่จำเป็น
   ├─ สามารถเตรียมข้อเสนอที่เหมาะสมได้มากขึ้น
   └─ ลดต้นทุนการเสนองาน

✅ ประเทศไทย
   ├─ ปรับปรุงสัง่สมสินค้าและบริการสาธารณะ
   ├─ เพิ่มการแข่งขัน → ลดต้นทุน
   ├─ ลดการทุจริต (ความชัดเจนลดการจ้างงานแบบเลือกใคร)
   └─ เร่งการจัดส่งบริการสาธารณะ
```

### เป้าหมายที่เจาะจง

```
GOAL 1: ความเร็ว
├─ ปัจจุบัน: 3-6 สัปดาห์ (15-30 วันทำการ)
├─ เป้าหมาย: 30-45 นาที
├─ วิธี: AI + ระบบขั้นตอนแบบอัตโนมัติ
└─ วัดผล: เวลาจากคลิกปุ่ม "สร้าง" ถึงได้ TOR สำเร็จ

GOAL 2: คุณภาพ
├─ ปัจจุบัน: 70% ถูกต้องในการพยายามครั้งแรก
├─ เป้าหมาย: 95% ถูกต้องเมื่อสร้าง (ไม่ต้องแก้ไขมาก)
├─ วิธี: ตรวจสอบอัตโนมัติ 3 ระดับ (ข้อมูล + ความสอดคล้อง + กฎหมาย)
└─ วัดผล: คะแนนคุณภาพ 0-100 (ต้องเกิน 85)

GOAL 3: ความสอดคล้องตามกฎหมาย
├─ ปัจจุบัน: 65% เป็นไปตามกฎหมายพระราชบัญญัติจัดซื้อจัดจ้าง พ.ศ. 2560
├─ เป้าหมาย: 100% ถูกต้องตามกฎหมาย
├─ วิธี: ความรู้เกี่ยวกับกฎหมายในระบบ AI
└─ วัดผล: ผ่านการตรวจสอบกฎหมาย 100%

GOAL 4: การปรับแต่ง
├─ ปัจจุบัน: ต้องเขียนใหม่ทั้งหมด สำหรับอุตสาหกรรมต่าง ๆ
├─ เป้าหมาย: ระบบสามารถสร้าง TOR สำหรับอุตสาหกรรมต่างๆ ได้
├─ วิธี: เลือกแม่แบบ (template) ตามประเภทโครงการ
└─ วัดผล: เสร็จ ≥ 80% โดยอัตโนมัติสำหรับแต่ละอุตสาหกรรม

GOAL 5: ความเข้าใจได้ง่าย
├─ ปัจจุบัน: ต้องอ่านหนังสือเรียน TOR ก่อนใช้
├─ เป้าหมาย: คนทั่วไป (ไม่ใช่ผู้เชี่ยวชาญ) สามารถใช้ได้
├─ วิธี: อินเทอร์เฟซแบบ 8 ขั้นตอนง่าย + คำแนะนำ
└─ วัดผล: ผู้ใช้ 80% สามารถสร้าง TOR ใจครั้งแรกได้
```

---

## 🏗️ สถาปัตยกรรมระบบแบบลำดับ 6 ชั้น

### ภาพรวมของระบบ

```
┌─────────────────────────────────────────────────────────────┐
│ ชั้นที่ 1: อินเทอร์เฟสกับผู้ใช้ (User Interface Layer)         │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Next.js 14 + React 18 + TypeScript                    │   │
│ │ • ศูนย์ (Wizard) 8 ขั้นตอนให้ผู้ใช้กรอกข้อมูล             │   │
│ │ • ตัวอย่าง TOR ที่ปรับปรุงแบบ Real-time               │   │
│ │ • ข้อเสนอแนะจาก AI แสดงในแผง (sidebar) ด้านขวา        │   │
│ │ • ตรวจสอบความแตกต่าง (diff viewer) ระหว่างเวอร์ชัน    │   │
│ └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↑↓ (REST APIs)
┌─────────────────────────────────────────────────────────────┐
│ ชั้นที่ 2: ปลายทาง API และการจัดการคำขอ                      │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ FastAPI + Python 3.11+ (แบบ Async/await)             │   │
│ │ • ยาขึ้นคำขอ (routing) และตรวจสอบข้อมูล               │   │
│ │ • ตรวจสอบตัวตน (authentication) และสิทธิ์             │   │
│ │ • จำกัดจำนวนคำขอต่อวินาที (rate limiting)             │   │
│ │ • บันทึกลงใน log เพื่อตรวจติดตาม                      │   │
│ └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↑↓ (Message Queue)
┌─────────────────────────────────────────────────────────────┐
│ ชั้นที่ 3: จัดการตัวแทน AI และการทำงานเป็นขั้นตอน           │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Langchain + Langraph (Graph-based Workflow)          │   │
│ │ • ตัวแทน AI 20 ตัว ทำงานตามลำดับ                    │   │
│ │ • การประสานงานระหว่างตัวแทน                           │   │
│ │ • จัดการข้อผิดพลาดและลองใหม่                           │   │
│ │ • นับจำนวน Token (สำหรับต้นทุน API)                    │   │
│ └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↑↓ (Direct API calls)
┌─────────────────────────────────────────────────────────────┐
│ ชั้นที่ 4: ระบบ AI สำหรับการคิดและสร้างเนื้อหา               │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ ตัวเลือก LLM (Hybrid Strategy):                       │   │
│ │ • ระบบ Cloud: Claude 5 Sonnet (ผ่าน Anthropic API) │   │
│ │   ↳ ประสิทธิภาพสูง เข้าใจภาษาไทย ได้ดี              │   │
│ │   ↳ Token 200,000 ต่อครั้ง                            │   │
│ │ • ระบบ Local: Llama 3 Thai (llama.cpp / LM Studio)    │   │
│ │   ↳ ความเป็นส่วนตัว ไม่มีค่าใช้ API                  │   │
│ │ • สำรอง: Small local models สำหรับกรณีเฉพาะ           │   │
│ └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↑↓ (Vector operations)
┌─────────────────────────────────────────────────────────────┐
│ ชั้นที่ 5: ระบบค้นหาและดึงข้อมูลจากฐานความรู้                  │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Vector Database (pgvector ใน PostgreSQL)             │   │
│ │ • เก็บ 800-1000 vectors (ตัวอย่าง TOR)               │   │
│ │ • ค้นหาข้อมูลที่เหมือนกัน (similarity search)         │   │
│ │ • ใช้ Embeddings: OpenAI text-embedding-3-small       │   │
│ │                                                         │   │
│ │ MongoDB (ฐานข้อมูลเอกสาร)                             │   │
│ │ • ค้นหาแบบ Full-text ใน TOR documents                 │   │
│ │ • ดัชนี (index) ข้อมูลประกอบ                           │   │
│ └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↑↓ (SQL/Document queries)
┌─────────────────────────────────────────────────────────────┐
│ ชั้นที่ 6: ฐานข้อมูลและการเก็บรักษา                           │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ • PostgreSQL 16: เก็บโครงการ logs คำขอบริการ         │   │
│ │ • Redis 7.x: เก็บเซสชั่น (session) cache             │   │
│ │ • MongoDB 7.x: เก็บเอกสาร TOR ข้อมูลประกอบ           │   │
│ │ • MinIO: เก็บไฟล์ที่สร้าง (Word, PDF)                 │   │
│ └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### ขั้นตอนการทำงานของระบบ

เมื่อผู้ใช้กดปุ่ม "สร้าง TOR":

```
ขั้นที่ 1: ผู้ใช้ป้อนข้อมูล (8 ขั้นตอน)
   ├─ ขั้นที่ 1: ชื่อโครงการ, กระทรวง, งบประมาณ
   ├─ ขั้นที่ 2: คำบรรยายปัญหา (ระบบปัจจุบันมีปัญหาอะไร)
   ├─ ขั้นที่ 3: เป้าหมายที่ต้องการ (ต้องการอะไร)
   ├─ ขั้นที่ 4: ขอบเขตงาน (ต้องทำอะไรบ้าง)
   ├─ ขั้นที่ 5: คุณสมบัติของผู้เสนองาน (ต้องมีความสามารถอะไร)
   ├─ ขั้นที่ 6: งบประมาณและการจ่ายเงิน (จ่ายเมื่อไหร่)
   ├─ ขั้นที่ 7: ตรวจสอบและปรับแต่ง (อ่านร่าง TOR)
   └─ ขั้นที่ 8: ส่งออก (ดาวน์โหลด Word/PDF)
   
            ↓ (ผ่าน REST API)

ขั้นที่ 2: ตรวจสอบข้อมูล (FastAPI)
   ├─ ตรวจสอบข้อมูลที่หายไป
   ├─ ตรวจสอบประเภทข้อมูล (number, text, date)
   ├─ ตรวจสอบความขัดแย้ง (เช่น งบประมาณ vs เวลา)
   ├─ ทำความสะอาดข้อมูล (ลบสัญลักษณ์พิเศษ)
   └─ ส่งข้อมูลไปยังตัวแทน AI หรือคืนข้อผิดพลาด
   
            ↓ (ผ่าน Message Queue / Celery)

ขั้นที่ 3: ตัวแทน AI ทำงาน (Langraph Workflow)
   
   🔄 PHASE 1: การเตรียม (Parallel = ทำพร้อมกัน)
   ├─ Agent 0: ตรวจสอบข้อมูลอีกครั้ง
   ├─ Agent 0.5: เลือกแม่แบบ TOR ที่เหมาะสม
   └─ Agent 1: วิเคราะห์บริบทโครงการ
        ↓
        
   🔄 PHASE 2: สร้างส่วนต่าง ๆ ของ TOR (Sequential = ทำตามลำดับ)
   ├─ Agents 2-4: สร้าง Section 4.1-4.3 (ความเป็นมา, วัตถุประสงค์, คุณสมบัติ)
   ├─ Agents 5-10: สร้าง Section 4.4-4.8 (ฮาร์ดแวร์, ซอฟต์แวร์, งาน, ผลิตภัณฑ์)
   ├─ Agents 11-12: สร้าง Section 4.11-4.14 (บำรุงรักษา, ปฏิบัติการ, DR, ความปลอดภัย)
   └─ Agents 13-17: สร้าง Section 5-10 (เวลา, การประเมิน, งบประมาณ, เอกสาร)
        ↓
        
   🔄 PHASE 3: ตรวจสอบคุณภาพ (Parallel = ทำพร้อมกัน)
   ├─ Agent 18: ตรวจสอบความเป็นไปตามกฎหมาย
   ├─ Agent 19: ตรวจสอบความสอดคล้องภายใน
   └─ Agent 20: เสนอแนะการปรับปรุง
        ↓
        
   🔄 PHASE 4: ประกอบเข้าด้วยกัน
   ├─ รวมทั้งหมด 10 ส่วนเป็น TOR ฉบับเดียว
   ├─ บันทึกลงฐานข้อมูล
   └─ สร้างลิงก์ดาวน์โหลด
   
            ↓ (ผ่าน REST API)

ขั้นที่ 4: ส่งกลับให้ผู้ใช้
   ├─ แสดง TOR ใน UI (หน้าจอ)
   ├─ ปุ่มดาวน์โหลด Word/PDF
   ├─ ปุ่มปรับแต่ง (edit)
   └─ ปุ่มประวัติเวอร์ชัน (version history)
```

---

## 💻 เลือกเทคโนโลยีและเหตุผล

### ส่วนหน้าของระบบ (Frontend)

**ทำไมต้อง Next.js 14 + React 18 + TypeScript?**

```
1️⃣ Next.js 14
   ├─ ข้อดี:
   │  ├─ ขนาดเร็ว: หน้าแรกโหลดใน 1-2 วินาที
   │  ├─ SEO ดี: ดัชนีได้ในเครื่องมือค้นหา
   │  ├─ Route ง่าย: ไม่ต้องตั้งค่า router เอง
   │  └─ Vercel Deploy: ง่ายมาก (push code → deploy อัตโนมัติ)
   │
   ├─ ตัวอย่างเซ็ตอัพ:
   │  npx create-next-app@latest tor-generator
   │  npm run dev  # เปิด http://localhost:3000
   │
   └─ โครงการตัวอย่าง:
      ├─ app/page.tsx → หน้า /
      ├─ app/wizard/page.tsx → หน้า /wizard
      └─ app/api/tor/route.ts → ปลายทาง API /api/tor

2️⃣ React 18
   ├─ ข้อดี:
   │  ├─ Component-based: ทำให้โค้ดง่ายอ่าน
   │  ├─ Hooks: useState, useEffect ใช้ง่าย
   │  ├─ JSX Syntax: เขียนเหมือน HTML ปกติ
   │  └─ Community ใหญ่: ได้หนังสือ tutorial มากมาย
   │
   ├─ ตัวอย่าง Component:
   │  function WizardStep1() {
   │    const [projectName, setProjectName] = useState('')
   │    return (
   │      <input 
   │        value={projectName}
   │        onChange={(e) => setProjectName(e.target.value)}
   │      />
   │    )
   │  }
   │
   └─ สำหรับ TOR Generator ใช้ฟีเจอร์:
      ├─ Form handling (react-hook-form)
      ├─ State management (zustand)
      ├─ Data validation (zod)
      └─ UI components (shadcn/ui)

3️⃣ TypeScript
   ├─ ข้อดี:
   │  ├─ ป้องกันข้อผิดพลาด: บวก type จะหาปัญหาก่อนรัน
   │  ├─ IDE autocomplete: ตอนพิมพ์ IDE เสนอ function
   │  ├─ เอกสาร: type บอกเราว่า parameter คืออะไร
   │  └─ Refactor ง่าย: เปลี่ยนชื่อ variable ทั้งที่
   │
   ├─ ตัวอย่างข้อมูล (Type):
   │  interface ProjectInput {
   │    projectName: string
   │    ministry: string
   │    budget: number
   │    timeline_months: number
   │  }
   │
   └─ Compilation:
      TypeScript → JavaScript → Run on browser
```

**โครงสร้างโฟลเดอร์ Frontend:**

```
frontend/
├── app/
│   ├── page.tsx                    # หน้าแรก
│   ├── wizard/
│   │   ├── step1/page.tsx         # ขั้นตอนที่ 1
│   │   ├── step2/page.tsx         # ขั้นตอนที่ 2
│   │   └── ... (step 3-8)
│   ├── projects/page.tsx           # จัดการโครงการ
│   ├── dashboard/page.tsx          # แดชบอร์ด
│   └── auth/page.tsx               # เข้าระบบ
│
├── components/
│   ├── WizardForm.tsx             # ฟอร์มทั้งหมด
│   ├── TORPreview.tsx             # ตัวอย่าง TOR
│   ├── SuggestionsPanel.tsx       # แผงข้อเสนอแนะ
│   ├── VersionDiffViewer.tsx      # เปรียบเทียบเวอร์ชัน
│   └── common/
│       ├── Header.tsx
│       ├── Sidebar.tsx
│       └── Footer.tsx
│
├── lib/
│   ├── api.ts                     # ฟังก์ชัน API call
│   ├── validators.ts              # Zod schemas
│   └── formatters.ts              # ฟังก์ชันจัดรูป
│
├── store/
│   ├── wizardStore.ts             # Zustand state
│   ├── authStore.ts
│   └── appStore.ts
│
└── styles/
    └── globals.css                # Tailwind CSS
```

### ส่วนท้องปลายของระบบ (Backend)

**ทำไมต้อง FastAPI + Python?**

```
1️⃣ FastAPI
   ├─ ข้อดี:
   │  ├─ ความเร็ว: เร็วมาก (อันดับ 2 ของ Python)
   │  ├─ Async/await: ไม่ชัก (ทำได้หลายอย่างพร้อมกัน)
   │  ├─ Docs อัตโนมัติ: ไป /docs ดูเอกสาร API
   │  ├─ Validation: ตรวจสอบข้อมูลอัตโนมัติ
   │  └─ AI-friendly: ดีสำหรับ ML/LLM work
   │
   ├─ ตัวอย่าง FastAPI server:
   │  from fastapi import FastAPI
   │  app = FastAPI()
   │  
   │  @app.post("/api/v1/tor/generate")
   │  async def generate_tor(project: ProjectInput):
   │      # สร้าง TOR ตรงนี้
   │      return {"status": "generating", "id": project_id}
   │
   └─ เปิดดู API docs:
      http://localhost:8000/docs

2️⃣ Python
   ├─ ข้อดี:
   │  ├─ Langchain library: ทำการ AI ง่าย
   │  ├─ LLM Integration: ต่อ Claude API ง่าย
   │  ├─ Data processing: pandas, numpy มากมาย
   │  ├─ Async support: AsyncIO ในตัว
   │  └─ Community: ม python ใช้ AI/ML มากที่สุด
   │
   ├─ Version: 3.11+ (เพราะ support async ดี)
   │
   └─ ตัวอย่าง Langchain ใน Python:
      from langchain.llms import Anthropic
      llm = Anthropic(api_key="...")
      response = llm.predict("สร้าง TOR ให้ฉัน")
```

**โครงสร้างโฟลเดอร์ Backend:**

```
backend/
├── app/
│   ├── main.py                    # เริ่มต้น FastAPI
│   ├── config.py                  # ตั้งค่า (API keys, DB)
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── tor.py        # /api/v1/tor/*
│   │       │   ├── projects.py   # /api/v1/projects/*
│   │       │   ├── auth.py       # /api/v1/auth/*
│   │       │   └── health.py     # /api/v1/health
│   │       └── models/           # Pydantic schemas
│   │
│   ├── agents/                    # ตัวแทน AI 20 ตัว
│   │   ├── context_agents.py     # Agents 0, 0.5, 1
│   │   ├── section_agents.py     # Agents 2-17
│   │   ├── qa_agents.py          # Agents 18-20
│   │   └── prompts/              # ข้อความสั่ง AI
│   │
│   ├── rag/                       # ระบบค้นหา
│   │   ├── embeddings.py         # สร้าง vectors
│   │   ├── vector_store.py       # pgvector operations
│   │   └── retriever.py          # ค้นหาข้อมูล
│   │
│   ├── database/                  # ฐานข้อมูล
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── schemas.py            # Pydantic schemas
│   │   └── crud.py               # Create/Read/Update/Delete
│   │
│   ├── services/                  # ตรรมชาติการทำงาน
│   │   ├── tor_service.py        # สร้าง TOR logic
│   │   ├── project_service.py
│   │   └── export_service.py     # Export Word/PDF
│   │
│   ├── external/                  # API ภายนอก
│   │   ├── anthropic_client.py   # Claude API
│   │   ├── openai_client.py      # OpenAI embeddings
│   │   └── llama_client.py       # Local LLM
│   │
│   └── utils/
│       ├── tokens.py             # นับ token
│       ├── validators.py         # ตรวจสอบ
│       └── cache.py              # caching
│
├── alembic/                       # Database migrations
│   └── versions/
│       ├── 001_init_schema.py
│       ├── 002_add_embeddings.py
│       └── 003_add_audit_logs.py
│
├── tests/                         # การทดสอบ
│   ├── test_api.py
│   ├── test_agents.py
│   └── test_rag.py
│
└── docker/
    ├── Dockerfile
    └── requirements.txt
```

### ระบบ AI ที่ใช้ (LLM)

**ใช้ Claude 5 Sonnet (Primary) + Thai Local Models (Fallback)**

```
🚀 PRIMARY: Claude 5 Sonnet (Cloud)
   ├─ Model: Claude 5 Sonnet via Anthropic API
   ├─ ทำไม Claude 5 Sonnet:
   │   ├─ Advanced reasoning & logic
   │   ├─ Thai language: เข้าใจ formal/informal สมบูรณ์
   │   ├─ Context window: 200,000 tokens
   │   ├─ Function calling: JSON output ได้บริสุทธิ์
   │   └─ โมเดลที่เหมาะสุดสำหรับ TOR generation
   │
   ├─ ต้นทุน Claude 5 Sonnet:
   │   ├─ Input: $0.003 per 1K tokens
   │   ├─ Output: $0.015 per 1K tokens
   │   ├─ ต่อ TOR: ~$0.30-0.50 USD
   │   └─ สำหรับ 100 TOR/วัน: ~$30-50 USD (~1,000-1,700 บาท)
   │
   └─ Setup: ANTHROPIC_API_KEY=sk-ant-xxxxx
   
💾 LOCAL: Thai Models (Fallback)
   ├─ Models ที่ดี สำหรับภาษาไทย:
   │   ├─ LLaMA 3.1 Thai-specific (8B/70B)
   │   ├─ Mistral 7B-Thai
   │   ├─ Qwen with Thai finetuning
   │   └─ Setup: Ollama, llama.cpp, LM Studio
   │
   ├─ ใช้เมื่อ:
   │   ├─ API quota หมด
   │   ├─ ต้องการ offline operation
   │   ├─ Template/formatting tasks (ไม่ต้องดีมาก)
   │   └─ ใช้พื้นที่ storage เอง
   │
   └─ ตัวอย่าง: LLaMA 3.1 Thai 70B (GPU ≥24GB)
   
⚖️ ARCHITECTURE:
   ├─ PRIMARY (Tier 1): Claude 5 Sonnet → Critical sections
   ├─ FALLBACK (Tier 2): Local Thai Model → Minor/template
   └─ ERROR HANDLING: Retry logic + graceful degradation
```

**Claude 5 Sonnet - ทำไมถึงเป็นตัวเลือกที่ดี:**
```
✅ Reasoning: ความคิดลึก + logic ที่ชัดเจน
✅ Thai: เข้าใจ พระราชบัญญัติ, ราชการภาษาไทย สมบูรณ์
✅ Tokens: 200,000 context window → เอกสารใหญ่ได้
✅ Accuracy: 95%+ first-time generation
✅ Cost: ~$0.30/TOR (vs 3,000 บาท manual work)
```

**กลวิธีแบบ Hybrid (Cloud + Local):**

```
┌─────────────────────────────────────┐
│ ตัวเลือก LLM                         │
├─────────────────────────────────────┤
│                                     │
│ ✅ PRIMARY: Claude (Cloud)          │
│    ├─ ใช้เมื่อ: สร้างส่วนหลัก TOR    │
│    ├─ ราคา: ~$0.50 ต่อ TOR        │
│    ├─ เวลา: 5-10 นาที               │
│    └─ คุณภาพ: 95%+                  │
│                                     │
│ ⚡ LOCAL: Llama 3 Thai             │
│    ├─ ใช้เมื่อ: แม่แบบเลือก         │
│    ├─ ราคา: 0 บาท                  │
│    ├─ เวลา: 1-3 วินาที              │
│    └─ คุณภาพ: 75-80%               │
│                                     │
│ 🔄 FALLBACK: GPT-4 (ถ้า Claude down)│
│    ├─ ใช้เมื่อ: Emergency only      │
│    ├─ ราคา: แพง (2x Claude)       │
│    └─ หลีกเลี่ยง: อัตโนมัติ        │
│                                     │
└─────────────────────────────────────┘

ข้อดี Hybrid:
├─ ประหยัด: 70% งานใช้ local (ไม่มีค่า API)
├─ ความเป็นส่วนตัว: ข้อมูลที่ 30% ไม่ส่งออก
├─ ความเร็ว: Local ตอบเร็วมาก (0.5-1 วินาที)
└─ ความมั่นใจ: ถ้า API down ยังทำงานต่อได้ (เลือด slower)
```

---

## 🤖 กลวิธีการทำงานของระบบ LLM ขั้นสูง

### การประสานงาน LLM ด้วย Langchain + Langraph

```
เหตุผลเลือก Langchain + Langraph:

✅ Langchain:
   ├─ Library ที่ช่วยจัดการ LLM ง่ายขึ้น
   ├─ Support พหุ LLM (Claude, GPT, Llama, etc)
   ├─ ฟีเจอร์ Built-in:
   │  ├─ Memory management (จำประวัติการสนทนา)
   │  ├─ Prompt templates (แม่แบบคำสั่ง)
   │  ├─ Chains (เชื่อมคำสั่งต่อกัน)
   │  └─ RAG support (ค้นหาเอกสาร)
   └─ ตัวอย่าง:
      from langchain.llms import Anthropic
      from langchain.chains import LLMChain
      
      llm = Anthropic(api_key="...")
      chain = LLMChain(llm=llm, prompt=template)
      result = chain.run(input="...")

✅ Langraph (Graph-based Workflow):
   ├─ ให้เรากำหนดขั้นตอนการทำงาน (workflow)
   ├─ ตัวแทน AI สามารถรัน parallel หรือ sequential
   ├─ จัดการเงื่อนไข (if-else) ได้ง่าย
   ├─ เก็บ state ระหว่างขั้นตอน
   └─ ตัวอย่าง:
      from langgraph.graph import StateGraph
      
      workflow = StateGraph(state_schema=TORState)
      workflow.add_node("agent_1", agent_1_func)
      workflow.add_node("agent_2", agent_2_func)
      workflow.add_edge("agent_1", "agent_2")
      
      # เรียกใช้
      compiled_workflow = workflow.compile()
      result = compiled_workflow.invoke(initial_state)
```

### ลำดับการทำงานของ 20 ตัวแทน AI

**PHASE 1: การเตรียมการ (Preparation) - ทำพร้อมกัน (Parallel)**

```
┌─────────────────────────────────────────────────────┐
│ PHASE 1: เตรียมข้อมูล (รันพร้อมกัน)                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Agent 0: Data Validator                             │
│ ├─ ตรวจสอบข้อมูลใหม่                               │
│ ├─ ตรวจสอบ: จำนวน งบประมาณ วันที่                 │
│ ├─ ลบข้อมูลที่หายไป                                │
│ └─ Output: clean_data                               │
│                                                     │
│ Agent 0.5: Template Selector                        │
│ ├─ เลือก TOR template ที่เหมาะสม                  │
│ ├─ ประเภท: โครงการ IT, โครงการสาธารณูปโภค, etc  │
│ ├─ ดึงแม่แบบจาก MongoDB                            │
│ └─ Output: selected_template                        │
│                                                     │
│ Agent 1: Context Analyzer                           │
│ ├─ วิเคราะห์บริบทโครงการ                          │
│ ├─ สกัด: ความหมาย, วัตถุประสงค์, ข้อจำกัด       │
│ ├─ ค้นหา: TOR ที่คล้ายคลึง (similarity search)   │
│ └─ Output: project_context, similar_tors            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**PHASE 2: สร้างส่วนต่าง ๆ ของ TOR (Sequential - ทำตามลำดับ)**

```
┌─────────────────────────────────────────────────────┐
│ PHASE 2: สร้าง Section (ตามลำดับ)                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Agents 2-4: Section 4.1-4.3 (Background)            │
│ ├─ Agent 2: ความเป็นมา (Background)               │
│ │  ├─ สร้าง Section 4.1                           │
│ │  └─ ความยาว: 500-800 คำ                        │
│ │                                                  │
│ ├─ Agent 3: วัตถุประสงค์ (Objectives)             │
│ │  ├─ สร้าง Section 4.2                           │
│ │  ├─ ตัวอักษร 5-8 ข้อ (specific, measurable)    │
│ │  └─ ความยาว: 400-600 คำ                        │
│ │                                                  │
│ └─ Agent 4: คุณสมบัติ (Qualifications)             │
│    ├─ สร้าง Section 4.3                           │
│    ├─ ตรวจสอบ: ความเหมาะสม vs งบประมาณ        │
│    └─ ความยาว: 600-900 คำ                        │
│                                                     │
│ Agents 5-10: Section 4.4-4.8 (Requirements)        │
│ ├─ Agent 5: ฮาร์ดแวร์ (Hardware)                   │
│ │  ├─ เลือก: Server, Workstation, Network       │
│ │  └─ ได้ BOM (Bill of Materials)                 │
│ │                                                  │
│ ├─ Agent 6: ซอฟต์แวร์ (Software)                  │
│ │  ├─ OS, Database, Middleware, Tools            │
│ │  ├─ ตรวจสอบ: License ถูกกฎหมาย                │
│ │  └─ ได้ก่อรูปแบบติดตั้ง                         │
│ │                                                  │
│ ├─ Agent 7: งาน (Tasks)                            │
│ │  ├─ สร้าง: 50-100 งานย่อย (Work Breakdown)    │
│ │  ├─ ระบุ: ระยะเวลา dependencies ความพึงพอใจ  │
│ │  └─ ได้ Gantt Chart JSON                        │
│ │                                                  │
│ ├─ Agent 8: ผลิตภัณฑ์ (Deliverables)              │
│ │  ├─ สร้าง: 20-30 deliverables                   │
│ │  ├─ ตัวอย่าง: Document, Code, Training, etc   │
│ │  └─ ระบุ: วันมอบ, รูปแบบ, องค์ประกอบ          │
│ │                                                  │
│ └─ Agents 9-10: Support & Personnel               │
│    ├─ Agent 9: การสนับสนุน (Support)             │
│    │  ├─ Warranty: 1-3 ปี                        │
│    │  └─ SLA: Response time, availability        │
│    │                                              │
│    └─ Agent 10: บุคลากร (Personnel)               │
│       ├─ Project Manager, Tech Lead               │
│       ├─ Developers, QA, Support staff            │
│       └─ อัตจ้าง (headcount)                      │
│                                                     │
│ Agents 11-12: Section 4.11-4.14 (Operations)      │
│ ├─ Agent 11: บำรุงรักษา (Maintenance)              │
│ │  ├─ Bug fixes, Updates, Patches                 │
│ │  ├─ Preventive maintenance                      │
│ │  └─ ระยะเวลา: 1-3 ปี                           │
│ │                                                  │
│ └─ Agent 12: ดำเนินการ/การฟื้นตัว/ความปลอดภัย   │
│    ├─ Operations procedures                        │
│    ├─ Disaster Recovery plan                      │
│    └─ Security requirements                       │
│                                                     │
│ Agents 13-17: Section 5-10 (Supporting)            │
│ ├─ Agent 13: ระยะเวลา (Timeline)                  │
│ │  ├─ 52-week schedule                           │
│ │  └─ Milestones: Month 3, 6, 9, 12             │
│ │                                                  │
│ ├─ Agent 14: การประเมิน (Evaluation)              │
│ │  ├─ Criteria: functionality, performance      │
│ │  ├─ Score: 0-100 points                        │
│ │  └─ Pass/Fail thresholds                       │
│ │                                                  │
│ ├─ Agent 15: งบประมาณ (Budget)                    │
│ │  ├─ คำนวณ: รวมต้นทุน                            │
│ │  ├─ ตรวจสอบ: Paid-up capital = Budget/4       │
│ │  └─ ระบุ: Payment terms                        │
│ │                                                  │
│ ├─ Agent 16: การจ่ายเงิน (Payment)                │
│ │  ├─ Schedule: 4 milestones (30%-20%-30%-20%)  │
│ │  └─ ชำระเมื่อ: deliver + accept milestone     │
│ │                                                  │
│ └─ Agent 17: โทษ/เอกสาร (Penalties/Docs)          │
│    ├─ Late penalties: % per month                 │
│    ├─ Required documents                          │
│    └─ Approval process                            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**PHASE 3: ตรวจสอบคุณภาพ (QA) - ทำพร้อมกัน (Parallel)**

```
┌─────────────────────────────────────────────────────┐
│ PHASE 3: ตรวจสอบคุณภาพ (รันพร้อมกัน)               │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Agent 18: Legal Compliance Checker                 │
│ ├─ ตรวจสอบ: พระราชบัญญัติจัดซื้อจัดจ้าง        │
│ ├─ วิธี: ตรวจสอบจาก Knowledge Base                │
│ ├─ ผลลัพธ์: ✅ pass หรือ ⚠️ warning              │
│ └─ ตัวอย่างการตรวจสอบ:
│    ├─ Paid-up capital ≥ Budget/4 ?
│    ├─ Timeline realistic vs scope?
│    ├─ Qualifications clear & achievable?
│    └─ Payment terms reasonable?
│                                                     │
│ Agent 19: Internal Consistency Checker             │
│ ├─ ตรวจสอบ: ความสัมพันธ์ระหว่าง sections       │
│ ├─ ตัวอย่าง:
│    ├─ Section 4.5 (ฮาร์ดแวร์) vs 4.2 (วัตถุประสงค์)
│    ├─ Section 4.2 (วัตถุประสงค์) vs 4.7 (งาน)
│    ├─ Section 4.6 vs 4.7 vs 4.8 (scope consistency)
│    └─ Budget vs Timeline vs Scope (Golden Triangle)
│ └─ ผลลัพธ์: รายการข้อขัดแย้ง + ข้อเสนอแนะ
│                                                     │
│ Agent 20: Suggestion Engine                        │
│ ├─ เสนอแนะการปรับปรุง                             │
│ ├─ ประเภท:
│    ├─ Content suggestions (เพิ่ม/ลบ/เปลี่ยน)
│    ├─ Formatting suggestions (ย่อหน้า รูปแบบ)
│    ├─ Wording suggestions (ใช้คำให้เหมาะสม)
│    └─ Structure suggestions (จัดชั้นแนว)
│ └─ ลำดับความสำคัญ: High, Medium, Low
│                                                     │
└─────────────────────────────────────────────────────┘
```

**PHASE 4: ประกอบขั้นสุดท้าย**

```
┌─────────────────────────────────────────────────────┐
│ PHASE 4: การประกอบ (Assembly & Export)             │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ขั้นตอน:                                            │
│ 1. รวมทั้ง 10 sections → 1 TOR document            │
│ 2. สร้าง Table of Contents (สารบัญ)               │
│ 3. บ้านหมายเลข (auto-numbering)                    │
│ 4. บันทึกลงฐานข้อมูล PostgreSQL                     │
│ 5. เก็บ vectors ใน pgvector                        │
│ 6. Export → Word (DOCX) + PDF                      │
│ 7. เก็บไฟล์ใน MinIO                                │
│ 8. สร้าง download links                            │
│                                                     │
│ ผลลัพธ์:
│ ├─ TOR Document (DOCX, PDF)
│ ├─ Project Record (stored in PostgreSQL)
│ ├─ Vector embeddings (stored in pgvector)
│ ├─ Version history
│ └─ Audit log
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🧠 ตัวแทน AI ที่เชี่ยวชาญ 20 ตัว - รายละเอียดลึก

### ข้อมูลทั่วไปของแต่ละตัวแทน

```
แต่ละตัวแทน AI มีคุณสมบัติ:

┌─ ชื่อ (Name):          Agent 1, Agent 2, ...
├─ บทบาท (Role):        อะไร
├─ ผลงาน (Output):       อะไร
├─ เงื่อนไข (Trigger):   เมื่อไหร่เรียกใช้
├─ Input Data:           ตัวแปรไหนที่ต้อง
├─ Output Format:        รูปแบบผลลัพธ์
├─ Prompts:              คำสั่ง AI ที่ใช้
├─ LLM Choice:           Claude หรือ Llama
├─ Execution Time:       ใช้เวลานาน
└─ Retry Logic:          ลองใหม่กี่ครั้ง
```

### Agent 0: Data Validator (ตรวจสอบข้อมูล)

```
📋 ระเบียน:
├─ Input: raw_project_data (ข้อมูลดิบจากผู้ใช้)
├─ Output: cleaned_data (ข้อมูลที่สะอาดแล้ว)
├─ Status: validation_report
└─ Errors: error_list

💼 หน้าที่:
├─ ตรวจสอบ Field ว่างเปล่า (required fields)
├─ ตรวจสอบประเภทข้อมูล (type checking)
│  ├─ Budget: ต้อง > 0 และ < 1,000,000,000
│  ├─ Timeline: ต้อง 1-60 เดือน
│  ├─ Ministry: ต้องใน whitelist
│  └─ ProjectType: ต้องใน predefined list
├─ ลบข้อมูล invalid (เช่น Excel formula errors)
├─ ทำความสะอาดข้อมูล (trim whitespace, normalize)
└─ Return: ✅ pass หรือ ❌ fail + error message

🔧 Prompt Template:
   "ตรวจสอบข้อมูลโครงการต่อไปนี้:
   - ชื่อโครงการ: {project_name}
   - งบประมาณ: {budget} บาท
   - ระยะเวลา: {timeline} เดือน
   - กระทรวง: {ministry}
   
   ตรวจสอบความถูกต้อง ตรวจสอบค่าหายไป 
   แล้ว return JSON ผลลัพธ์"

⏱️ Timing:
├─ Execution: 2-5 วินาที
├─ Retry: ไม่ต้องลองใหม่ (deterministic)
└─ On Error: return error list เพื่อให้ผู้ใช้แก้ไข
```

### Agent 0.5: Template Selector (เลือกแม่แบบ)

```
📋 ระเบียน:
├─ Input: project_type, industry, scope_category
├─ Output: selected_template, template_metadata
└─ Confidence: 0.0-1.0

💼 หน้าที่:
├─ ค้นหา TOR templates ที่เหมาะสม
├─ ประเภทโครงการ:
│  ├─ IT Infrastructure
│  ├─ Software Development
│  ├─ Public Infrastructure
│  ├─ Consulting Services
│  ├─ Equipment & Hardware
│  └─ Hybrid/Custom
├─ ดึงแม่แบบจาก MongoDB
├─ เลือกอย่างอย่าง 1 หรือ รวมหลายอย่าง
└─ Return: template object พร้อม metadata

🔧 Template Metadata:
   {
     "template_id": "tpl_it_001",
     "name": "IT Infrastructure Project",
     "industry": "Information Technology",
     "sections_prefilled": {...},
     "required_agents": [2,3,4,5,6,7,8,9,10,11,12],
     "estimated_completion": 35,  // minutes
     "base_timeline": 12,  // months
     "complexity_score": 7  // 1-10
   }

⏱️ Timing:
├─ Query MongoDB: 1-2 วินาที
├─ Select template: 1 วินาที
└─ Total: 2-3 วินาที
```

### Agent 1: Context Analyzer (วิเคราะห์บริบท)

```
📋 ระเบียน:
├─ Input: cleaned_data, project_description, objectives
├─ Output: project_context, extracted_entities, similar_tors
└─ Context_embedding

💼 หน้าที่:
├─ วิเคราะห์สาระสำคัญของโครงการ
│  ├─ แยก: ปัญหา, เป้าหมาย, ขอบเขต
│  ├─ สกัด: Entities (คน, เครื่องมือ, สถานที่)
│  └─ เข้าใจ: ความต้องการทั่วไป
├─ ค้นหา: TOR ที่คล้ายคลึง (similarity search)
│  ├─ ใช้ Embeddings vector search
│  ├─ ได้ Top-5 TORs ที่คล้ายที่สุด
│  └─ Return: similar_tor_ids + similarity_score
├─ สร้าง Context Summary (สรุปบริบท)
└─ Return: JSON object ที่มี context info ทั้งหมด

🔧 Prompt Template:
   "อ่านคำบรรยายโครงการต่อไปนี้ แล้ว:
   1. สกัด Key entities (คน, องค์กร, เทคโนโลยี)
   2. ระบุ Main challenges (ปัญหาหลัก)
   3. ระบุ Success criteria (เกณฑ์สำเร็จ)
   4. เสนอแนะ Skill requirements (ความสามารถที่ต้อง)
   
   Description: {description}
   
   Return JSON ผลลัพธ์"

⏱️ Timing:
├─ Analyze context: 3-5 วินาที (Claude)
├─ Vector similarity search: 1-2 วินาที
└─ Total: 5-7 วินาที
```

### Agents 2-17: Section Creation Agents (สร้างส่วน)

```
🔄 Pattern สำหรับ Agents 2-17:

📋 Input:
├─ project_context (จาก Agent 1)
├─ cleaned_data (จาก Agent 0)
├─ template (จาก Agent 0.5)
├─ similar_sections (จาก RAG retrieval)
└─ tone_guidelines (ทางการ formal Thai)

📋 Output:
├─ section_content (เนื้อหา 400-900 คำ)
├─ metadata {word_count, quality_score, key_points}
├─ validation_status (✅ pass / ⚠️ needs review)
└─ suggestions (รายการข้อเสนอแนะ)

🔧 Prompt Pattern:
   "สร้าง Section {number}.{subsection} ของ TOR
   โครงการชื่อ: {project_name}
   บริบท: {project_context}
   ความต้องการจาก Template: {template_section}
   ตัวอย่างจาก TOR ที่คล้ายคลึง:
   
   {similar_sections_examples}
   
   ข้อกำหนด:
   - ใช้ภาษาไทยราชการ
   - ความยาว: 400-900 คำ
   - ครอบคลุม: {required_points}
   - ชัดเจน, เฉพาะเจาะจง, วัดได้
   
   Return JSON {content, metadata, validation}"

📊 Agent-by-Agent Details:

Agent 2 - Section 4.1 (ความเป็นมา):
├─ ระบุ: Current situation, Problems, Why needed
├─ ความยาว: 500-800 คำ
├─ Tone: Formal, analytical
└─ LLM: Claude (ต้องมี reasoning)

Agent 3 - Section 4.2 (วัตถุประสงค์):
├─ สร้าง: 5-8 Objectives (SMART goals)
├─ SMART: Specific, Measurable, Achievable, Relevant, Time-bound
├─ ความยาว: 400-600 คำ
└─ LLM: Claude

Agent 4 - Section 4.3 (คุณสมบัติ):
├─ กำหนด: Qualifications ของผู้เสนองาน
├─ ระบุ: experience, team, financial, legal status
├─ ตรวจสอบ: สอดคล้องกับ scope และ budget
├─ ความยาว: 600-900 คำ
└─ LLM: Claude

Agent 5 - Section 4.4 (ฮาร์ดแวร์):
├─ เลือก: Server, Workstation, Network equipment
├─ สร้าง: BOM (Bill of Materials)
├─ ระบุ: Specifications, Quantity, Unit cost
├─ ความยาว: 500-700 คำ + BOM table
└─ LLM: Claude หรือ Llama (data-driven)

Agent 6 - Section 4.5 (ซอฟต์แวร์):
├─ ระบุ: OS, Database, Libraries, Tools
├─ ตรวจสอบ: License type (GPL, Commercial, Open)
├─ ระบุ: Version requirements, compatibility
├─ ความยาว: 600-800 คำ
└─ LLM: Claude (legal awareness needed)

Agent 7 - Section 4.6 (งาน/Work Breakdown):
├─ สร้าง: Work breakdown structure (WBS)
├─ จำนวน: 50-100 work items
├─ ระบุ: Description, Duration, Dependencies
├─ Output: Gantt chart JSON + Description
├─ ความยาว: 800-1000 คำ + structured data
└─ LLM: Claude (complex planning)

Agent 8 - Section 4.7 (ผลิตภัณฑ์/Deliverables):
├─ สร้าง: Deliverables list (20-30 items)
├─ ระบุ: Name, Format, Delivery date, Content
├─ ตัวอย่าง: Design document, Code, Training, etc
├─ ความยาว: 700-900 คำ
└─ LLM: Claude

Agent 9 - Section 4.8 (การสนับสนุน):
├─ ระบุ: Warranty period (1-3 ปี)
├─ SLA: Response time (4-24 hours)
├─ Support levels: Critical, High, Medium, Low
├─ Availability: 24/7 หรือ Business hours
├─ ความยาว: 400-600 คำ
└─ LLM: Llama (template-based)

Agent 10 - Section 4.9 (บุคลากร):
├─ ระบุ: Required roles (PM, TL, Dev, QA, Support)
├─ ระบุ: Experience level, Number of people
├─ คำนวณ: Headcount และ Person-months
├─ ความยาว: 500-700 คำ
└─ LLM: Llama (data-driven)

Agent 11 - Section 4.10 (บำรุงรักษา):
├─ ระบุ: Maintenance period (1-3 ปี)
├─ ประเภท: Preventive, Corrective, Adaptive
├─ Scope: Bug fixes, Security patches, Updates
├─ SLA: Bug fix response time
├─ ความยาว: 400-600 คำ
└─ LLM: Llama

Agent 12 - Section 4.11-4.14 (Operations/DR/Security):
├─ Section 4.11: Operations procedures
├─ Section 4.12: Disaster Recovery plan
├─ Section 4.13: Security requirements
├─ Section 4.14: Performance & SLA
├─ ความยาว: 900-1200 คำ รวม
└─ LLM: Claude (complex and critical)

Agent 13 - Section 5 (ระยะเวลา/Timeline):
├─ สร้าง: 52-week project schedule
├─ ระบุ: Milestones: Month 3, 6, 9, 12
├─ Phases: Planning, Development, Testing, Deployment
├─ Output: Gantt chart + Narrative description
├─ ความยาว: 500-700 คำ
└─ LLM: Claude (need logical sequencing)

Agent 14 - Section 6 (การประเมิน/Evaluation):
├─ สร้าง: Evaluation criteria
├─ ประเมิน: Functionality, Performance, Quality
├─ Scoring: 0-100 points
├─ Pass/Fail thresholds (≥60 = pass)
├─ ความยาว: 500-700 คำ
└─ LLM: Claude

Agent 15 - Section 7 (งบประมาณ/Budget):
├─ คำนวณ: ต้นทุนรวม
│  ├─ Hardware cost
│  ├─ Software licenses
│  ├─ Labor (person-months × daily rate)
│  ├─ Maintenance
│  ├─ Training
│  └─ Contingency (10-15%)
├─ ตรวจสอบ: Paid-up capital ≥ Budget / 4
├─ ความยาว: 600-800 คำ + cost breakdown table
└─ LLM: Claude (need calculation)

Agent 16 - Section 8 (การจ่ายเงิน/Payment):
├─ สร้าง: Payment schedule
├─ Milestones: Month 3 (30%), Month 6 (20%), Month 9 (30%), Month 12 (20%)
├─ เงื่อนไข: Payment upon acceptance + delivery
├─ ความยาว: 400-600 คำ
└─ LLM: Llama (standard template)

Agent 17 - Section 9-10 (Penalties/Documents):
├─ Section 9: Late penalties (0.5-1% per month)
├─ Section 10: Required documents list
├─ ความยาว: 500-700 คำ
└─ LLM: Llama (standard legal terms)

⏱️ Timing per agent:
├─ Claude agents (2,3,4,6,7,8,12,13,14,15): 5-15 วินาที
├─ Llama agents (5,9,10,11,16,17): 1-3 วินาที
└─ Total Phase 2: ~60-90 วินาที
```

---

## 📦 การเก็บรักษาข้อมูลและระบบค้นหา (Data Storage & RAG)

### Architecture ของระบบค้นหา (RAG)

```
┌─────────────────────────────────────────────────────────┐
│ Retrieval-Augmented Generation (RAG) System             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ ✅ Vector Database (pgvector)                           │
│    ├─ ประกอบด้วย: 800-1000 vectors (embeddings)        │
│    ├─ ที่มา: ตัวอย่าง TOR ที่เก็บจากสังคม             │
│    ├─ Embedding model: OpenAI text-embedding-3-small   │
│    ├─ Vector dimension: 1536 dimension                 │
│    ├─ Use: Similarity search (ค้นหา TOR ที่คล้ายคลึง) │
│    │                                                    │
│    └─ ตัวอย่างการค้นหา:
│       Query: "โครงการ IT infrastructure 100 ล้าน"
│       ↓
│       1. สร้าง embedding จาก query
│       2. ค้นหา K-Nearest vectors (K=5)
│       3. Return Top-5 similar TORs
│       4. ใช้เป็น context สำหรับ Agent
│
│ ✅ Document Database (MongoDB)                          │
│    ├─ ประกอบด้วย: Full TOR documents                   │
│    ├─ Collections:
│    │  ├─ tor_templates (แม่แบบ TOR)
│    │  ├─ tor_generated (TOR ที่สร้างแล้ว)
│    │  ├─ vector_store_docs (เอกสารอ้างอิง)
│    │  └─ audit_logs (บันทึกการใช้งาน)
│    │
│    ├─ Indexes:
│    │  ├─ Full-text search (section, content)
│    │  ├─ Compound indexes (type + industry)
│    │  └─ TTL indexes (ลบเอกสารเก่า)
│    │
│    └─ ตัวอย่างการค้นหา:
│       Query: "SLA requirement"
│       ↓
│       1. Full-text search ใน MongoDB
│       2. หา sections ที่มีคำว่า SLA
│       3. Return matching documents + locations
│
│ ✅ Caching Layer (Redis)                                │
│    ├─ เก็บ: Frequently accessed vectors
│    ├─ Expiry: 1-24 ชั่วโมง (configurable)
│    ├─ Key pattern:
│    │  ├─ vector:similarity:{query_hash}
│    │  ├─ doc:project:{project_id}
│    │  └─ template:id:{template_id}
│    └─ Hit ratio: 60-70% (expected)
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Database Schema (โครงสร้างฐานข้อมูล)

**PostgreSQL 16 (Relational Data):**

```
TABLE users
├─ id (UUID PK)
├─ email (VARCHAR unique)
├─ name (VARCHAR)
├─ ministry (VARCHAR)
├─ role (ENUM: user, admin, approver)
├─ created_at (TIMESTAMP)
└─ updated_at (TIMESTAMP)

TABLE projects
├─ id (UUID PK)
├─ user_id (FK → users)
├─ name (VARCHAR)
├─ ministry (VARCHAR)
├─ budget (DECIMAL)
├─ timeline_months (INTEGER)
├─ project_type (VARCHAR)
├─ status (ENUM: draft, generating, completed, archived)
├─ created_at (TIMESTAMP)
└─ updated_at (TIMESTAMP)

TABLE tor_documents
├─ id (UUID PK)
├─ project_id (FK → projects)
├─ content (TEXT)  // เนื้อหา TOR สมบูรณ์
├─ version (INTEGER)
├─ status (ENUM: draft, review, approved, published)
├─ created_at (TIMESTAMP)
├─ approved_by (UUID FK → users)
├─ approved_at (TIMESTAMP)
└─ file_paths (JSON)  // {docx_path, pdf_path, ...}

TABLE embeddings
├─ id (UUID PK)
├─ tor_id (FK → tor_documents)
├─ section_number (VARCHAR)  // "4.1", "4.2", etc
├─ section_title (VARCHAR)
├─ vector (vector(1536))  // pgvector column
├─ created_at (TIMESTAMP)
└─ indexed_at (TIMESTAMP)

TABLE audit_logs
├─ id (UUID PK)
├─ user_id (FK → users)
├─ action (VARCHAR)  // "created", "updated", "exported"
├─ resource_type (VARCHAR)  // "tor_document", "project"
├─ resource_id (UUID)
├─ changes (JSONB)  // ก่อนและหลัง
├─ timestamp (TIMESTAMP)
└─ ip_address (VARCHAR)
```

**MongoDB 7 (Document Data):**

```
Collection: tor_templates
└─ Document:
   {
     _id: ObjectId,
     name: "IT Infrastructure Project",
     type: "IT",
     industry: "Information Technology",
     sections: {
       4.1: { placeholder: "...", example: "..." },
       4.2: { placeholder: "...", example: "..." },
       ...
     },
     metadata: {
       complexity: 7,
       estimated_time: 40,  // นาที
       required_agents: [...]
     },
     created_at: ISODate,
     updated_at: ISODate
   }

Collection: tor_generated
└─ Document:
   {
     _id: ObjectId,
     project_id: UUID,
     tor_document_id: UUID,
     full_content: "...",  // TOR สมบูรณ์
     metadata: {
       generation_time: 45,  // วินาที
       agents_used: [0, 1, 2, 3, ...],
       quality_score: 92,
       compliance_score: 100
     },
     sections: {
       4.1: { content: "...", agent_id: 2 },
       4.2: { content: "...", agent_id: 3 },
       ...
     },
     created_at: ISODate,
     modified_count: 5,
     last_modified_by: UUID
   }

Collection: vector_store_docs
└─ Document:
   {
     _id: ObjectId,
     tor_id: UUID,
     section: "4.1",
     text: "...",  // full section text
     vector: [0.1234, -0.5678, ...],  // 1536 dims
     metadata: {
       project_type: "IT",
       industry: "Technology",
       complexity: 7
     },
     created_at: ISODate
   }

Collection: audit_logs
└─ Document:
   {
     _id: ObjectId,
     timestamp: ISODate,
     user_id: UUID,
     action: "tor_generated",
     details: {
       project_id: UUID,
       tor_id: UUID,
       agents_executed: [...],
       total_time: 75  // วินาที
     }
   }
```

**Redis (Caching):**

```
Key patterns:

1. Vector search cache:
   KEY: vector:similarity:{hash(query)}:{k}
   VALUE: [
     {vector_id, similarity_score, tor_id},
     ...
   ]
   TTL: 4 hours

2. Template cache:
   KEY: template:id:{template_id}
   VALUE: {full template object}
   TTL: 24 hours

3. Project cache:
   KEY: project:{project_id}
   VALUE: {project object with metadata}
   TTL: 1 hour

4. Session cache:
   KEY: session:{user_id}:{session_id}
   VALUE: {user info, auth token, permissions}
   TTL: 8 hours

5. Rate limiting:
   KEY: ratelimit:{user_id}:{endpoint}
   VALUE: {request_count}
   TTL: 1 minute

6. TOR generation progress:
   KEY: progress:{project_id}
   VALUE: {phase, agent_id, status, progress_percent}
   TTL: 2 hours
```

---

## 🚀 วิธีการปรับใช้ระบบ (Deployment)

### การปรับใช้ในท้องถิ่น (Local Deployment)

**ข้อมูลขั้นพื้นฐาน:**
```
ประเทศไทยต้องการ:
✅ ความเป็นส่วนตัว (Privacy): ไม่ส่งข้อมูล TOR ออกไป
✅ ความเป็นอิสระ (Independence): ไม่ขึ้นอยู่ API ภายนอก
✅ ตัดสินใจได้ (Control): ควบคุมระบบเอง
✅ ต้นทุนต่ำ (Cost-effective): ไม่ต้องจ่ายสมาชิกแต่ละเดือน

ดังนั้น LOCAL FIRST ✅
```

**Local Stack (Docker Compose):**

```yaml
version: '3.9'

services:
  # Frontend
  frontend:
    image: tor-generator-frontend:latest
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NEXT_PUBLIC_ENV: development
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
    command: npm run dev

  # Backend API
  backend:
    image: tor-generator-backend:latest
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/tor_db
      MONGODB_URL: mongodb://mongo:27017/tor_db
      REDIS_URL: redis://redis:6379
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - postgres
      - mongo
      - redis
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --reload

  # PostgreSQL
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: tor_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

  # MongoDB
  mongo:
    image: mongo:7.0
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: user
      MONGO_INITDB_ROOT_PASSWORD: password
      MONGO_INITDB_DATABASE: tor_db
    volumes:
      - mongo_data:/data/db

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  # MinIO (Object Storage)
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  mongo_data:
  redis_data:
  minio_data:
```

**เริ่มต้น Local:**

```bash
# 1. Clone repository
git clone https://github.com/org/tor-generator.git
cd tor-generator

# 2. สร้างไฟล์ .env
cp .env.example .env
# แก้ไข API keys ใน .env

# 3. รัน Docker Compose
docker-compose up -d

# 4. ตรวจสอบการทำงาน
docker-compose ps
curl http://localhost:8000/docs  # ดู API docs
curl http://localhost:3000       # ดู frontend

# 5. สร้างระบบ (initialize)
docker-compose exec backend python -m alembic upgrade head
docker-compose exec backend python -m app.seed_db  # load templates
```

### การปรับใช้บนคลาวด์ (Cloud Deployment)

**Option: AWS Architecture:**

```
┌──────────────────────────────────────────────────┐
│ AWS Cloud Deployment                             │
├──────────────────────────────────────────────────┤
│                                                  │
│ 🌐 Frontend (CloudFront + S3)                    │
│    ├─ S3 bucket: tor-generator-frontend          │
│    ├─ CloudFront CDN (global cache)              │
│    └─ Cost: ~$5-10/month                         │
│                                                  │
│ 🔵 Backend (ECS + Fargate)                       │
│    ├─ Docker image: ECR registry                 │
│    ├─ ECS Fargate: serverless containers         │
│    ├─ ALB: Load balancer                         │
│    ├─ Auto-scaling: 1-10 containers              │
│    └─ Cost: ~$100-200/month                      │
│                                                  │
│ 📊 Databases (RDS + DocumentDB)                  │
│    ├─ RDS PostgreSQL: Multi-AZ                   │
│    ├─ AWS DocumentDB (MongoDB-compatible)        │
│    ├─ ElastiCache Redis: T3 instance             │
│    └─ Cost: ~$150-300/month                      │
│                                                  │
│ 💾 Storage (S3 + EBS)                            │
│    ├─ S3 buckets: TOR documents, vectors         │
│    ├─ Lifecycle: Move old to Glacier             │
│    └─ Cost: ~$10-20/month                        │
│                                                  │
│ 🔐 Security (IAM + VPC + KMS)                    │
│    ├─ VPC with private subnets                   │
│    ├─ Security groups (port 443 only)            │
│    ├─ KMS encryption at rest                     │
│    ├─ IAM roles for services                     │
│    └─ No additional cost                         │
│                                                  │
│ 📈 Monitoring (CloudWatch)                       │
│    ├─ Logs: CloudWatch Logs                      │
│    ├─ Metrics: CPU, Memory, Network              │
│    ├─ Alarms: Auto-scaling triggers              │
│    └─ Cost: ~$20-30/month                        │
│                                                  │
│ 🔄 CI/CD (CodePipeline)                          │
│    ├─ GitHub → CodePipeline                      │
│    ├─ CodeBuild: Test + Build                    │
│    ├─ CodeDeploy: Deploy to ECS                  │
│    └─ Cost: ~$50/month                           │
│                                                  │
│ 💰 TOTAL AWS COST: ~$350-600/month               │
│    (for ~100-1000 TOR generations/month)         │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Terraform Configuration (Infrastructure as Code):**

```hcl
# ตัวอย่าง minimal Terraform
provider "aws" {
  region = "ap-southeast-1"  # Singapore
}

# VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true
}

# RDS PostgreSQL
resource "aws_rds_cluster" "postgres" {
  cluster_identifier = "tor-postgres"
  engine = "aurora-postgresql"
  engine_version = "15.2"
  database_name = "tor_db"
  
  serverlessv2_scaling_configuration {
    max_capacity = 2.0
    min_capacity = 0.5
  }
}

# DocumentDB (MongoDB-compatible)
resource "aws_docdb_cluster" "mongodb" {
  cluster_identifier = "tor-mongo"
  engine = "docdb"
  master_username = "admin"
  master_password = var.mongo_password
  backup_retention_period = 7
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "tor-cluster"
}

# Fargate Service
resource "aws_ecs_service" "backend" {
  name = "tor-backend"
  cluster = aws_ecs_cluster.main.id
  launch_type = "FARGATE"
  desired_count = 2
  
  network_configuration {
    subnets = aws_subnet.private[*].id
    security_groups = [aws_security_group.backend.id]
  }
}

# ... ไฟล์ Terraform ยาวกว่านี้มาก ...
```

### ข้อเปรียบเทียบ: Local vs Cloud

```
┌─────────────────┬──────────────────┬──────────────────┐
│ ลักษณะ          │ Local (Docker)   │ Cloud (AWS)      │
├─────────────────┼──────────────────┼──────────────────┤
│ ต้นทุนเริ่มต้น   │ 0 บาท            │ ~$200/month      │
│ ความเป็นส่วนตัว │ ✅ 100%          │ ⚠️ 50% (AWS know)│
│ ความเร็ว        │ ⚡ เร็ว local    │ 🌍 เร็วทั่วโลก   │
│ ความเสถียร      │ ⚠️ ถ้ากำลังหมด  │ ✅ 99.99% SLA    │
│ Scalability     │ ⚠️ ลำดับ          │ ✅ Automatic     │
│ Maintenance     │ 👤 ต้องดูแลเอง   │ 🤖 AWS ดูแล      │
│ ใช้สำหรับ       │ Development      │ Production       │
│                 │ Small scale      │ Large scale      │
│                 │ Testing          │ Real users       │
└─────────────────┴──────────────────┴──────────────────┘

💡 สุดท้าย:
   ✅ LOCAL สำหรับ Dev/Testing
   ✅ CLOUD สำหรับ Production
   ✅ HYBRID: Local first, Cloud backup
```

---

## 📚 สรุปสถาปัตยกรรมทั้งระบบ

```
TOR Generator System - Complete Architecture:

┌────────────────────────────────────────────────────────────┐
│                    LAYER 1: Frontend                        │
│            Next.js 14 + React 18 + TypeScript              │
│  • 8-step wizard UI  • Live preview  • Responsive design   │
└────────────────────────────────────────────────────────────┘
                        ⬇️ REST API
┌────────────────────────────────────────────────────────────┐
│                 LAYER 2: API Gateway                        │
│        FastAPI + Python 3.11 (Async/Await)                │
│   • Request validation  • Authentication  • Rate limiting  │
└────────────────────────────────────────────────────────────┘
                    ⬇️ Message Queue / Direct
┌────────────────────────────────────────────────────────────┐
│              LAYER 3: Agent Orchestration                   │
│         Langchain + Langraph (Graph-based)                │
│   • 20 specialized agents  • State management              │
│   • Phase 1: Prepare (parallel)                           │
│   • Phase 2: Generate (sequential)                        │
│   • Phase 3: QA (parallel)                                │
│   • Phase 4: Assembly                                     │
└────────────────────────────────────────────────────────────┘
                    ⬇️ API Calls / Vector ops
┌────────────────────────────────────────────────────────────┐
│              LAYER 4: LLM Intelligence                      │
│         Claude 3.5 (Primary) + Llama 3 (Local)            │
│   • Hybrid strategy: 70% local, 30% cloud                 │
│   • Cost: ~$0.30-0.50 per TOR                             │
│   • Thai language: Perfect understanding                   │
└────────────────────────────────────────────────────────────┘
                    ⬇️ Vector / SQL queries
┌────────────────────────────────────────────────────────────┐
│            LAYER 5: Knowledge & Retrieval                   │
│      pgvector (800-1000 vectors) + MongoDB (Docs)         │
│   • Similarity search  • Full-text search  • RAG support   │
│   • Cached in Redis: 60-70% hit rate                       │
└────────────────────────────────────────────────────────────┘
                        ⬇️ I/O
┌────────────────────────────────────────────────────────────┐
│            LAYER 6: Data Persistence                        │
│   PostgreSQL 16  │  MongoDB 7  │  Redis 7  │  MinIO       │
│   • Relational  │ • Documents │ • Cache  │ • File store  │
│   • Audit logs  │ • Templates │ • Session│ • Export      │
└────────────────────────────────────────────────────────────┘

⏱️ PERFORMANCE METRICS:
   • Total generation time: 30-45 นาที (target)
   • Agents execution: ~60-90 วินาที
   • Export (Word/PDF): 5-10 วินาที
   • Quality score: 95%+ first-time
   • Legal compliance: 100%
   
💰 COST ANALYSIS:
   • Hardware (local): 0 บาท (use existing infrastructure)
   • Software licenses: 0 บาท (open-source stack)
   • Claude API: ~$0.15-0.25 per TOR (for primary LLM)
   • For 100 TORs/day: ~$15-25 USD/day (~500-800 บาท)
   • Cost per TOR: ~$0.50 (vs ~3,000 บาท manual labor)
   
✅ LOCAL FIRST PHILOSOPHY:
   ✓ All data stays in Thailand
   ✓ Independent from external APIs
   ✓ Can operate offline (partial)
   ✓ Full control and auditability
   ✓ Compliant with Thai government requirements
```

---

**ส่วนถัดไป: Part 04 จะเป็นรายละเอียดเก็บที่ระเอียดของเพิ่มเติมอีกครั้งว่า:
- API Endpoints Reference
- Database Schema Full Details
- Installation & Setup Guide
- Development Workflow
- Testing Strategy
- Troubleshooting Guide**
