# Draft-TORs-Skills - ร่าง TOR จัดซื้อจัดจ้างภาครัฐ

ชุด Skills สำหรับ **ร่าง** TOR (Terms of Reference) ตามกฎหมายจัดซื้อจัดจ้างภาครัฐไทย พ.ร.บ. 2560

> **ดู check-TORs-Skills/ สำหรับ Skill ตรวจสอบ TOR**

---

## สรุปแพลตฟอร์ม

| Platform | Format | Install Method | Folder |
|----------|--------|---------------|--------|
| **Kiro** (IDE) | `.kiro/skills/` + steering | Auto-loads from workspace | `.kiro/skills/` (root) |
| **Claude** Code/Projects | `SKILL.md` + `references/` + `assets/` | Copy to `~/.claude/skills/` or upload | `skills/claude/` |
| **ChatGPT** GPT/Projects/Codex | `instructions.md` + `knowledge/` + `SKILL.md` | GPT Builder or Codex CLI | `skills/chatgpt/` |
| **Gemini** NotebookLM/Gems | Sources (.md files) + notebook guide | Upload sources to notebook | `skills/gemini-notebooklm/` |
| **Hermes** Agent/Desktop | `SKILL.md` (extended) + `references/` | `cp` to `~/.hermes/skills/` | `skills/hermes-agent/` |

---

## Directory Structure

```
skills/
├── README.md                          # This file
├── claude/
│   ├── README.md                      # Claude setup guide
│   └── tor-procurement/
│       ├── SKILL.md                   # Main skill (Agent Skills standard)
│       ├── references/                # Legal refs, decision rules
│       │   ├── tor_reference_complete.md
│       │   ├── method_selection.json
│       │   ├── template_selection.json
│       │   └── document_checklist.json
│       └── assets/                    # Templates, language guide
│           ├── tor_writing_guide.md
│           └── tor_base_template.md
│
├── chatgpt/
│   ├── README.md                      # ChatGPT setup guide
│   └── tor-procurement/
│       ├── SKILL.md                   # Codex/Skills format
│       ├── instructions.md            # GPT Builder instructions
│       ├── gpt-config.json            # GPT configuration reference
│       └── knowledge/                 # Upload as knowledge files
│           ├── tor_writing_guide.md
│           ├── tor_reference_complete.md
│           ├── method_selection.json
│           ├── template_selection.json
│           ├── document_checklist.json
│           └── tor_base_template.md
│
├── gemini-notebooklm/
│   ├── README.md                      # NotebookLM/Gemini setup guide
│   ├── notebook-instruction.md        # Paste into "Notebook guide"
│   ├── gemini-chat-instruction.md     # For Gemini Gems
│   └── sources/                       # Upload as notebook sources
│       ├── 01_tor_reference_complete.md
│       ├── 02_tor_writing_guide.md
│       ├── 03_method_selection.md
│       ├── 04_document_checklist.md
│       ├── 05_template_selection.md
│       └── 06_tor_base_template.md
│
└── hermes-agent/
    ├── README.md                      # Hermes setup guide
    └── tor-procurement/
        ├── SKILL.md                   # Extended SKILL.md with Hermes metadata
        └── references/                # Supporting reference files
            ├── method_selection.md
            ├── template_selection.md
            ├── document_checklist.md
            └── tor_writing_guide.md
```

---

## Quick Start (แต่ละแพลตฟอร์ม)

### Kiro (current workspace)
ใช้งานได้ทันที — Kiro อ่าน `.kiro/skills/` และ `.kiro/steering/` อัตโนมัติ

### Claude Code
```bash
cp -r skills/claude/tor-procurement ~/.claude/skills/
```

### Claude Projects (Web)
1. สร้าง Project > ตั้งชื่อ "TOR จัดซื้อจัดจ้างภาครัฐ"
2. Paste SKILL.md content เป็น Project Instructions
3. Upload ไฟล์จาก `references/` + `assets/`

### ChatGPT Custom GPT
1. Create a GPT > Name: "TOR Advisor"
2. Paste `instructions.md` เป็น Instructions
3. Upload ไฟล์จาก `knowledge/`

### ChatGPT / Codex CLI
```bash
cp -r skills/chatgpt/tor-procurement .codex/skills/
```

### Gemini NotebookLM
1. สร้าง Notebook ใหม่
2. Upload ไฟล์ทั้ง 6 จาก `sources/`
3. (Optional) ตั้ง Notebook guide จาก `notebook-instruction.md`

### Hermes Desktop / CLI
```bash
cp -r skills/hermes-agent/tor-procurement ~/.hermes/skills/government/
```

---

## Format Comparison

| Feature | Claude | ChatGPT | Gemini/NotebookLM | Hermes |
|---------|--------|---------|-------------------|--------|
| Main file | SKILL.md | SKILL.md + instructions.md | sources/*.md | SKILL.md |
| Frontmatter | name, description | name, description | N/A | name, desc, version, metadata |
| Knowledge | references/ + assets/ | knowledge/ folder | Upload as sources | references/ |
| Config | N/A | gpt-config.json | notebook-instruction | metadata.hermes.config |
| Auto-discovery | Yes (skill name match) | Yes (skill name) | No (manual) | Yes (slash command) |
| Open standard | Agent Skills | Agent Skills | Proprietary | Agent Skills (extended) |

---

## เกี่ยวกับ Agent Skills Open Standard

**SKILL.md** เป็นมาตรฐานเปิดที่ใช้ร่วมกันระหว่าง Claude Code, OpenAI Codex, Hermes Agent, Cursor และเครื่องมืออื่นอีกกว่า 30 ตัว โดยมีโครงสร้าง:

```markdown
---
name: skill-name
description: When to use this skill
---

# Skill Title
Instructions for the AI agent...
```

Skills ทุก folder ในโปรเจกต์นี้ใช้รูปแบบนี้เป็นพื้นฐาน โดยแต่ละแพลตฟอร์มจะมีไฟล์เสริมเฉพาะของตัวเอง

---

## Tips

- **Context window จำกัด**: ถ้าแพลตฟอร์มรองรับ context น้อย ให้ upload เฉพาะไฟล์สำคัญก่อน (ลำดับ priority ตามเลขนำหน้าในโฟลเดอร์ sources/)
- **ภาษาราชการ**: ทุกแพลตฟอร์มใช้คู่มือภาษาเดียวกัน (tor_writing_guide) — ช่วยให้ output สม่ำเสมอ
- **Update knowledge**: เมื่อกฎหมายเปลี่ยน ให้แก้ไขที่ `documents/knowledge-base/` แล้ว copy ไปอัพเดตแต่ละแพลตฟอร์ม
- **ทดสอบ**: ทดลองร่าง TOR ง่ายๆ (เช่น "ซื้อคอมพิวเตอร์ 5 เครื่อง วงเงิน 200,000") เพื่อตรวจว่า skill ทำงานถูกต้อง
