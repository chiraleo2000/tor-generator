# Google Gemini / NotebookLM Setup

## Format: Sources + System Instructions

NotebookLM uses uploaded **sources** (documents, PDFs, text, URLs) that Gemini grounds its responses in. There is no SKILL.md equivalent - instead you upload documents as knowledge sources and optionally set a notebook-level instruction.

## Directory Structure

```
gemini-notebooklm/
├── README.md                  # This file (setup guide)
├── notebook-instruction.md    # Paste into NotebookLM "Notebook guide"
├── sources/                   # Upload these as notebook sources
│   ├── 01_tor_reference_complete.md    # Legal framework (Priority 1)
│   ├── 02_tor_writing_guide.md         # Language & vocabulary (Priority 2)
│   ├── 03_method_selection.md          # Decision rules (Priority 3)
│   ├── 04_document_checklist.md        # Review checklist (Priority 4)
│   ├── 05_template_selection.md        # Template matrix (Priority 5)
│   └── 06_tor_base_template.md         # Base template (Priority 6)
└── gemini-chat-instruction.md # For Gemini Chat/Advanced (system instruction)
```

## NotebookLM Setup

### Step 1: Create Notebook
1. Go to [notebooklm.google.com](https://notebooklm.google.com)
2. Click "New Notebook"
3. Name: "TOR จัดซื้อจัดจ้างภาครัฐ"

### Step 2: Upload Sources
Upload all files from the `sources/` folder as sources:
- Click "+" to add source
- Select "Upload" > choose files from `sources/` folder
- All 6 files (each under 500,000 words limit)

### Step 3: Set Notebook Guide (Optional)
1. Click the notebook settings icon
2. Paste content from `notebook-instruction.md` into the "Notebook guide" field
3. This tells Gemini how to behave when answering from these sources

### Step 4: Use
- Ask questions about TOR drafting, procurement law, etc.
- NotebookLM grounds all answers in the uploaded sources
- Generate Audio Overview for team training (podcast-style)

## Gemini Chat / Gemini Advanced Setup

For using with Gemini Chat (not NotebookLM):
1. Open Gemini at [gemini.google.com](https://gemini.google.com)
2. Create a new "Gem" (custom chatbot)
3. Paste `gemini-chat-instruction.md` as the instruction
4. Upload files from `sources/` as knowledge

## Tips
- NotebookLM works best with clear, structured text documents
- Sources are in Markdown (.md) format - NotebookLM handles these well
- Files are numbered by priority for limited-source scenarios
- Use the Audio Overview feature to create training podcasts about procurement
- Share the notebook with team members for collaborative access

## Limitations
- Max 50 sources per notebook (Free), 300 (Plus)
- Max 500,000 words per source
- No real-time web search (grounded only in uploaded sources)
- Cannot execute code or run scripts
