---
inclusion: auto
---

# Procurement TOR Drafting Context

โปรเจกต์นี้เป็นระบบ AI สำหรับร่าง TOR จัดซื้อจัดจ้างภาครัฐไทย ตาม พ.ร.บ. 2560

## กฎสำคัญ: ภาษาราชการ
- TOR ทุกฉบับต้องเขียนด้วย **ภาษาราชการ** เท่านั้น
- อ้างอิง `prompts/tor_writing_guide.md` สำหรับสำนวน/คำศัพท์/โครงสร้างประโยค
- ห้ามใช้ภาษาพูด ภาษาปาก คำย่อไม่เป็นทางการ
- ใช้สำนวน "ด้วย...มีความประสงค์จะ...", "ภายในระยะเวลา...นับถัดจาก..."

## โครงสร้างโปรเจกต์
- `knowledge-base/` — ข้อมูลกฎหมาย/ระเบียบที่ extract แล้ว (JSON)
- `templates/` — TOR templates (base + method layers + type layers)
- `prompts/` — System prompts สำหรับ ChatGPT/Claude
- `.kiro/skills/` — Kiro skills: tor-intake, tor-draft, tor-review
- `scripts/` — Python pipeline: extract PDF → analyze → knowledge base
- `raw_text/` — Raw text ที่ extract จาก PDF/DOCX
- `analysis/` — ผลวิเคราะห์โครงสร้างเอกสาร

## Skills ที่ใช้
1. **tor-intake** — เก็บ requirement, กำหนดวิธีจัดซื้อ
2. **tor-draft** — ร่าง TOR จาก structured data
3. **tor-review** — ตรวจสอบ TOR ตามกฎหมาย

## กฎหมายหลักที่อ้างอิง
- พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560
- ระเบียบกระทรวงการคลังฯ พ.ศ. 2560
- กฎกระทรวง 8 ฉบับ
- หนังสือเวียนกรมบัญชีกลาง 9 ฉบับ
