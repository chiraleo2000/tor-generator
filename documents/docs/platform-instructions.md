# คู่มือการใช้ Skills ร่าง TOR / ตรวจสอบ TOR บน LLM Platforms

## ภาพรวม Skills ที่มี

| Skill | หน้าที่ | Input | Output |
|-------|---------|-------|--------|
| **tor-intake** | เก็บ requirement จากผู้ใช้ | Free-form text | Structured JSON |
| **tor-draft** | ร่าง TOR ด้วยภาษาราชการ | Structured data จาก intake | TOR ฉบับเต็ม (.md → .docx) |
| **tor-review** | ตรวจสอบ TOR ที่ร่างแล้ว | ร่าง TOR + ข้อมูลโครงการ | รายงานผลตรวจ + ข้อแก้ไข |

## กระบวนการทำงาน 2 โหมด

### โหมด A: ร่าง TOR (Drafting)
```
ผู้ใช้ → [tor-intake] → structured data → [tor-draft] → TOR ฉบับร่าง → [tor-review] → TOR สมบูรณ์
```

### โหมด B: ตรวจสอบ TOR (Review)
```
ผู้ใช้ + ร่าง TOR (จากภายนอก) → [tor-review] → รายงานผลตรวจ + ข้อเสนอแนะ
```

---

## 1. Kiro (AWS IDE)

### Setup
```
โปรเจกต์นี้ → เปิดด้วย Kiro → Skills จะ activate อัตโนมัติจาก .kiro/skills/
```

### ไฟล์ที่ Kiro อ่านอัตโนมัติ:
- `.kiro/steering/procurement.md` — context เกี่ยวกับโปรเจกต์ (auto-inclusion)
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
ผู้ใช้: "ตรวจสอบ TOR นี้ให้หน่อย" + แนบไฟล์ TOR หรือ paste เนื้อหา
→ Kiro จะใช้ tor-review ตรวจตาม checklist 40+ ข้อ
→ ส่งรายงานผลตรวจ + ข้อเสนอแนะ
```

### Knowledge Files ที่อ้างอิง:
- `knowledge-base/05-reference-summary/tor_reference_complete.md`
- `knowledge-base/04-decision-rules/method_selection.json`
- `knowledge-base/04-decision-rules/template_selection.json`
- `prompts/tor_writing_guide.md`

---

## 2. Claude (Cowork / Projects)

### Setup — Claude Projects
1. สร้าง Project ใหม่ชื่อ "TOR จัดซื้อจัดจ้างภาครัฐ"
2. ตั้ง **Project Instructions** → copy เนื้อหาจาก `prompts/claude_project_instructions.md`
3. Upload **Knowledge Files** (ลำดับสำคัญ):
   - `prompts/tor_writing_guide.md` ← ภาษาราชการ + สำนวน
   - `knowledge-base/05-reference-summary/tor_reference_complete.md` ← กฎหมาย/reference
   - `knowledge-base/04-decision-rules/method_selection.json` ← decision rules
   - `knowledge-base/04-decision-rules/template_selection.json` ← template matrix
   - `knowledge-base/04-decision-rules/document_checklist.json` ← เอกสารที่ต้องทำ
   - `.kiro/skills/tor-review.md` ← checklist ตรวจสอบ (ใช้เป็น reference)

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
+ แนบไฟล์ TOR (.docx/.pdf) หรือ paste เนื้อหา
+ (Optional) ระบุ: วงเงิน, ประเภทพัสดุ, วิธีจัดซื้อ

Claude จะ:
1. ระบุประเภทงาน/วิธีจัดซื้อ
2. ตรวจตาม checklist 5 หมวด (A-E)
3. ส่งรายงานผล พร้อมข้อเสนอแนะเรียงตามความสำคัญ
```

### Setup — Claude Cowork (Team)
- เหมือน Claude Projects แต่แชร์ Project กับทีม
- ทุกคนในทีมเข้าถึง knowledge files + instructions เดียวกัน
- แนะนำ: ตั้ง naming convention สำหรับ conversation เช่น "[TOR-Draft] โครงการ X" หรือ "[TOR-Review] โครงการ Y"

---

## 3. ChatGPT (Works / Projects)

### Setup — ChatGPT Projects (Plus/Team)
1. สร้าง Project ใหม่ชื่อ "TOR จัดซื้อจัดจ้าง"
2. ตั้ง **Custom Instructions** → copy จาก `prompts/chatgpt_system_prompt.md`
3. Upload files เป็น **Project Knowledge**:
   - `prompts/tor_writing_guide.md`
   - `knowledge-base/05-reference-summary/tor_reference_complete.md`
   - `knowledge-base/04-decision-rules/method_selection.json`
   - `knowledge-base/04-decision-rules/template_selection.json`
   - `.kiro/skills/tor-review.md` (ใช้เป็น checklist reference)

