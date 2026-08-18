# Claude Code / Claude Projects Skill

## Format: Agent Skills (SKILL.md)

This folder follows the [Agent Skills open standard](https://agentskills.io) used by Claude Code, Claude Projects, and other compatible tools.

## Directory Structure

```
claude/
└── tor-procurement/
    ├── SKILL.md              # Main skill file (required)
    ├── references/           # Legal references and decision rules
    │   ├── tor_reference_complete.md
    │   ├── method_selection.json
    │   ├── template_selection.json
    │   └── document_checklist.json
    └── assets/               # Templates and writing guides
        ├── tor_writing_guide.md
        └── tor_base_template.md
```

## Installation

### Claude Code (CLI)
```bash
# Copy to personal skills
cp -r tor-procurement ~/.claude/skills/

# Or use as project skill
cp -r tor-procurement .claude/skills/
```

### Claude Projects (Web)
1. Create a new Project named "TOR จัดซื้อจัดจ้างภาครัฐ"
2. Set Project Instructions: copy content from SKILL.md
3. Upload all files from `references/` and `assets/` as knowledge files

### Claude Cowork (Team)
Same as Claude Projects, but create in a shared workspace so team members can access the same knowledge and instructions.

## Usage
- Draft: "ร่าง TOR จ้างพัฒนาระบบ HRM วงเงิน 3 ล้าน สำหรับกรมสรรพากร"
- Review: "ตรวจสอบ TOR นี้" + paste/upload TOR document
