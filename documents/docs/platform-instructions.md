# คู่มือการใช้สกิลร่าง TOR / ตรวจสอบ TOR บนแพลตฟอร์ม LLM

## ภาพรวมสกิลที่มี

| สกิล | หน้าที่ | ข้อมูลเข้า | ผลลัพธ์ |
|-------|---------|------------|---------|
| **tor-intake** | เก็บความต้องการจากผู้ใช้ | ข้อความอิสระ | JSON โครงสร้าง |
| **tor-draft** | ร่าง TOR ด้วยภาษาราชการ | ข้อมูลโครงสร้างจาก intake | TOR ฉบับเต็ม (.md → .docx) |
| **tor-review** | ตรวจสอบ TOR ที่ร่างแล้ว | ร่าง TOR + ข้อมูลโครงการ | รายงานผลตรวจ + ข้อแก้ไข |

## กระบวนการทำงาน 2 โหมด

### โหมด ก: ร่าง TOR
```
ผู้ใช้ → [tor-intake] → ข้อมูลโครงสร้าง → [tor-draft] → TOR ฉบับร่าง → [tor-review] → TOR สมบูรณ์
```

### โหมด ข: ตรวจสอบ TOR
```
ผู้ใช้ + ร่าง TOR (จากภายนอก) → [tor-review] → รายงานผลตรวจ + ข้อเสนอแนะ
```

---

## 1. Kiro (AWS IDE)

### การตั้งค่า
```
โปรเจกต์นี้ → เปิดด้วย Kiro → สกิลจะเปิดเองจาก .kiro/skills/
```

### ไฟล์ที่ Kiro อ่านอัตโนมัติ:
- `.kiro/steering/procurement.md` — บริบทโปรเจกต์ (แนบอัตโนมัติ)
- `.kiro/skills/tor-intake.md` — skill เก็บ requirement
- `.kiro/skills/tor-draft.md` — skill ร่าง TOR
- `.kiro/skills/tor-review.md` — skill ตรวจสอบ TOR

### วิธีใช้ — ร่าง TOR:
```
ผู้ใช้: "ร่าง TOR จ้างพัฒนาระบบ HRM วงเงิน 3 ล้าน สำหรับ กรมสรรพากร"
→ Kiro จะใช้ tor-intake ถามข้อมูลเพิ่ม
→ จากนั้นใช้ tor-draft ร่าง TOR ด้วยภาษาราชการ
→ สุดท้าย tor-review ตรวจสอบอัตโนมัติ
```

### วิธีใช้ — ตรวจสอบ TOR:
```
ผู้ใช้: "ตรวจสอบ TOR นี้ให้หน่อย" + แนบไฟล์ TOR หรือวางเนื้อหา
→ Kiro จะใช้ tor-review ตรวจตามรายการตรวจกว่า 40 ข้อ
→ ส่งรายงานผลตรวจ + ข้อเสนอแนะ
```

### เอกสารความรู้ที่อ้างอิง:
- `knowledge-base/05-reference-summary/tor_reference_complete.md`
- `knowledge-base/04-decision-rules/method_selection.json`
- `knowledge-base/04-decision-rules/template_selection.json`
- `prompts/tor_writing_guide.md`

---

## 2. Claude (Cowork / Projects)

### การตั้งค่า — Claude Projects
1. สร้างโปรเจกต์ใหม่ชื่อ "TOR จัดซื้อจัดจ้างภาครัฐ"
2. ตั้ง **คำสั่งโปรเจกต์** → คัดลอกเนื้อหาจาก `prompts/claude_project_instructions.md`
3. อัปโหลด **เอกสารความรู้** (ลำดับสำคัญ):
   - `prompts/tor_writing_guide.md` ← ภาษาราชการ + สำนวน
   - `knowledge-base/05-reference-summary/tor_reference_complete.md` ← กฎหมาย/reference
   - `knowledge-base/04-decision-rules/method_selection.json` ← decision rules
   - `knowledge-base/04-decision-rules/template_selection.json` ← template matrix
   - `knowledge-base/04-decision-rules/document_checklist.json` ← เอกสารที่ต้องทำ
   - `.kiro/skills/tor-review.md` ← รายการตรวจ (ใช้อ้างอิง)

### วิธีใช้ — ร่าง TOR:
```
พิมพ์: "ช่วยร่าง TOR จ้างพัฒนาระบบ [ชื่อระบบ] วงเงิน [X] บาท สำหรับ [หน่วยงาน]"
Claude จะ:
1. ถามข้อมูลเพิ่ม (ประเภทพัสดุ, ขอบเขต, ระยะเวลา, เงื่อนไขพิเศษ)
2. กำหนดวิธีจัดซื้อตาม decision rules
3. ร่าง TOR ด้วยภาษาราชการ ครบทุกหัวข้อ
4. ตรวจสอบอัตโนมัติก่อนส่ง
```

