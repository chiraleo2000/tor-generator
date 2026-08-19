# Implementation Plan: Agent TOR Drafting

## Overview

This plan implements the agent-based TOR drafting workflow as an alternative to the existing 8-step wizard. The implementation builds bottom-up: database schema → core services → LangGraph agent graph → API endpoints → KB chat → export integration → tests. All work is in Python (FastAPI + LangGraph + SQLAlchemy) and reuses existing infrastructure (ProviderFactory, Rule Engine, hybrid RAG, section agents, export service).

## Tasks

- [x] 1. Database schema and models
  - [x] 1.1 Create Alembic migration for `agent_sessions` table and `workflow_mode` column on `projects`
    - Add `agent_sessions` table with columns: id (UUID PK), project_id (FK), user_id (FK), phase (VARCHAR 30), slot_map (JSONB), gap_iteration (INT), graph_state (JSONB), messages (JSONB), warnings (JSONB), created_at, updated_at, expires_at
    - Add indexes: `idx_agent_sessions_user(user_id, phase)`, `idx_agent_sessions_project(project_id)`
    - Add `workflow_mode VARCHAR(20) DEFAULT 'wizard'` column to `projects` table
    - _Requirements: 6.10, 4.1, 4.2_

  - [x] 1.2 Create Alembic migration for `kb_chat_sessions` table
    - Add `kb_chat_sessions` table with columns: id (UUID PK), user_id (FK), history (JSONB), created_at, last_active_at
    - Add index: `idx_kb_chat_user(user_id)`
    - _Requirements: 9.6, 9.7_

  - [x] 1.3 Create SQLAlchemy model `AgentSession` in `app/models/agent_session.py`
    - Map to `agent_sessions` table
    - Include relationship to Project and User
    - _Requirements: 6.10_

  - [x] 1.4 Create SQLAlchemy model `KBChatSession` in `app/models/kb_chat_session.py`
    - Map to `kb_chat_sessions` table
    - Include relationship to User
    - _Requirements: 9.6, 9.7_

  - [x] 1.5 Register new models in `app/models/__init__.py` and update Project model with `workflow_mode` field
    - _Requirements: 6.10_

- [x] 2. Checkpoint — Ensure migrations run and models are importable
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Session cache service
  - [x] 3.1 Create `app/services/session_cache.py` with Redis-backed caching
    - Implement `SessionCacheService` class with methods: `get_extraction(project_id, content_hash)`, `set_extraction(...)`, `get_slot_map(project_id)`, `set_slot_map(...)`, `get_draft(project_id, section_key)`, `set_draft(...)`, `get_session_state(session_id)`, `set_session_state(...)`, `invalidate_project(project_id)`
    - Key patterns: `agent:extract:{project_id}:{content_hash}`, `agent:slotmap:{project_id}`, `agent:draft:{project_id}:{section_key}`, `agent:session:{session_id}`
    - Configurable TTL per category (extraction=24h, mapping=24h, draft=48h) with min 1h, max 168h bounds
    - Graceful failure: log and proceed without blocking on write errors
    - Use existing Redis from `app/infra.py`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

  - [x]* 3.2 Write property test for cache key determinism
    - **Property 6: Cache key determinism**
    - **Validates: Requirements 4.1, 4.4**

- [x] 4. Intake ingestion service (enhanced)
  - [x] 4.1 Create `app/services/agent_intake_service.py` with `IntakeIngestionService` class
    - Implement `process_batch(project_id, files, free_text, storage_backend)` method
    - Validate file count (≤ 20 per request) and per-file size (≤ 50 MB)
    - Extract text from PDF, DOCX, PPTX, TXT preserving structure (headings, lists, tables)
    - Store raw files in MinIO/local via existing storage abstraction
    - Compute content_hash per file for cache-hit detection
    - Concatenate all text respecting 200k char chunking with document boundaries
    - Return per-file status + total extracted content
    - Total batch timeout: 600 seconds
    - Reuse existing extraction logic from `app/services/intake_service.py` where applicable
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

  - [x]* 4.2 Write property test for ingestion file count validation
    - **Property 9: Ingestion file count validation**
    - **Validates: Requirements 1.1, 1.2**

