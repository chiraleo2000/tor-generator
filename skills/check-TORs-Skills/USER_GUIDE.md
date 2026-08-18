# คู่มือการใช้งาน TOR Skills
# User Guide: TOR Review/Draft/Intake Skills

**เวอร์ชัน:** 1.0  
**วันที่:** มกราคม 2568 (January 2025)  
**ผู้จัดทำ:** AI-Assisted Documentation

---

## สารบัญ (Table of Contents)

1. [ภาพรวม (Overview)](#1-ภาพรวม)
2. [แพลตฟอร์มที่รองรับ (Platform Support)](#2-แพลตฟอร์มที่รองรับ)
3. [ข้อมูลที่ต้องเตรียม (Input Requirements)](#3-ข้อมูลที่ต้องเตรียม)
4. [ขอบเขตความรู้ (Topics Covered)](#4-ขอบเขตความรู้)
5. [ตัวอย่างการใช้งาน (Example Prompts)](#5-ตัวอย่างการใช้งาน)
6. [โครงสร้างไฟล์ (File Structure)](#6-โครงสร้างไฟล์)
7. [การปรับแต่ง (Customization)](#7-การปรับแต่ง)
8. [บันทึกการเปลี่ยนแปลง (Changelog)](#8-บันทึกการเปลี่ยนแปลง)

---

## 1. ภาพรวม

### TOR Skills คืออะไร?

ชุดเครื่องมือ AI สำหรับช่วยจัดทำและตรวจสอบ TOR (Terms of Reference) จัดซื้อจัดจ้างภาครัฐไทย
ตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560

### 3-Skill Workflow (กระบวนการ 3 ขั้นตอน)

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  TOR Intake  │ →  │  TOR Draft   │ →  │  TOR Review  │
│  เก็บข้อมูล    │    │  ร่าง TOR     │    │  ตรวจสอบ     │
└──────────────┘    └──────────────┘    └──────────────┘
```

| Skill | หน้าที่ | Input | Output |
|-------|---------|-------|--------|
| **TOR Intake** | เก็บ requirement จากผู้ใช้ | Free-form ภาษาไทย | Structured JSON |
| **TOR Draft** | ร่าง TOR ฉบับสมบูรณ์ | Structured data จาก Intake | TOR (.md/.docx) |
| **TOR Review** | ตรวจสอบ TOR ที่ร่างแล้ว | ไฟล์ TOR (.docx/.pdf/text) | รายงานตรวจสอบ |

### ใช้ได้กับงานประเภทใด?
- จัดซื้อสินค้า (Goods)
- จ้างบริการ / จ้างทำของ (Services)
- งานก่อสร้าง (Construction)
- จ้างที่ปรึกษา (Consulting)
- จ้างออกแบบ/ควบคุมงาน (Design/Supervision)
- งาน IT (Software, Hardware, Maintenance, Cloud)

---

## 2. แพลตฟอร์มที่รองรับ

### 2.1 Kiro IDE

**วิธีตั้งค่า:**
1. ไฟล์ skill อยู่ที่ `.kiro/skills/` ในโปรเจค
2. Kiro จะ activate skill อัตโนมัติเมื่อเปิดโปรเจค
3. ใช้ `#File` เพื่อแนบไฟล์ TOR ที่ต้องการตรวจ

**ไฟล์ที่ต้องมี:**
```
.kiro/
└── skills/
    ├── tor-intake.md
    ├── tor-draft.md
    └── tor-review.md
```

**วิธีใช้:**
- พิมพ์คำสั่งในแชท เช่น "ตรวจสอบ TOR นี้" หรือ "ช่วยร่าง TOR โครงการ..."
- แนบไฟล์ด้วย `#File` tag
- Skills จะทำงานตาม context โดยอัตโนมัติ

### 2.2 Claude (Projects / Artifacts)

**วิธีตั้งค่า:**
1. สร้าง Project ใหม่ใน Claude
2. Upload ไฟล์เหล่านี้เป็น Project Knowledge:
   - `SKILL.md` (จาก `check-TORs-Skills/claude/tor-review/`)
   - ไฟล์ใน `references/` ทั้งหมด (tor_reference_complete.md, kb_*.md, *.json)
3. ตั้ง System Instructions ตาม SKILL.md

**วิธีใช้:**
- Upload ไฟล์ TOR ที่ต้องการตรวจ → ถาม "ตรวจสอบ TOR นี้"
- พิมพ์ requirement → ถาม "ช่วยร่าง TOR"
- Claude จะใช้ knowledge files เป็นฐานอ้างอิง

### 2.3 ChatGPT (Custom GPTs)

**วิธีตั้งค่า:**
1. สร้าง Custom GPT ใหม่
2. Upload `gpt-config.json` เป็น instructions
3. Upload ไฟล์ใน `knowledge/` ทั้งหมด:
   - `tor_reference_complete.md`
   - `kb_contract_penalty.md`
   - `kb_evaluation_criteria.md`
   - `kb_guarantee.md`
   - `kb_procurement_methods.md`
   - `kb_qualifications.md`
   - `kb_timeline_process.md`
   - `kb_real_tor_patterns.md`
   - `document_checklist.json`
   - `method_selection.json`
   - `template_selection.json`

**วิธีใช้:**
- Upload ไฟล์ TOR หรือ paste ข้อความ
- GPT จะตรวจสอบตาม checklist อัตโนมัติ
- สามารถถามคำถามเฉพาะเจาะจงได้

---

## 3. ข้อมูลที่ต้องเตรียม

### 3.1 สำหรับ TOR Review (ตรวจสอบ TOR)

**Input หลัก (บังคับ):**
- ร่าง TOR ที่ต้องการตรวจ (.docx, .pdf, หรือ paste text)

**Input เสริม (แนะนำ):**
- ชื่อโครงการ
- หน่วยงานผู้จัดซื้อ
- วงเงินงบประมาณ
- ประเภทพัสดุ (สินค้า/บริการ/ก่อสร้าง/ที่ปรึกษา/ออกแบบ)
- วิธีจัดซื้อจัดจ้าง (e-bidding/คัดเลือก/เฉพาะเจาะจง)

### 3.2 สำหรับ TOR Draft (ร่าง TOR)

**ข้อมูลบังคับ:**
- ชื่อโครงการ
- หน่วยงานผู้จัดซื้อ
- ประเภทพัสดุ
- วงเงินงบประมาณโดยประมาณ
- ขอบเขตงานคร่าวๆ
- ระยะเวลาที่ต้องการ

**ข้อมูลเพิ่มเติมตามประเภทงาน:**

| ประเภท | ข้อมูลเพิ่มเติม |
|--------|----------------|
| IT/Software | SLA, จำนวนผู้ใช้, ระบบที่ต้อง integrate |
| IT MA | รายการอุปกรณ์, Response/Resolution time |
| ก่อสร้าง | พื้นที่, มีแบบรูป/BOQ หรือไม่ |
| ที่ปรึกษา | สาขาเชี่ยวชาญ, บุคลากร, Deliverables |
| Data Center | อุปกรณ์หลัก, ระบบย่อย |

### 3.3 สำหรับ TOR Intake (เก็บข้อมูล)

**Input:** Free-form ภาษาไทย — บอกสิ่งที่ต้องการจัดซื้อจัดจ้าง
- ระบบจะถามคำถามเพิ่มเติมจนครบ
- ไม่จำเป็นต้องรู้ศัพท์เทคนิค

**ตัวอย่าง Input:**
> "อยากจ้างบริษัททำเว็บไซต์ให้หน่วยงาน งบประมาณ 3 ล้าน ต้องเชื่อมกับระบบเดิม"

---

## 4. ขอบเขตความรู้

### 4.1 กฎหมายที่ครอบคลุม (Legal Framework)
- **พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560** — กรอบหลัก
- **ระเบียบกระทรวงการคลังฯ พ.ศ. 2560** — ขั้นตอนละเอียด
- **กฎกระทรวง** — วงเงิน, วิธีการ, ค่าจ้างออกแบบ, ที่ปรึกษา
- **หนังสือเวียน** — ว.119, ว.56, ว.159, ว.322, ว.336, ว.356 ฯลฯ
- **ประกาศคณะกรรมการนโยบายฯ** — มาตรฐาน, แนวปฏิบัติ

### 4.2 ประเภทการจัดซื้อจัดจ้าง (6 ประเภท + ประเภทย่อย)
1. **สินค้า** — วัสดุ, ครุภัณฑ์, IT Hardware
2. **งานบริการ** — MA, Outsource, จ้างเหมา, IT Service
3. **งานก่อสร้าง** — อาคาร, ถนน, สาธารณูปโภค, ปรับปรุง
4. **จ้างที่ปรึกษา** — วิศวกรรม, IT Strategy, กฎหมาย
5. **จ้างออกแบบ/ควบคุมงาน** — สถาปัตยกรรม, วิศวกรรม
6. **อื่นๆ** — ตามกฎกระทรวงกำหนด

### 4.3 วิธีจัดซื้อจัดจ้าง (3 วิธี + วิธีย่อย)
1. **ประกาศเชิญชวนทั่วไป** — e-market, e-bidding, สอบราคา
2. **คัดเลือก** — เชิญ ≥3 ราย ตามเงื่อนไข ม.56(1)
3. **เฉพาะเจาะจง** — 1 ราย / วงเงิน ≤500,000

### 4.4 การตรวจสอบที่ดำเนินการ

**A. ความครบถ้วน (13 หัวข้อ):**
- ความเป็นมา, วัตถุประสงค์, คุณสมบัติ, ขอบเขต, ระยะเวลา
- วงเงิน, สถานที่, งวดงาน, รับประกัน, ค่าปรับ
- เกณฑ์พิจารณา, เอกสาร, เงื่อนไขอื่น

**B. ความถูกต้องตามกฎหมาย (10 ข้อ):**
- คุณสมบัติครบ 9 ข้อ, ไม่ล็อกสเปค, ไม่เกินจำเป็น
- วิธีจัดซื้อสอดคล้องวงเงิน, ค่าปรับ 0.01-0.20%
- หลักประกัน 5%, ไม่แบ่งซื้อ, ผลงานสมเหตุสมผล

**C. ความสอดคล้อง (6 ข้อ):**
- วงเงิน↔ขอบเขต, ระยะเวลา↔ขอบเขต
- งวดงานรวม=100%, เกณฑ์↔คุณสมบัติ

**D. ข้อกำหนดเฉพาะประเภท:**
- IT: SLA, Data ownership, Licensing, Training
- ก่อสร้าง: แบบรูป, BOQ, วิชาชีพ, ความปลอดภัย
- ที่ปรึกษา: Man-month, เกณฑ์คุณภาพ ≥80%
- MA: PM/CM, Certification, Statement of Compliance

**E. ภาษาและรูปแบบ (5 ข้อ)**

### 4.5 เกณฑ์พิจารณา (Evaluation Criteria)
- **ราคาต่ำสุด** — งาน MA ที่ spec ชัดเจน
- **Price Performance** — งาน IT ซับซ้อน (เทคนิค:ราคา)
- **QCBS** — ที่ปรึกษา (คุณภาพ ≥80%)

---

## 5. ตัวอย่างการใช้งาน

### 5.1 ตรวจสอบ TOR (TOR Review)

**Kiro IDE:**
```
ตรวจสอบ TOR นี้ #File[TOR_โครงการระบบ.docx]
โครงการจ้างพัฒนาระบบ IT วงเงิน 15 ล้านบาท วิธี e-bidding
```

**Claude:**
```
ช่วยตรวจสอบ TOR ที่แนบมานี้ ว่าครบถ้วนถูกต้องตามกฎหมายหรือไม่
- โครงการ: จ้างบำรุงรักษาระบบ Data Center
- วงเงิน: 5 ล้านบาท
- วิธี: ประกวดราคาอิเล็กทรอนิกส์ (e-bidding)
[paste TOR text หรือ upload ไฟล์]
```

**ChatGPT:**
```
ตรวจ TOR โครงการจ้างพัฒนาเว็บไซต์ของหน่วยงาน X
วงเงิน 3 ล้านบาท วิธี e-bidding
[paste TOR text]
```

### 5.2 ร่าง TOR (TOR Draft)

**Kiro IDE:**
```
ช่วยร่าง TOR โครงการจ้างบำรุงรักษาระบบเครือข่าย
- หน่วยงาน: กรมการปกครอง
- วงเงิน: 8 ล้านบาท
- ระยะเวลา: 1 ปี (365 วัน)
- ขอบเขต: ดูแล Server 20 เครื่อง, Network Switch 50 ตัว, Firewall 4 ตัว
- SLA: Response 2 ชม., Resolution 8 ชม.
```

**Claude:**
```
ร่าง TOR จ้างที่ปรึกษาศึกษาความเป็นไปได้โครงการ Smart City
- หน่วยงาน: เทศบาลนคร X
- วงเงิน: 20 ล้านบาท
- ระยะเวลา: 12 เดือน
- ต้องการ: ศึกษาความเป็นไปได้ + ออกแบบระบบ + Pilot
```

### 5.3 เก็บข้อมูล (TOR Intake)

**ทุกแพลตฟอร์ม:**
```
อยากจะจ้างบริษัทมาทำระบบจัดการเอกสารให้สำนักงาน
ตอนนี้ใช้กระดาษหมดเลย อยากให้เป็นอิเล็กทรอนิกส์
งบประมาณประมาณ 5 ล้าน ใช้เวลาไม่เกิน 6 เดือน
```

*ระบบจะถามเพิ่ม:*
- จำนวนผู้ใช้กี่คน?
- ต้องเชื่อมกับระบบอะไรบ้าง?
- ต้องการ Cloud หรือ On-premise?

---

## 6. โครงสร้างไฟล์

```
check-TORs-Skills/
├── USER_GUIDE.md                          ← คู่มือนี้
├── tor_structure_analysis.md              ← วิเคราะห์โครงสร้าง TOR จริง
│
├── chatgpt/
│   └── tor-review/
│       ├── gpt-config.json                ← Config สำหรับ Custom GPT
│       ├── instructions.md                ← Instructions GPT
│       ├── SKILL.md                       ← Skill definition
│       └── knowledge/                     ← Knowledge files
│           ├── document_checklist.json
│           ├── kb_contract_penalty.md
│           ├── kb_evaluation_criteria.md
│           ├── kb_guarantee.md
│           ├── kb_procurement_methods.md
│           ├── kb_qualifications.md
│           ├── kb_real_tor_patterns.md    ← NEW: ข้อมูลจาก TOR จริง
│           ├── kb_timeline_process.md
│           ├── method_selection.json
│           ├── template_selection.json
│           └── tor_reference_complete.md
│
├── claude/
│   └── tor-review/
│       ├── SKILL.md                       ← Skill definition for Claude
│       ├── assets/                        ← Assets (if any)
│       └── references/                    ← Reference files
│           ├── document_checklist.json
│           ├── kb_contract_penalty.md
│           ├── kb_evaluation_criteria.md
│           ├── kb_guarantee.md
│           ├── kb_procurement_methods.md
│           ├── kb_qualifications.md
│           ├── kb_timeline_process.md
│           ├── method_selection.json
│           ├── template_selection.json
│           └── tor_reference_complete.md  ← + Section 12: Real-World Patterns
│
└── (kiro skills อยู่ที่ .kiro/skills/)
    ├── tor-intake.md
    ├── tor-draft.md
    └── tor-review.md                      ← + Real-World TOR Patterns section
```

---

## 7. การปรับแต่ง

### 7.1 เพิ่มระเบียบเฉพาะหน่วยงาน

หากหน่วยงานมีระเบียบภายในเพิ่มเติม สามารถเพิ่มได้ดังนี้:

**Kiro:** เพิ่มใน `.kiro/skills/tor-review.md` section ใหม่
```markdown
### Agency-Specific Rules: [ชื่อหน่วยงาน]
- กฎเกณฑ์เฉพาะ 1
- กฎเกณฑ์เฉพาะ 2
```

**Claude:** เพิ่มเป็น Project Knowledge file ใหม่
- สร้างไฟล์ `kb_agency_rules.md` upload เข้า Project

**ChatGPT:** upload เป็น Knowledge file เพิ่มเติมใน GPT configuration

### 7.2 เพิ่มเกณฑ์ตรวจสอบเฉพาะ

เพิ่ม check items ใน Checklist section ของ skill files:
```markdown
### F. ข้อกำหนดเฉพาะหน่วยงาน [ชื่อ]
- [ ] ข้อกำหนดที่ 1
- [ ] ข้อกำหนดที่ 2
```

### 7.3 เพิ่ม Template ใหม่

หากมี template TOR เฉพาะ:
1. จัดทำ template เป็น Markdown
2. เพิ่มใน `template_selection.json`
3. อ้างอิงใน tor-draft skill

### 7.4 ปรับปรุงจากกฎหมายใหม่

เมื่อมีหนังสือเวียนหรือกฎกระทรวงใหม่:
1. อัปเดต `tor_reference_complete.md` — เพิ่มข้อมูลใหม่
2. อัปเดต knowledge files ที่เกี่ยวข้อง
3. อัปเดต checklist ใน skill files

---

## 8. บันทึกการเปลี่ยนแปลง

| เวอร์ชัน | วันที่ | การเปลี่ยนแปลง |
|----------|--------|---------------|
| 1.0 | ม.ค. 2568 | เวอร์ชันแรก — สร้าง 3-skill workflow (Intake/Draft/Review) |
| 1.0 | ม.ค. 2568 | เพิ่ม Real-World TOR Patterns จากการวิเคราะห์ 3 TOR จริง |
| 1.0 | ม.ค. 2568 | สร้าง kb_real_tor_patterns.md สำหรับ ChatGPT |
| 1.0 | ม.ค. 2568 | อัปเดต tor_reference_complete.md เพิ่ม Section 12 |
| 1.0 | ม.ค. 2568 | อัปเดต .kiro/skills/tor-review.md เพิ่ม Real-World section |

---

## ภาคผนวก: ข้อจำกัดและคำเตือน

### สิ่งที่ Skills ทำได้:
- ตรวจสอบความครบถ้วนของหัวข้อ
- ตรวจความถูกต้องตามกฎหมาย/ระเบียบ
- ตรวจความสอดคล้องระหว่างส่วน
- แนะนำข้อแก้ไข + ประเมินความเสี่ยง
- ร่าง TOR ตาม template + กฎหมาย
- เลือกวิธีจัดซื้อจัดจ้างที่เหมาะสม

### สิ่งที่ Skills ไม่ได้ทำ:
- ไม่ใช่ที่ปรึกษากฎหมายตัวจริง — ใช้เป็นเครื่องมือช่วยเท่านั้น
- ไม่รับประกันว่า TOR จะผ่านการอุทธรณ์/ร้องเรียน 100%
- ไม่คำนวณราคากลาง
- ไม่สร้าง BOQ / แบบรูปรายการ
- ไม่ตรวจสอบข้อเท็จจริง (เช่น บริษัทมีผลงานจริงหรือไม่)

### คำแนะนำ:
> TOR ที่ร่างหรือตรวจด้วย AI ควรให้ผู้เชี่ยวชาญด้านพัสดุ/กฎหมายของหน่วยงาน
> ทบทวนอีกครั้งก่อนนำไปใช้จริง โดยเฉพาะโครงการวงเงินสูงหรือมีความซับซ้อน

---

*จัดทำโดย: AI-Assisted Documentation System*  
*อ้างอิง: พ.ร.บ. การจัดซื้อจัดจ้างฯ 2560, ระเบียบกระทรวงการคลังฯ 2560, หนังสือเวียน กรมบัญชีกลาง*