### วิธีใช้ — ตรวจสอบ TOR:
```
พิมพ์: "ตรวจสอบ TOR ฉบับนี้ให้ครบถ้วนและถูกต้องตามกฎหมาย"
+ แนบไฟล์ TOR (.docx/.pdf) หรือวางเนื้อหา
+ (ถ้ามี) ระบุ: วงเงิน, ประเภทพัสดุ, วิธีจัดซื้อ

Claude จะ:
1. ระบุประเภทงาน/วิธีจัดซื้อ
2. ตรวจตามรายการ 5 หมวด (ก–จ)
3. ส่งรายงานผล พร้อมข้อเสนอแนะเรียงตามความสำคัญ
```

### การตั้งค่า — Claude Cowork (ทีม)
- เหมือน Claude Projects แต่แชร์โปรเจกต์กับทีม
- ทุกคนในทีมเข้าถึงเอกสารความรู้และคำสั่งเดียวกัน
- แนะนำ: ตั้งชื่อบทสนทนา เช่น "[TOR-Draft] โครงการ X" หรือ "[TOR-Review] โครงการ Y"

---

## 3. ChatGPT (Works / Projects)

### การตั้งค่า — ChatGPT Projects (Plus/Team)
1. สร้างโปรเจกต์ใหม่ชื่อ "TOR จัดซื้อจัดจ้าง"
2. ตั้ง **คำสั่งกำหนดเอง** → คัดลอกจาก `prompts/chatgpt_system_prompt.md`
3. อัปโหลดไฟล์เป็น **ความรู้ของโปรเจกต์**:
   - `prompts/tor_writing_guide.md`
   - `knowledge-base/05-reference-summary/tor_reference_complete.md`
   - `knowledge-base/04-decision-rules/method_selection.json`
   - `knowledge-base/04-decision-rules/template_selection.json`
   - `.kiro/skills/tor-review.md` (ใช้อ้างอิงรายการตรวจ)

### วิธีใช้:
เหมือน Claude — พิมพ์คำขอเป็นภาษาธรรมชาติ:
- ร่าง: "ร่าง TOR จ้างบริการ cloud วงเงิน 800,000 บาท"
- ตรวจ: "ตรวจ TOR นี้" + วาง/อัปโหลดเนื้อหา

### การตั้งค่า — ChatGPT Works (องค์กร)
- ผู้ดูแลสร้าง Custom GPT ชื่อ "TOR Advisor"
- อัปโหลดเอกสารความรู้ทั้งหมดเข้า GPT
- ตั้งคำสั่งจาก `prompts/chatgpt_system_prompt.md`
- แชร์ GPT ให้ทุกคนในองค์กร

---

## 4. Cursor (AI IDE)

### การตั้งค่า
1. เปิดโปรเจกต์ด้วย Cursor
2. สร้างไฟล์ `.cursorrules` ที่รากโปรเจกต์:

```
# .cursorrules
You are a Thai government procurement TOR expert.
Always use formal Thai bureaucratic language (ภาษาราชการ).
Reference: prompts/tor_writing_guide.md for language guidelines.
Reference: knowledge-base/05-reference-summary/tor_reference_complete.md for legal rules.
Reference: .kiro/skills/tor-review.md for review checklist.

When drafting TOR:
- Use decision rules from knowledge-base/04-decision-rules/
- Follow template structure from templates/base/tor_base.md
- Write in formal Thai government language only

When reviewing TOR:
- Use checklist from .kiro/skills/tor-review.md
- Check all 5 categories (A-E)
- Output a structured review report
```

3. ใช้ `@file` reference ใน chat:
```
@tor_writing_guide.md @tor_reference_complete.md ร่าง TOR จ้างพัฒนาระบบ...
```

### วิธีใช้:
- **Cmd+K** (inline edit): เลือก text ใน TOR ที่ต้องการปรับปรุง → "ปรับให้เป็นภาษาราชการ"
- **Cmd+L** (chat): "ร่าง TOR..." หรือ "ตรวจสอบ TOR ในไฟล์ X"
- **@file** reference: อ้างไฟล์ knowledge โดยตรง

---

## 5. แพลตฟอร์มอื่น (Gemini, Copilot, LLM ในเครื่อง)

