# Hermes Agent / Hermes Desktop Skill

## Format: SKILL.md (Agent Skills Open Standard)

Hermes Agent by Nous Research uses the same SKILL.md open standard as Claude Code and OpenAI Codex, but with extended YAML frontmatter for platform-specific features (tags, config settings, platform restrictions).

## Directory Structure

```
hermes-agent/
└── tor-procurement/
    ├── SKILL.md              # Main skill file (extended frontmatter)
    └── references/           # Supporting reference files
        ├── method_selection.md
        ├── template_selection.md
        ├── document_checklist.md
        └── tor_writing_guide.md
```

## Installation

### Hermes Desktop / CLI
```bash
# Copy to personal skills directory
cp -r tor-procurement ~/.hermes/skills/government/tor-procurement

# Or install from local path
hermes skills install ./tor-procurement
```

### Verify Installation
```bash
hermes skills list
# Should show: tor-procurement - Draft and review Thai government procurement TOR...
```

### Use as Slash Command
```
/tor-procurement Draft a TOR for IT system development, budget 3M THB
```

## Configuration

The skill declares config settings in its frontmatter. After installation, configure via:
```bash
hermes config set skills.config.tor.language thai-formal
hermes config set skills.config.tor.default_penalty_rate 0.10
```

## Compatibility

This skill is compatible with:
- Hermes Agent (CLI + Desktop) - Full support including slash commands
- Claude Code - Works as-is (ignores Hermes-specific metadata)
- OpenAI Codex - Works as-is via SKILL.md standard
- Any tool supporting the Agent Skills open standard

## Usage
- Draft: "ร่าง TOR จ้างพัฒนาระบบ HRM วงเงิน 3 ล้าน"
- Review: "ตรวจสอบ TOR นี้" + paste TOR content
- Query: "/tor-procurement วงเงิน 2 ล้าน ใช้วิธีไหน?"

## Notes
- Platform: works on macOS, Linux, and Windows (via WSL2 for Hermes CLI)
- The skill uses `references/` for supporting documents (Hermes reads these when the skill is loaded)
- No external dependencies required
- No environment variables needed