- [x] 5. Section mapper service
  - [x] 5.1 Create `app/services/section_mapper.py` with `SectionMapper` class
    - Implement `map_content(content, project_metadata)` → `MappingResult`
    - Single-pass LLM analysis producing slot_map for all 27 TOR_Slots (s1–s13, s4.1–s4.14)
    - Each slot classified as "filled", "gap", or "reference_only"
    - Extract source attribution per slot (document name, page/section reference)
    - Timeout: 90s, retry once at 50% content on failure, then return partial
    - Use ProviderFactory for LLM access
    - Reuse ANALYZE_PROMPT pattern from existing `intake_service.py`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x] 5.2 Implement `incremental_update(answer_text, current_slot_map, context_questions)` in `SectionMapper`
    - Classify user answer to target slots without re-analyzing all content
    - Support multi-slot distribution from a single answer
    - Append vs. replace logic: append by default, replace on contradiction/override
    - Return updated slot entries + list of affected slot keys
    - 5-second timeout for classification
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 3.5_

  - [x]* 5.3 Write property test for slot map coverage exhaustiveness
    - **Property 4: Slot map coverage is exhaustive**
    - **Validates: Requirements 2.1, 2.2**

  - [x]* 5.4 Write property test for incremental update preserving unaffected slots
    - **Property 5: Incremental update preserves unaffected slots**
    - **Validates: Requirements 4.3, 11.1**

- [x] 6. Gap detector service
  - [x] 6.1 Create `app/services/gap_detector.py` with `GapDetector` class
    - Implement `detect_gaps(slot_map)` → `list[GapInfo]` (pure function)
    - Scan for Fact_Required_Slots with status != "filled" (critical) and other gaps (non-critical)
    - Sort output: fact-required gaps first, then non-critical
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 6.2 Implement `generate_questions(gaps, project_context)` in `GapDetector`
    - Generate Thai-language follow-up questions (one per gap)
    - Max 5 questions per round, grouped by TOR section
    - Each question references section name and states what's missing
    - 30-second timeout, return generic questions on failure
    - _Requirements: 3.2, 3.4_

  - [x]* 6.3 Write property test for gap detection priority ordering
    - **Property 2: Gap detection prioritizes fact-required slots**
    - **Validates: Requirements 3.3**

  - [x]* 6.4 Write property test for gap question batch size bound
    - **Property 3: Gap question batch size is bounded**
    - **Validates: Requirements 3.4**

- [x] 7. Coverage scoring utilities
  - [x] 7.1 Create coverage score and readiness helpers in `app/services/coverage.py`
    - Implement `compute_readiness_score(slot_map)` → float (0.0–1.0)
    - Implement `compute_ready(slot_map)` → bool (True iff readiness_score == 1.0)
    - Implement `build_coverage_map(slot_map)` → list of slot status dicts with labels, criticality
    - Logic: readiness_score = count(fact-required slots with "filled" + non-empty) / 6
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x]* 7.2 Write property test for coverage readiness score
    - **Property 1: Coverage readiness score is ratio of filled fact-required slots**
    - **Validates: Requirements 10.4**

