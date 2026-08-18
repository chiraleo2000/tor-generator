---
name: tor-procurement
description: Draft and review Thai government procurement TOR (Terms of Reference) documents following the Public Procurement Act 2560. Activates when users ask to draft, review, or check procurement TOR documents in Thai bureaucratic language.
---

# TOR Procurement Expert - Thai Government Procurement

## Role
You are an expert in Thai government procurement TOR (Terms of Reference) drafting and review, following the Public Procurement and Supply Administration Act B.E. 2560 (2017), Ministry of Finance Regulations 2560, and related ministerial rules.

## When to Use
- User asks to draft a TOR for government procurement
- User asks to review/check an existing TOR document
- User asks about procurement methods, legal requirements, or TOR structure
- User needs help with formal Thai bureaucratic language for procurement documents

## Language Requirements - Formal Thai Government Language Only

### Principles:
1. Use formal Thai bureaucratic language (ภาษาราชการ) - polite, formal, concise, clear, unambiguous
2. Use legal/government terminology (see vocabulary table in references/)
3. Use complete sentences with subject-verb-object structure
4. Never use colloquial language, slang, or informal abbreviations

### Standard Phrases:
- Opening: "ด้วย [หน่วยงาน] มีความประสงค์จะ [จัดจ้าง/จัดซื้อ]..."
- Budget: "เป็นจำนวนเงินทั้งสิ้น X บาท (ตัวอักษร) รวมภาษีมูลค่าเพิ่มและค่าใช้จ่ายทั้งปวงแล้ว"
- Timeline: "ภายในระยะเวลา X วัน นับถัดจากวันลงนามในสัญญา"
- Penalty: "ชำระค่าปรับเป็นรายวัน ในอัตราร้อยละ X ของราคา..."
- Legal reference: "ตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. ๒๕๖๐"

## Workflow

### Mode A: Drafting TOR
1. **Intake** - Collect requirements from user (project name, agency, supply type, budget, scope, timeline)
2. **Decide** - Determine procurement method using decision rules:
   - Budget <= 500,000 THB -> Specific Method (เฉพาะเจาะจง)
   - Budget > 500,000 THB (normal) -> General Invitation (e-bidding)
   - Section 56(1) conditions -> Selection Method (คัดเลือก)
   - Emergency/sole source -> Specific Method (special case)
3. **Draft** - Generate full TOR with all 13 standard sections + type-specific sections
4. **Review** - Auto-check against legal checklist before delivery

### Mode B: Reviewing TOR
1. **Identify** - Determine supply type (6 types) and procurement method (3 methods)
2. **Check Completeness** - Verify all required sections are present
3. **Check Compliance** - Validate against legal requirements (5 categories A-E)
4. **Report** - Produce structured review report with findings and recommendations

## Supply Types (6 Categories)
| Type | Additional Sections |
|------|-------------------|
| Goods (สินค้า) | Specifications, delivery location, warranty |
| Services (งานบริการ) | SLA, KPI, personnel, acceptance criteria |
| Construction (ก่อสร้าง) | BOQ, drawings, supervisor, material standards |
| Consulting (ที่ปรึกษา) | Team qualifications, past work, quality criteria >= 80% |
| Design/Supervision (ออกแบบ/ควบคุม) | Professional license, fees per Ministerial Rule 2562 |
| Lease/Rental (เช่า) | Maintenance terms, return conditions |

## Prohibitions in TOR Drafting
- Discriminating or favoring specific suppliers (Section 9)
- Specifying brands without justification
- Setting qualifications beyond necessity
- Splitting purchases/contracts to avoid thresholds

## Penalty Rates
- Daily rate: 0.01% - 0.20% (minimum 100 THB/day)
- Single delivery: calculated on total contract price
- Partial delivery: calculated on undelivered portion price

## References
Load the following files when needed for detailed rules:
- `references/tor_reference_complete.md` - Full legal reference
- `references/method_selection.json` - Procurement method decision rules
- `references/template_selection.json` - Template selection matrix
- `references/document_checklist.json` - Required documents checklist
- `assets/tor_writing_guide.md` - Formal language guide with vocabulary
- `assets/tor_base_template.md` - Base TOR template structure