### วิธีใช้:
เหมือน Claude — พิมพ์ request เป็นภาษาธรรมชาติ:
- ร่าง: "ร่าง TOR จ้างบริการ cloud วงเงิน 800,000 บาท"
- ตรวจ: "ตรวจ TOR นี้" + paste/upload เนื้อหา

### Setup — ChatGPT Works (Enterprise)
- Admin สร้าง Custom GPT ชื่อ "TOR Advisor"
- Upload knowledge files ทั้งหมดเข้า GPT
- ตั้ง Instructions จาก `prompts/chatgpt_system_prompt.md`
- แชร์ GPT ให้ทุกคนในองค์กร

---

## 4. Cursor (AI IDE)

### Setup
1. เปิดโปรเจกต์ด้วย Cursor
2. สร้างไฟล์ `.cursorrules` ที่ root:

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

## 5. Platforms อื่นๆ (Gemini, Copilot, local LLM)

### หลักการทั่วไป:
1. **System Prompt**: ใช้ `prompts/chatgpt_system_prompt.md` เป็นฐาน (ปรับตาม platform)
2. **Knowledge/Context**: Upload หรือ paste เนื้อหาจาก:
   - `prompts/tor_writing_guide.md` (ภาษา)
   - `knowledge-base/05-reference-summary/tor_reference_complete.md` (กฎหมาย)
   - `.kiro/skills/tor-review.md` (checklist)
3. **ข้อจำกัด context window**: ถ้า context จำกัด ให้ใช้ตามลำดับความสำคัญ:
   - Priority 1: `tor_writing_guide.md` (ภาษาราชการ)
   - Priority 2: `tor_reference_complete.md` บทที่ 2-4 (วิธีจัดซื้อ + กฎระเบียบ TOR)
   - Priority 3: `tor-review.md` checklist (ถ้าใช้โหมดตรวจ)
   - Priority 4: decision rules JSON files

### สำหรับ Local LLM (Ollama, LM Studio):
- ใช้ RAG: embed knowledge-base/ ทั้งโฟลเดอร์
- System prompt: ใช้ `chatgpt_system_prompt.md` ตัดสั้นลง
- แนะนำ model: ขนาด ≥ 70B สำหรับภาษาไทย (Qwen2.5, Llama3.3)

---

## 6. เปรียบเทียบ Platforms

| Feature | Kiro | Claude Projects | ChatGPT Projects | Cursor |
|---------|------|-----------------|------------------|--------|
| Auto-load skills | ✓ (steering) | ✗ (manual upload) | ✗ (manual upload) | ✗ (.cursorrules) |
| Knowledge files | อ่าน repo ตรง | Upload ≤ 50 files | Upload ≤ 20 files | @file reference |
| Max context | ~200K tokens | ~200K tokens | ~128K tokens | ~128K tokens |
| ภาษาไทย | ดี (Claude) | ดีมาก | ดี | ดี (ใช้ Claude/GPT) |
| File output (.docx) | ✓ (script) | ✗ (Markdown) | ✗ (Markdown) | ✓ (script) |
| Team sharing | ✗ | ✓ (Cowork) | ✓ (Works) | ✗ |
| Best for | Dev + TOR draft | Review + Draft | Quick draft | Inline edit |

---

## 7. Tips การใช้งาน

### สำหรับร่าง TOR:
1. **เตรียมข้อมูลก่อน**: ชื่อโครงการ, วงเงิน, ประเภทงาน, ขอบเขตคร่าวๆ
2. **ให้ AI ถามกลับ**: อย่าพยายามใส่ข้อมูลทั้งหมดในครั้งเดียว
3. **ตรวจ output**: ใช้ tor-review checklist ตรวจซ้ำเสมอ
4. **ปรับภาษา**: ถ้า AI ใช้ภาษาไม่เป็นทางการ ให้สั่ง "ปรับให้เป็นภาษาราชการ"

### สำหรับตรวจสอบ TOR:
1. **ให้ context ครบ**: วงเงิน + ประเภทพัสดุ + วิธีจัดซื้อ
2. **ส่ง TOR ทั้งฉบับ**: ไม่ตัดบางส่วน (AI ต้องดูความสอดคล้องระหว่างหัวข้อ)
3. **ถามเจาะลึก**: "ข้อไหนมีความเสี่ยงสูงสุด?" หรือ "ข้อนี้ขัดกฎหมายตรงไหน?"
4. **ให้ AI เสนอแก้ไข**: "ช่วยเขียนใหม่ให้ถูกต้อง" ในข้อที่ไม่ผ่าน

### ข้อควรระวัง:
- AI อาจ hallucinate เลขมาตรา/ข้อ — ตรวจสอบอ้างอิงกับ reference document เสมอ
- ราคากลางต้องคำนวณจริง — AI ไม่สามารถกำหนดราคาให้ได้
- คุณสมบัติเฉพาะหน่วยงาน — ต้อง input จากผู้ใช้ (AI ไม่รู้ระเบียบภายใน)