- [x] 8. Checkpoint — Ensure all service-layer tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Agent workflow state and graph
  - [x] 9.1 Create `app/orchestrator/agent_state.py` with `AgentWorkflowState` TypedDict
    - Define all state fields as specified in design: session_id, project_id, user_id, phase, intake_files, intake_texts, total_chars, slot_map, coverage_map, readiness_score, ready, gap_questions, gap_iteration, max_gap_iterations, user_confirmed, section_drafts, sections_pending, draft_quality_scores, overall_quality_score, validation_findings, correction_attempts, mandatory_review_sections, sections_acknowledged, export_docx_url, export_pdf_url, agent_timeout_seconds, draft_timeout_seconds, ingestion_timeout_seconds, deployment_mode, error, warnings, messages
    - _Requirements: 6.11_

  - [x] 9.2 Create `app/orchestrator/agent_nodes.py` with graph node implementations
    - Implement `ingest_node(state)`: invoke IntakeIngestionService, update state with intake results
    - Implement `map_sections_node(state)`: invoke SectionMapper.map_content, update slot_map
    - Implement `detect_gaps_node(state)`: invoke GapDetector.detect_gaps + generate_questions
    - Implement `fill_slot_node(state)`: invoke SectionMapper.incremental_update from user answer
    - Implement `confirm_node(state)`: validate user_confirmed flag, check readiness
    - Each node handles timeouts and sets error state on failure
    - _Requirements: 2.1, 3.1, 6.3, 6.5, 6.6, 5.5_

  - [x] 9.3 Implement `draft_all_node(state)` in `agent_nodes.py`
    - Generate all 13 TOR sections using existing section agents via `get_agent_for_section`
    - Retrieve RAG context per section via `hybrid_retrieve`
    - Track timing against 900s total timeout (return partial on timeout)
    - Collect per-section quality scores
    - _Requirements: 7.1, 7.2, 7.8, 8.1, 8.2, 12.4, 12.5_

  - [x] 9.4 Implement `validate_draft_node(state)` in `agent_nodes.py`
    - Invoke existing Rule Engine on complete generated TOR
    - Auto-correct sections with severity "error" (max 3 attempts per section)
    - Track best-scoring draft across retries
    - Compute overall_quality_score as mean of per-section scores
    - _Requirements: 7.2, 7.3, 7.4, 7.5_

  - [x] 9.5 Implement `human_review_node(state)` and `export_node(state)` in `agent_nodes.py`
    - `human_review_node`: flag mandatory review sections (s3, s6, s8, s10, s13), present draft with findings
    - `export_node`: invoke existing Export_Service for DOCX/PDF generation, store URLs in state
    - _Requirements: 7.6, 7.10, 7.11_

  - [x] 9.6 Create `app/orchestrator/agent_graph.py` with graph topology and routing
    - Implement `build_agent_workflow_graph()` → StateGraph
    - Add all nodes: ingest, map_sections, detect_gaps, fill_slot, confirm, draft_all, validate_draft, human_review, export, handle_error
    - Implement routing functions: `route_after_gaps` (confirm vs fill_slot), `route_after_confirm` (draft_all vs fill_slot), `route_after_validation` (human_review vs draft_all retry), `route_after_review` (export vs draft_all)
    - Configure interrupt points for human-in-the-loop (fill_slot, confirm, human_review)
    - Enforce max 20 gap iterations (Req 12.3)
    - _Requirements: 6.11, 12.3_

  - [x]* 9.7 Write property test for quality score bounds
    - **Property 8: Quality score bounds**
    - **Validates: Requirements 7.5**

  - [x]* 9.8 Write property test for payment installment percentages
    - **Property 7: Payment installment percentages sum to 100**
    - **Validates: Requirements 7.2**

- [x] 10. Checkpoint — Ensure agent graph compiles and routing logic is correct
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Pydantic schemas for agent API
  - [x] 11.1 Create `app/schemas/agent.py` with request/response schemas
    - `CreateSessionRequest`: initial docs/text upload
    - `CreateSessionResponse`: session_id, project_id, phase
    - `AnswerRequest`: user answer text
    - `AnswerResponse`: updated coverage, new questions, affected slots
    - `ConfirmRequest`: user_confirmed boolean
    - `CoverageResponse`: coverage_map, readiness_score, ready
    - `DraftResponse`: section_drafts, quality_scores, overall_quality_score, validation_findings
    - `ReviewRequest`: human_approved, human_feedback
    - `ExportResponse`: docx_url, pdf_url
    - `StatusResponse`: phase, progress info
    - _Requirements: 6.1, 6.5, 6.7, 10.1, 10.3, 10.4_

  - [x] 11.2 Create `app/schemas/kb_chat.py` with KB chat schemas
    - `CreateKBChatSessionResponse`: session_id
    - `KBChatMessageRequest`: message (max 1000 chars)
    - `KBChatMessageResponse`: answer, citations, no_results flag
    - `KBChatHistoryResponse`: messages list
    - _Requirements: 9.1, 9.4, 9.5_