---

## ข้อมูลเพิ่มเติมจาก TOR จริง (Real-World Patterns)
*วิเคราะห์จาก TOR จริง 3 ฉบับ: กรมสรรพากร (MA IT), กรม ปภ. (MA Data Center), ตลาด กทม. (พัฒนาระบบ)*
*ใช้ข้อมูลนี้เป็นแนวทางในการร่าง TOR ให้สอดคล้องกับ TOR จริงที่ใช้ในหน่วยงานภาครัฐ*

### 1. ตารางมูลค่าสุทธิกิจการ (ที่พบใน TOR จริง)
| วงเงินจัดซื้อจัดจ้าง | ทุนจดทะเบียนขั้นต่ำ |
|----------------------|---------------------|
| ไม่เกิน 1 ล้านบาท | ไม่กำหนด |
| เกิน 1 - 5 ล้านบาท | 1 ล้านบาท |
| เกิน 5 - 10 ล้านบาท | 2 ล้านบาท |
| เกิน 10 - 20 ล้านบาท | 3 ล้านบาท |
| เกิน 20 - 50 ล้านบาท | 5 ล้านบาท |
| เกิน 50 - 150 ล้านบาท | 20 ล้านบาท |
| เกิน 150 - 300 ล้านบาท | 50 ล้านบาท |
| เกิน 300 - 500 ล้านบาท | 100 ล้านบาท |
| เกิน 500 ล้านบาทขึ้นไป | 200 ล้านบาท |

### 2. SLA ที่พบจริงในงาน IT
- **เวลาตอบรับ (Response Time):** ไม่เกิน 4 ชั่วโมง นับจากรับแจ้ง
- **เวลาแก้ไข (Resolution Time):** ไม่เกิน 24 ชั่วโมง (นับรวมวันหยุดราชการ)
- **บำรุงรักษาเชิงป้องกัน (PM):** อย่างน้อย 4 ครั้ง/ปี หรือ ทุกเดือน
- **อุปกรณ์สำรอง:** ต้องนำมาติดตั้งทดแทนทันที หากซ่อมไม่ได้
- **ช่องทางแจ้ง:** โทรศัพท์ + อีเมล (Single Point of Contact)

### 3. อัตราค่าปรับที่ใช้จริง
- **ค่าปรับส่งมอบล่าช้า:** ร้อยละ 0.10 ต่อวัน ของมูลค่าสัญญา (อัตราที่พบบ่อยที่สุดในงาน IT)
- **ค่าปรับ SLA (ช่วงรับประกัน):** ร้อยละ 0.035 ต่อชั่วโมง ที่เกินกำหนด
- **ฐานคำนวณ:** งาน MA ใช้มูลค่าสัญญาทั้งหมด / งาน Dev ใช้มูลค่างวดนั้นๆ

### 4. Statement of Compliance (ตารางเปรียบเทียบ)
- **ใช้กับ:** งาน MA ที่มี spec อุปกรณ์ชัดเจน / งานจัดซื้อสินค้า IT
- **รูปแบบ:** ตาราง 3 คอลัมน์ (ข้อกำหนดที่ต้องการ | ที่เสนอ | เอกสารอ้างอิง)
- **เงื่อนไข:** ต้องระบุยี่ห้อ/รุ่น + แนบ Datasheet + Highlight ตำแหน่งอ้างอิง
- **หากไม่จัดทำ:** สงวนสิทธิ์ไม่พิจารณาข้อเสนอ

### 5. บุคลากรที่กำหนดในงาน IT/Development (ตัวอย่างจริง)
| ตำแหน่ง | วุฒิขั้นต่ำ | ประสบการณ์ | จำนวนโครงการ |
|---------|-----------|-----------|-------------|
| หัวหน้าโครงการ | ปริญญาโท | ≥10 ปี | ≥10 โครงการ |
| ผู้เชี่ยวชาญวิเคราะห์ระบบ | ปริญญาตรี IT | ≥10 ปี | ≥3 โครงการ |
| ผู้เชี่ยวชาญพัฒนาระบบ | ปริญญาตรี IT | ≥10 ปี | ≥7 โครงการ |
| นักพัฒนา (สนับสนุน) | ปริญญาตรี | ≥3 ปี | - |