### หลักการทั่วไป:
1. **คำสั่งระบบ**: ใช้ `prompts/chatgpt_system_prompt.md` เป็นฐาน (ปรับตามแพลตฟอร์ม)
2. **เอกสารความรู้/บริบท**: อัปโหลดหรือวางเนื้อหาจาก:
   - `prompts/tor_writing_guide.md` (ภาษา)
   - `knowledge-base/05-reference-summary/tor_reference_complete.md` (กฎหมาย)
   - `.kiro/skills/tor-review.md` (รายการตรวจ)
3. **ข้อจำกัดหน้าต่างบริบท**: ถ้าบริบทจำกัด ให้ใช้ตามลำดับความสำคัญ:
   - ลำดับ 1: `tor_writing_guide.md` (ภาษาราชการ)
   - ลำดับ 2: `tor_reference_complete.md` บทที่ 2-4 (วิธีจัดซื้อ + กฎระเบียบ TOR)
   - ลำดับ 3: `tor-review.md` รายการตรวจ (ถ้าใช้โหมดตรวจ)
   - ลำดับ 4: ไฟล์ JSON กฎตัดสินใจ

### สำหรับ LLM ในเครื่อง (Ollama, LM Studio):
- ใช้ค้นหาคลังความรู้: ฝังเวกเตอร์ทั้งโฟลเดอร์ knowledge-base/
- คำสั่งระบบ: ใช้ `chatgpt_system_prompt.md` ตัดสั้นลง
- แนะนำโมเดล: ขนาดไม่ต่ำกว่า 70B สำหรับภาษาไทย (Qwen2.5, Llama3.3)

---

## 6. เปรียบเทียบแพลตฟอร์ม

| คุณสมบัติ | Kiro | Claude Projects | ChatGPT Projects | Cursor |
|---------|------|-----------------|------------------|--------|
| โหลดสกิลอัตโนมัติ | ✓ (steering) | ✗ (อัปโหลดเอง) | ✗ (อัปโหลดเอง) | ✗ (.cursorrules) |
| เอกสารความรู้ | อ่านรีโปตรง | อัปโหลดไม่เกิน 50 ไฟล์ | อัปโหลดไม่เกิน 20 ไฟล์ | อ้างด้วย @file |
| บริบทสูงสุด | ประมาณ 200K โทเคน | ประมาณ 200K โทเคน | ประมาณ 128K โทเคน | ประมาณ 128K โทเคน |
| ภาษาไทย | ดี (Claude) | ดีมาก | ดี | ดี (ใช้ Claude/GPT) |
| ส่งออกไฟล์ (.docx) | ✓ (สคริปต์) | ✗ (Markdown) | ✗ (Markdown) | ✓ (สคริปต์) |
| แชร์ทีม | ✗ | ✓ (Cowork) | ✓ (Works) | ✗ |
| เหมาะกับ | พัฒนา + ร่าง TOR | ตรวจ + ร่าง | ร่างเร็ว | แก้ข้อความในไฟล์ |

---

## 7. ข้อแนะนำการใช้งาน

### สำหรับร่าง TOR:
1. **เตรียมข้อมูลก่อน**: ชื่อโครงการ, วงเงิน, ประเภทงาน, ขอบเขตคร่าวๆ
2. **ให้ AI ถามกลับ**: อย่าพยายามใส่ข้อมูลทั้งหมดในครั้งเดียว
3. **ตรวจผลลัพธ์**: ใช้รายการตรวจ tor-review ซ้ำเสมอ
4. **ปรับภาษา**: ถ้า AI ใช้ภาษาไม่เป็นทางการ ให้สั่ง "ปรับให้เป็นภาษาราชการ"

### สำหรับตรวจสอบ TOR:
1. **ให้บริบทครบ**: วงเงิน + ประเภทพัสดุ + วิธีจัดซื้อ
2. **ส่ง TOR ทั้งฉบับ**: ไม่ตัดบางส่วน (AI ต้องดูความสอดคล้องระหว่างหัวข้อ)
3. **ถามเจาะลึก**: "ข้อไหนมีความเสี่ยงสูงสุด?" หรือ "ข้อนี้ขัดกฎหมายตรงไหน?"
4. **ให้ AI เสนอแก้ไข**: "ช่วยเขียนใหม่ให้ถูกต้อง" ในข้อที่ไม่ผ่าน

### ข้อควรระวัง:
- AI อาจแต่งเลขมาตรา/ข้อ — ตรวจสอบอ้างอิงกับเอกสารอ้างอิงเสมอ
- ราคากลางต้องคำนวณจริง — AI ไม่สามารถกำหนดราคาให้ได้
- คุณสมบัติเฉพาะหน่วยงาน — ต้องให้ผู้ใช้ระบุ (AI ไม่รู้ระเบียบภายใน)
