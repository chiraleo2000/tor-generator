# check-TORs-Skills - ตรวจสอบ TOR จัดซื้อจัดจ้างภาครัฐ

ชุด Skills สำหรับ **ตรวจสอบ** TOR (Terms of Reference) ที่ร่างแล้ว ตามกฎหมายจัดซื้อจัดจ้างภาครัฐไทย พ.ร.บ. 2560

> **ดู Draft-TORs-Skills/ สำหรับ Skill ร่าง TOR**

---

## สิ่งที่ Skill นี้ทำ

เมื่อผู้ใช้ส่ง TOR มาตรวจ Skill จะ:
1. ระบุประเภทพัสดุ + วิธีจัดซื้อ
2. ตรวจความครบถ้วน 13 หัวข้อ
3. ตรวจความถูกต้องตามกฎหมาย 10 ข้อ
4. ตรวจความสอดคล้องระหว่างส่วน 6 ข้อ
5. ตรวจข้อกำหนดเฉพาะประเภทงาน
6. ตรวจภาษาและรูปแบบ
7. ส่งรายงานผลตรวจ + ข้อเสนอแนะเรียงตามความสำคัญ

---

## Platforms

| Platform | Format | Folder |
|----------|--------|--------|
| **Claude** Code/Projects | SKILL.md + references/ + assets/ | `claude/` |
| **ChatGPT** GPT/Codex | instructions.md + SKILL.md + knowledge/ | `chatgpt/` |
| **Gemini** NotebookLM/Gems | sources/ + instructions | `gemini-notebooklm/` |
| **Hermes** Agent/Desktop | SKILL.md + references/ | `hermes-agent/` |

---

## Directory Structure

```
check-TORs-Skills/
├── README.md
├── claude/
│   └── tor-review/
│       ├── SKILL.md
│       ├── references/          # 10 knowledge files
│       └── assets/
│           └── review_report_template.md
├── chatgpt/
│   └── tor-review/
│       ├── SKILL.md
│       ├── instructions.md
│       ├── gpt-config.json
│       └── knowledge/           # 10 knowledge files
├── gemini-notebooklm/
│   ├── gemini-chat-instruction.md
│   ├── notebook-instruction.md
│   └── sources/                 # 10 knowledge files
└── hermes-agent/
    └── tor-review/
        ├── SKILL.md
        └── references/          # 10 knowledge files
```

---

## Quick Start

### Claude Code
```bash
cp -r claude/tor-review ~/.claude/skills/
```

### ChatGPT Custom GPT
1. Create GPT "TOR Checker"
2. Paste `instructions.md`
3. Upload files from `knowledge/`

### Gemini NotebookLM
1. Create Notebook
2. Upload all from `sources/`
3. Set Notebook guide from `notebook-instruction.md`

### Hermes
```bash
cp -r hermes-agent/tor-review ~/.hermes/skills/audit/
```

---

## Usage

```
ผู้ใช้: "ตรวจสอบ TOR นี้ให้หน่อย" + [paste TOR content]

AI จะ:
1. วิเคราะห์ประเภทงาน + วิธีจัดซื้อ
2. ตรวจตาม checklist 5 หมวด (A-E)
3. ส่งรายงานผลตรวจ:
   - สถานะ: ผ่าน/ไม่ผ่าน
   - ระดับเสี่ยง: ต่ำ-วิกฤต
   - ข้อแก้ไข: 🔴วิกฤต 🟠สำคัญ 🟡แนะนำ
```

---

## Critical Checks (ข้อที่ต้องผ่าน)

| Code | ข้อตรวจ | ผลกระทบถ้าไม่ผ่าน |
|------|---------|-------------------|
| B2 | ไม่ล็อกสเปค/เอื้อผู้ประกอบการ | จัดซื้อเป็นโมฆะ |
| B4 | วิธีจัดซื้อตรงวงเงิน | จัดซื้อเป็นโมฆะ |
| B7 | ไม่แบ่งซื้อ/แบ่งจ้าง | โทษอาญา ม.120 |
| B3 | คุณสมบัติไม่เกินจำเป็น | กีดกันการแข่งขัน |