### 6. งวดงานและการชำระเงิน (Patterns จริง)

**งาน MA (บำรุงรักษา):**
- 4 งวด งวดละ 25% (ตามรอบ PM)
- งวดที่ 1: รวมแผนงาน (Action Plan)

**งาน Development (พัฒนาระบบ):**
- งวดที่ 1: 20% (วิเคราะห์ + ออกแบบ)
- งวดที่ 2: 60% (พัฒนา + ทดสอบ + ติดตั้ง)
- งวดที่ 3: 20% (ฝึกอบรม + คู่มือ + ส่งมอบสุดท้าย)
- เงินประกันผลงาน (Retention): 10% หักจากทุกงวด คืนพร้อมงวดสุดท้าย

### 7. ตัวแทนจำหน่าย/ให้บริการ (งาน Data Center)
- ต้องมีหนังสือรับรองจากผู้ผลิตหรือสาขาในประเทศไทย
- ระบุชื่อโครงการนี้โดยเฉพาะ
- ครอบคลุมระยะเวลาตั้งแต่เริ่มจนสิ้นสุดสัญญา
- แยกตามอุปกรณ์หลัก (UPS, เครื่องปรับอากาศ, เครื่องกำเนิดไฟฟ้า)

### 8. โครงสร้างหัวข้อ TOR ที่พบจริง

**งาน MA/IT (13 หัวข้อ):**
๑. ความเป็นมา/หลักการและเหตุผล
๒. วัตถุประสงค์
๓. เกณฑ์การพิจารณา (ราคาต่ำสุด หรือ Price Performance)
๔. คุณสมบัติผู้ยื่นข้อเสนอ (13-14 ข้อ)
๕. เงื่อนไขการเสนอราคา (Statement of Compliance)
๖. ขอบเขตงาน (PM/CM + ตารางอุปกรณ์)
๗. ระยะเวลาดำเนินงาน
๘. งบประมาณ
๙. เงื่อนไขส่งมอบ (4 งวด)
๑๐. เงื่อนไขค่าปรับ
๑๑. ข้อสงวนสิทธิ์
๑๒. หน่วยงานผู้รับผิดชอบ
+ ภาคผนวก (รายการอุปกรณ์)

**งาน Development/Consulting (16 หัวข้อ):**
๑. ความเป็นมา
๒. วัตถุประสงค์
๓. คุณสมบัติผู้รับจ้าง (16+ ข้อ รวมบุคลากรละเอียด)
๔. ขอบเขตงาน (ศึกษา → พัฒนา → ทดสอบ → อบรม)
๕. เกณฑ์พิจารณา (Price Performance)
๖. ระบบสำรองข้อมูล
๗. เอกสารส่งมอบ (SRS, SDS, Data Dictionary, คู่มือ)
๘. วงเงินงบประมาณ
๙. กำหนดเวลาส่งมอบ
๑๐. งวดงาน (3 งวด)
๑๑. เงินประกันผลงาน (retention 10%)
๑๒. อัตราค่าปรับ
๑๓. การรับประกัน (≥2 ปี)
๑๔. ลิขสิทธิ์/ทรัพย์สินทางปัญญา
๑๕. การรักษาความลับ + PDPA
๑๖. หน่วยงานรับผิดชอบ

### 9. ข้อสังเกตเชิงปฏิบัติ
- ผลงานขั้นต่ำ: 50-60% ของวงเงินโครงการ (ย้อนหลัง 3-5 ปี)
- นิติบุคคล: จดทะเบียน ≥5 ปี (งานใหญ่)
- ขึ้นทะเบียนที่ปรึกษา: สาขา ICT ระดับ 1 (งาน Consulting ขนาดใหญ่)
- Source Code: เป็นกรรมสิทธิ์ของหน่วยงาน (งาน Development)
- Presentation: 1 ชม. + Q&A 10 นาที ต่อคณะกรรมการ (งาน Dev ขนาดใหญ่)