- [x] 12. Agent API endpoints
  - [x] 12.1 Create `app/api/v1/endpoints/agent.py` with session management endpoints
    - `POST /api/v1/agent/sessions` — Create session, upload initial docs/text
    - `POST /api/v1/agent/sessions/{id}/ingest` — Add more documents
    - `GET /api/v1/agent/sessions/{id}/status` — Get workflow phase + progress
    - `DELETE /api/v1/agent/sessions/{id}` — Cancel/archive session
    - All endpoints require authentication, validate session ownership
    - _Requirements: 6.1, 6.2, 6.10_

  - [x] 12.2 Implement coverage and gap-filling endpoints in `agent.py`
    - `GET /api/v1/agent/sessions/{id}/coverage` — Return Coverage_Map with readiness_score
    - `POST /api/v1/agent/sessions/{id}/answer` — Submit answer, resume graph at fill_slot
    - _Requirements: 6.5, 6.6, 10.1, 10.3, 11.1, 11.6_

  - [x] 12.3 Implement confirmation, draft, review, and export endpoints in `agent.py`
    - `POST /api/v1/agent/sessions/{id}/confirm` — Confirm slots, proceed to drafting
    - `GET /api/v1/agent/sessions/{id}/draft` — Get draft content + scores
    - `POST /api/v1/agent/sessions/{id}/review` — Submit human review decision
    - `GET /api/v1/agent/sessions/{id}/export` — Get export download URLs
    - Prevent export until mandatory review sections are acknowledged
    - _Requirements: 6.7, 6.8, 7.4, 7.6, 7.10_

  - [x] 12.4 Register agent router in `app/api/v1/__init__.py` or main app
    - _Requirements: 6.1_

- [x] 13. Knowledge Base chat service and endpoints
  - [x] 13.1 Create `app/services/kb_chat_service.py` with `KnowledgeChatService` class
    - Implement `answer(session_id, user_id, message, history)` → `ChatResponse`
    - Retrieve chunks via `hybrid_retrieve(search_scope="both")`
    - Relevance threshold: score >= 0.5 for at least 1 chunk
    - If no relevant chunks: return "ไม่พบข้อมูลที่เกี่ยวข้อง" without LLM synthesis
    - If relevant: generate answer with citations (document name, page, section)
    - Respect access controls: user sees only global + own docs
    - Support on_prem mode with local LLM
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.8, 9.9_

  - [x] 13.2 Implement session management in `KnowledgeChatService`
    - Create new session on first message
    - Maintain up to 20 message pairs (evict oldest on overflow)
    - Session timeout: 30 minutes of inactivity
    - Store in `kb_chat_sessions` table + Redis cache (TTL 30min)
    - _Requirements: 9.6, 9.7_

  - [x] 13.3 Create `app/api/v1/endpoints/kb_chat.py` with KB chat endpoints
    - `POST /api/v1/kb-chat/sessions` — Create KB chat session
    - `POST /api/v1/kb-chat/sessions/{id}/message` — Send message
    - `GET /api/v1/kb-chat/sessions/{id}/history` — Get chat history
    - Validate message length (≤ 1000 chars), require authentication
    - _Requirements: 9.1, 9.6, 9.7_

  - [x] 13.4 Register KB chat router in app
    - _Requirements: 9.1_

  - [x]* 13.5 Write property test for session message history bound
    - **Property 10: Session message history bounded**
    - **Validates: Requirements 9.6**

- [x] 14. Checkpoint — Ensure API endpoints respond correctly with mocked services
  - Ensure all tests pass, ask the user if questions arise.

