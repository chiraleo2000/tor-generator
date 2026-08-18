# ChatGPT Custom GPT / Projects / Codex Skill

## Formats Included

This folder provides **three compatible formats** for the ChatGPT ecosystem:

| Format | Use Case | File |
|--------|----------|------|
| Custom GPT config | ChatGPT Plus/Team GPT Builder | `gpt-config.json` + `instructions.md` |
| SKILL.md | OpenAI Codex CLI / ChatGPT Skills | `SKILL.md` |
| Knowledge files | Upload to GPT or Project | `knowledge/` folder |

## Directory Structure

```
chatgpt/
└── tor-procurement/
    ├── SKILL.md              # Codex/Skills format (open standard)
    ├── instructions.md       # GPT Builder instructions (paste into GPT)
    ├── gpt-config.json       # GPT configuration reference
    └── knowledge/            # Upload these as knowledge files
        ├── tor_writing_guide.md
        ├── tor_reference_complete.md
        ├── method_selection.json
        ├── template_selection.json
        ├── document_checklist.json
        └── tor_base_template.md
```

## Installation

### Option 1: Custom GPT (ChatGPT Plus/Team/Enterprise)
1. Go to ChatGPT > Explore GPTs > Create a GPT
2. Name: "TOR Advisor - ที่ปรึกษาร่าง TOR จัดซื้อจัดจ้างภาครัฐ"
3. Instructions: copy content from `instructions.md`
4. Upload all files from `knowledge/` folder
5. Enable Code Interpreter
6. Add conversation starters from `gpt-config.json`

### Option 2: ChatGPT Projects
1. Create a new Project named "TOR จัดซื้อจัดจ้าง"
2. Set Custom Instructions from `instructions.md`
3. Upload all files from `knowledge/` as project files

### Option 3: OpenAI Codex CLI
```bash
# Copy SKILL.md to your project
cp -r tor-procurement/.  .codex/skills/tor-procurement/
```

### Option 4: ChatGPT Skills (SKILL.md)
Upload the `SKILL.md` file directly as a skill in ChatGPT settings.

## Usage
- Draft: "ร่าง TOR จ้างพัฒนาระบบ HRM วงเงิน 3 ล้าน"
- Review: "ตรวจสอบ TOR นี้" + paste/upload TOR document
- Query: "วงเงิน 800,000 ต้องใช้วิธีอะไร?"