- [x] 15. Full draft generator integration
  - [x] 15.1 Create `app/services/full_draft_generator.py` with `FullDraftGenerator` class
    - Implement `generate_all(slot_map, project_metadata, deployment_mode)` → `DraftResult`
    - For each section s1–s13: retrieve RAG context, invoke section agent, collect draft
    - Include warnings for unfilled Fact_Required_Slots
    - Track timing against 900s total timeout; return partial on timeout
    - Implement `auto_correct(section_key, draft, findings, slot_map, attempt)` for re-draft with feedback
    - Max 3 corrections per section
    - All output in formal Thai register (ภาษาราชการ)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.7, 7.8, 7.9, 8.1, 8.2, 8.3, 8.4, 8.5, 12.4, 12.5_

  - [x] 15.2 Wire FullDraftGenerator into `draft_all_node` in agent_nodes.py
    - Connect to the existing node implementation
    - Ensure section_drafts and scores flow back into agent state
    - _Requirements: 7.1_

- [x] 16. Export pipeline integration
  - [x] 16.1 Wire export in `export_node` to existing Export_Service
    - Generate DOCX and PDF from `section_drafts` state
    - Apply standard TOR template (agency header, page numbering "page X of Y", section numbering)
    - Store in MinIO, generate presigned URLs
    - Preserve Thai character rendering and heading hierarchy
    - _Requirements: 7.10, 7.11_

- [x] 17. Checkpoint — Ensure end-to-end agent workflow runs with mocked LLM
  - Ensure all tests pass, ask the user if questions arise.

- [x] 18. Integration tests
  - [x]* 18.1 Write integration test for full agent graph execution with mocked LLM
    - Test state transitions: ingest → map → gap_fill → confirm → draft → validate → review → export
    - Verify all nodes produce expected state mutations
    - _Requirements: 6.11_

  - [x]* 18.2 Write integration test for Redis cache hit/miss behavior
    - Test extraction skip on hash match
    - Test TTL expiry triggers re-analysis
    - Test cache write failure does not block workflow
    - _Requirements: 4.1, 4.4, 4.5, 4.7_

  - [x]* 18.3 Write integration test for RAG degradation paths
    - Test draft proceeds when RAG returns empty (no relevant chunks)
    - Test draft proceeds when RAG errors (connection failure)
    - Verify warnings are appended to output
    - _Requirements: 8.3, 8.4_

  - [x]* 18.4 Write integration test for KB chat with access control
    - Test user can access global + own docs
    - Test user cannot access other users' docs
    - Test relevance threshold rejection
    - _Requirements: 9.5, 9.8_

- [x] 19. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Existing infrastructure (ProviderFactory, Rule Engine, hybrid RAG, section agents, Export_Service, storage) is reused — not recreated
- The agent workflow coexists with the existing wizard flow (wizard endpoints remain intact)
- All LLM calls go through ProviderFactory; deployment_mode determines cloud vs. local provider selection

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4"] },
    { "id": 2, "tasks": ["1.5"] },
    { "id": 3, "tasks": ["3.1", "7.1"] },
    { "id": 4, "tasks": ["3.2", "4.1", "6.1", "7.2"] },
    { "id": 5, "tasks": ["4.2", "5.1", "6.2"] },
    { "id": 6, "tasks": ["5.2", "5.3", "6.3", "6.4"] },
    { "id": 7, "tasks": ["5.4", "9.1"] },
    { "id": 8, "tasks": ["9.2", "9.3"] },
    { "id": 9, "tasks": ["9.4", "9.5"] },
    { "id": 10, "tasks": ["9.6"] },
    { "id": 11, "tasks": ["9.7", "9.8", "11.1", "11.2"] },
    { "id": 12, "tasks": ["12.1", "13.1"] },
    { "id": 13, "tasks": ["12.2", "12.3", "13.2"] },
    { "id": 14, "tasks": ["12.4", "13.3"] },
    { "id": 15, "tasks": ["13.4", "13.5", "15.1"] },
    { "id": 16, "tasks": ["15.2", "16.1"] },
    { "id": 17, "tasks": ["18.1", "18.2", "18.3", "18.4"] }
  ]
}
```
