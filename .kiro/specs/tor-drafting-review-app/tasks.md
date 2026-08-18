# Implementation Plan: TOR Drafting and Review Application

## Overview

This implementation plan breaks down the TOR Drafting and Review Application into incremental, dependency-ordered tasks. The system uses a 6-layer architecture: Next.js 14 frontend, FastAPI backend, LangGraph AI orchestration, LLM/RAG services, Rule Engine guardrail, and PostgreSQL+pgvector/Redis/MinIO persistence. Tasks are grouped by major component and ordered so each task builds on previously completed work.

## Tasks

- [x] 1. Infrastructure Setup (Docker Compose & Project Scaffolding)
  - [x] 1.1 Create monorepo directory structure and root configuration files
    - Create top-level directories: `frontend/`, `backend/`, `docker/`
    - Create root `.env.example` with all environment variables (DEPLOYMENT_MODE, DB credentials, Redis, MinIO, API keys, ports)
    - Create `.gitignore` for Python, Node.js, Docker, and IDE artifacts
    - _Requirements: 1.1, 1.6_

  - [x] 1.2 Create Docker Compose configuration with all services
    - Define services: frontend, backend, postgres (pgvector/pgvector:pg15), redis (redis:7-alpine), minio (minio/minio:latest), qdrant (optional profile)
    - Configure health checks (30s interval, 3 retries, 40s start period) for each service
    - Set up named volumes (pg_data, minio_data, qdrant_data) and shared bridge network (tor_network)
    - Configure `depends_on` with `condition: service_healthy` for proper startup ordering
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8, 1.9_

  - [x] 1.3 Create Backend Dockerfile
    - Multi-stage build: Python 3.11 base, install system deps (Tesseract OCR, WeasyPrint deps, Thai fonts)
    - Install Python dependencies from requirements.txt / pyproject.toml
    - Set up non-root user, expose port 4000, health check endpoint
    - _Requirements: 1.2_

  - [x] 1.4 Create Frontend Dockerfile
    - Multi-stage build: Node 20 base, install dependencies, build Next.js, production image with standalone output
    - Expose port 3000, set NEXT_PUBLIC_API_URL environment variable
    - _Requirements: 1.2_

- [x] 2. Database Layer (PostgreSQL + pgvector Schema & Migrations)
  - [x] 2.1 Set up backend Python project with FastAPI, SQLAlchemy, and Alembic
    - Create `backend/pyproject.toml` with dependencies: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, python-jose, passlib[bcrypt], redis, minio, python-multipart
    - Initialize Alembic with async PostgreSQL configuration
    - Create `backend/app/config.py` with Pydantic Settings loading from environment
    - _Requirements: 13.1, 13.4_

  - [x] 2.2 Create SQLAlchemy ORM models for all entities
    - Implement models: User, Project, ProjectVersion, TORSection, Template, TemplateVersion, KnowledgeBaseDocument, KBChunk (with pgvector Vector column), Suggestion, AuditLog, UploadedFile
    - Define relationships, indexes, and constraints as specified in the ERD
    - Use UUID primary keys, proper column types (JSONB, Vector(1536), BigInteger for budget)
    - _Requirements: 13.1, 13.2_

  - [x] 2.3 Create initial Alembic migration with full schema
    - Generate migration from ORM models including all tables, indexes, and the pgvector extension
    - Create performance indexes: idx_projects_owner_status, idx_tor_sections_project, idx_kb_chunks_embedding (HNSW), etc.
    - Add database collation configuration for Thai (th_TH.UTF-8)
    - _Requirements: 13.1, 13.2, 16.6_

  - [x] 2.4 Write unit tests for ORM models and migration
    - Test model instantiation, relationship loading, constraint enforcement
    - Test migration up/down operations
    - _Requirements: 13.2_

- [x] 3. Backend Core (FastAPI Application Setup)
  - [x] 3.1 Create FastAPI application entry point with middleware stack
    - Implement `backend/app/main.py`: FastAPI app initialization, lifespan handler (DB connection pool, Redis client, MinIO client)
    - Add middleware: CORS (configurable frontend origin), request ID injection, request logging
    - Create API router structure under `app/api/v1/`
    - _Requirements: 15.2, 15.6_

  - [x] 3.2 Implement health check endpoints
    - GET `/health`: Check all dependencies (PostgreSQL, Redis, MinIO) and return aggregate status
    - GET `/health/ready`: Readiness probe (DB + Redis connected)
    - Return structured response with individual service statuses
    - _Requirements: 1.5, 1.7_

  - [x] 3.3 Implement standardized error response envelope and exception handlers
    - Create error response schema: `{ok, error: {code, message, field, details}, meta: {requestId, timestamp}}`
    - Register FastAPI exception handlers for validation errors, auth errors, rate limits, timeouts
    - Return Thai-language error messages for user-facing validation errors
    - _Requirements: 15.2, 16.1_

  - [x] 3.4 Implement database session management and connection pooling
    - Create async SQLAlchemy session factory with configurable pool size (default 20)
    - Implement dependency injection for DB sessions in FastAPI routes
    - Run pending Alembic migrations on application startup
    - _Requirements: 13.4, 13.5_

- [x] 4. Authentication & Security
  - [x] 4.1 Implement user registration and password hashing
    - Create `app/services/auth_service.py`: register user, validate password policy (min 8 chars, uppercase, lowercase, digit, special)
    - Implement bcrypt hashing with 12 salt rounds
    - Create Pydantic schemas for register request/response
    - POST `/api/v1/auth/register` endpoint
    - _Requirements: 9.1, 9.2, 9.8_

  - [x] 4.2 Implement JWT authentication (login, logout, token validation)
    - POST `/api/v1/auth/login`: Validate credentials, generate JWT (HS256, 24h expiry), store session in Redis
    - POST `/api/v1/auth/logout`: Invalidate session in Redis
    - GET `/api/v1/auth/me`: Return current user profile from token
    - Create FastAPI dependency for JWT validation (`get_current_user`)
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 4.3 Implement role-based access control (RBAC) middleware
    - Create role enum: officer, reviewer, admin
    - Create FastAPI dependency `require_role(roles: list)` that checks user role
    - Enforce project ownership at data access points (user can only access own projects unless admin/reviewer)
    - _Requirements: 9.3, 9.7_

  - [x] 4.4 Implement rate limiting with Redis
    - Create rate limiter middleware using Redis sliding window (100 req/min per user for API, 10 uploads/min for files)
    - Return HTTP 429 with `Retry-After` header when exceeded
    - _Requirements: 15.1, 15.5, 14.6_

  - [x] 4.5 Implement audit logging service
    - Create audit log service that records: login, logout, login_failed, create, update, delete, export, review events
    - Store user_id, action, resource_type, resource_id, IP address, timestamp, details (JSONB)
    - _Requirements: 15.7, 9.7_

  - [x] 4.6 Write property test for authentication token isolation (Property 11)
    - **Property 11: Authentication Token Isolation**
    - Verify JWT for User A never grants access to User B's projects
    - **Validates: Requirements 9.3, 9.7**

  - [x] 4.7 Write property test for rate limiting enforcement (Property 13)
    - **Property 13: Rate Limiting Enforcement**
    - Verify requests exceeding configured limit receive HTTP 429
    - **Validates: Requirements 15.1, 15.5**

- [x] 5. Checkpoint - Infrastructure and Core Backend
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Provider Factory (Strategy Pattern)
  - [x] 6.1 Define abstract interfaces for LLM, Embedding, and VectorStore providers
    - Create `backend/app/providers/base.py` with abstract classes: `LLMProvider` (invoke, stream), `EmbeddingProvider` (embed_query, embed_documents), `VectorStoreProvider` (upsert, search, delete)
    - Define response types: LLMResponse, SearchResult
    - _Requirements: 2.1, 2.4_

  - [x] 6.2 Implement Claude Sonnet LLM provider (cloud mode)
    - Create `backend/app/providers/llm/claude_provider.py`: Anthropic API client with prompt caching
    - Implement invoke() and stream() methods
    - Handle timeout (60s default), circuit breaker pattern (5 failures → 30s open)
    - _Requirements: 2.3, 2.7_

  - [x] 6.3 Implement LM Studio local LLM provider (on-prem mode)
    - Create `backend/app/providers/llm/lm_studio_provider.py`: OpenAI-compatible API client pointing to local endpoint
    - Implement invoke() and stream() with configurable base_url and model_name
    - _Requirements: 2.2_

  - [x] 6.4 Implement embedding providers (OpenAI and Qwen3 local)
    - Create `backend/app/providers/embedding/openai_provider.py`: text-embedding-3-small
    - Create `backend/app/providers/embedding/qwen3_provider.py`: local Qwen3-Embedding-4B via OpenAI-compatible API
    - Both implement embed_query() and embed_documents()
    - _Requirements: 2.5_

  - [x] 6.5 Implement vector store providers (pgvector and Qdrant)
    - Create `backend/app/providers/vector_store/pgvector_provider.py`: SQLAlchemy-based with HNSW search
    - Create `backend/app/providers/vector_store/qdrant_provider.py`: Qdrant client
    - Both implement upsert(), search(top_k, filter), delete()
    - _Requirements: 2.6, 3.6_

  - [x] 6.6 Implement ProviderFactory with deployment mode resolution
    - Create `backend/app/providers/factory.py`: Read DEPLOYMENT_MODE env var, instantiate correct providers
    - Handle `on_prem` (all local), `cloud` (all cloud APIs), `hybrid` (per-component via LLM_PROVIDER, EMBEDDING_PROVIDER, VECTOR_STORE_PROVIDER)
    - Reject invalid/missing DEPLOYMENT_MODE with descriptive error
    - Reject missing sub-provider vars in hybrid mode
    - _Requirements: 2.1, 2.4, 2.8, 2.9_

  - [x] 6.7 Write property test for Provider Factory mode resolution (Property 1)
    - **Property 1: Provider Factory Mode Resolution**
    - For any valid DEPLOYMENT_MODE, factory returns functioning providers; for invalid values, rejects with error
    - **Validates: Requirements 2.1, 2.8, 2.9**

- [x] 7. RAG Pipeline (Document Ingestion & Retrieval)
  - [x] 7.1 Implement document text extraction (PDF, DOCX, OCR)
    - Create `backend/app/rag/extraction.py`: Extract text from PDF (PyMuPDF), DOCX (python-docx), plain text
    - Implement OCR fallback for scanned PDFs using Tesseract (Thai + English)
    - Handle OCR timeout (30s default) with partial result return
    - _Requirements: 3.1, 14.1, 14.2, 14.3, 14.5_

  - [x] 7.2 Implement Thai-aware text chunking
    - Create `backend/app/rag/chunking.py`: Thai word segmentation via PyThaiNLP (newmm engine)
    - Chunk text into 500–1000 tokens with 100-token overlap, preserving section boundaries
    - Maintain chunk metadata: document_id, chunk_index, section_label, page_number
    - _Requirements: 3.2, 16.4_

  - [x] 7.3 Implement RAG ingestion pipeline (embed + store)
    - Create `backend/app/rag/ingestion.py`: Orchestrate extraction → chunking → embedding → vector store upsert
    - Handle embedding failures per-chunk (skip failed, log, continue)
    - Update KnowledgeBaseDocument processing status and chunk count
    - _Requirements: 3.3, 3.7, 3.8_

  - [x] 7.4 Implement RAG retrieval with metadata filtering
    - Create `backend/app/rag/retrieval.py`: Embed query → cosine similarity search → return top-K chunks
    - Support metadata filtering (document_type, legal_reference, section_relevance)
    - Handle fewer results than K gracefully
    - _Requirements: 3.4, 3.5, 3.9_

  - [x] 7.5 Write property test for RAG chunking preservation (Property 5)
    - **Property 5: RAG Chunking Preservation**
    - Verify concatenation of chunks (accounting for overlap) reconstructs original text
    - **Validates: Requirements 3.2, 3.3**

  - [x] 7.6 Write property test for embedding round-trip retrieval (Property 6)
    - **Property 6: Embedding Round-Trip Retrieval**
    - Verify stored chunk returns as top-1 result when searching with its own text
    - **Validates: Requirements 3.4, 3.6**

- [x] 8. Rule Engine (Compliance Validation)
  - [x] 8.1 Implement core Rule Engine framework and scoring algorithm
    - Create `backend/app/rule_engine/engine.py`: Validation orchestrator with weighted scoring
    - Implement Quality_Score calculation: legal(40%) + completeness(30%) + consistency(20%) + format(10%)
    - Return structured findings: severity, rule_violated, affected_section, recommended_correction
    - _Requirements: 6.1, 6.6, 6.7_

  - [x] 8.2 Implement legal compliance rules
    - Create `backend/app/rule_engine/rules/legal.py`: พ.ร.บ. 2560 references, required clauses
    - Vendor paid-up capital: `floor(budget / 4)`
    - Penalty rates: 0.01%–0.20% per day, minimum 100 baht/day
    - Brand-lock fairness: flag proprietary names without "or equivalent"
    - _Requirements: 6.1, 6.2, 6.8_

  - [x] 8.3 Implement completeness and consistency rules
    - Create `backend/app/rule_engine/rules/completeness.py`: All 13 sections present, required subsections, minimum content
    - Create `backend/app/rule_engine/rules/consistency.py`: Budget↔Scope, Timeline↔Deliverables, Qualifications↔Complexity
    - Halt scoring if required sections missing, return list
    - _Requirements: 6.5, 6.9_

  - [x] 8.4 Implement payment schedule and timeline validation rules
    - Create `backend/app/rule_engine/rules/payment.py`: Sum = 100%, each 5%–50%
    - Create `backend/app/rule_engine/rules/timeline.py`: Budget > 100M → ≥180 days; Budget < 10M → ≤365 days
    - _Requirements: 6.3, 6.4_

  - [x] 8.5 Implement format adherence rules
    - Create `backend/app/rule_engine/rules/format.py`: Thai government format, numbering, พ.ศ. dates, section ordering
    - _Requirements: 6.6 (format 10% weight)_

  - [x] 8.6 Write property test for Rule Engine quality score determinism (Property 2)
    - **Property 2: Rule Engine Quality Score Determinism**
    - Multiple invocations with same input produce identical scores and findings
    - **Validates: Requirements 6.6, 6.7**

  - [x] 8.7 Write property test for payment schedule percentage invariant (Property 3)
    - **Property 3: Payment Schedule Percentage Invariant**
    - Valid schedules sum to 100%, each installment 5%–50%, penalty 0.01%–0.20%
    - **Validates: Requirements 6.3, 6.8**

  - [x] 8.8 Write property test for vendor capital calculation (Property 4)
    - **Property 4: Vendor Capital Calculation**
    - For any positive budget, capital = floor(budget/4)
    - **Validates: Requirements 6.2**

  - [x] 8.9 Write property test for quality score bounded range (Property 9)
    - **Property 9: Quality Score Bounded Range**
    - Score always 0–100, weighted breakdown sums to total
    - **Validates: Requirements 6.6**

- [~] 9. Checkpoint - Provider Factory, RAG, and Rule Engine
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. LangGraph Orchestrator (AI Agents & Workflow)
  - [x] 10.1 Define LangGraph StateGraph schema and orchestrator skeleton
    - Create `backend/app/orchestrator/state.py`: TORDraftState TypedDict (project_id, user_input, template, target_section, rag_chunks, draft_content, quality_score, validation_findings, retry_count, human_approved, etc.)
    - Create `backend/app/orchestrator/graph.py`: StateGraph with nodes (validate_input, retrieve_context, llm_draft, rule_guardrail, human_review, finalize)
    - Define conditional routing: guardrail pass → human_review, fail → retry/human_review
    - _Requirements: 5.2, 12.2_

  - [x] 10.2 Implement specialized drafting agents (10 agents)
    - Create `backend/app/orchestrator/agents/` directory with agent modules
    - Implement agents for each TOR section: Background, Objectives, Qualifications, Scope, Timeline, Evaluation, Budget, Payment, Penalties/Warranty, Documents
    - Each agent has dedicated system prompt with section-specific guidance in Thai formal register
    - _Requirements: 5.6, 12.1, 16.5_

  - [x] 10.3 Implement orchestrator nodes (validate, retrieve, draft, guardrail, finalize)
    - validate_input: Check required fields, return errors for invalid
    - retrieve_context: Call RAG pipeline, handle retrieval failures gracefully
    - llm_draft: Invoke appropriate agent via ProviderFactory LLM
    - rule_guardrail: Run Rule Engine, decide pass/retry
    - finalize: Persist section, update project state
    - _Requirements: 5.1, 5.2, 5.3, 5.8_

  - [x] 10.4 Implement retry loop and human-in-the-loop breakpoints
    - Configurable max_retries (default 3, max 10) and timeout per agent (default 60s, max 300s)
    - Pass Rule Engine feedback to agent as structured correction instructions on retry
    - Trigger mandatory human review for: legal references (§3, §10, §13), budget (§6, §8), penalties (§10), and 3× failed validation
    - Present best-scoring draft with warnings after max retries exhausted
    - _Requirements: 5.4, 5.5, 12.3, 12.5, 12.6, 12.7, 12.8, 12.9_

  - [x] 10.5 Implement cross-section state maintenance and Review Agent
    - Maintain conversation state across wizard flow (later sections reference earlier)
    - Implement ReviewAgent that analyzes full assembled TOR for cross-section consistency
    - Generate categorized suggestions: compliance, clarity, completeness, consistency
    - _Requirements: 10.2, 12.4_

  - [x] 10.6 Write property test for orchestrator retry bound (Property 12)
    - **Property 12: Orchestrator Retry Bound**
    - Max retries enforced, never enters infinite loop
    - **Validates: Requirements 5.4, 5.5, 12.6**

- [x] 11. API Endpoints (Projects, Wizard, Drafting, Review)
  - [x] 11.1 Implement project CRUD endpoints
    - GET `/projects` (paginated, filterable by status, sorted by updated_at desc, 20/page)
    - POST `/projects` (create with metadata: name, ministry, budget, type, template_id)
    - GET/PUT/DELETE `/projects/{id}` (detail, update, archive)
    - GET `/projects/{id}/versions`, POST `/projects/{id}/versions/{v}/restore`
    - _Requirements: 9.4, 9.5, 9.6, 9.9_

  - [x] 11.2 Implement wizard step endpoints
    - PUT `/projects/{id}/steps/{step}`: Save step data (validate, persist, create version snapshot)
    - GET `/projects/{id}/steps/{step}`: Retrieve step data
    - POST `/projects/{id}/steps/{step}/draft`: Trigger AI drafting via Orchestrator
    - _Requirements: 4.2, 4.3, 5.1_

  - [x] 11.3 Implement AI drafting and review endpoints
    - POST `/projects/{id}/draft-section`: Draft specific TOR section via Orchestrator
    - POST `/projects/{id}/review`: Run full Rule Engine review on assembled TOR
    - GET `/projects/{id}/suggestions`: Get AI suggestions (3–20 items, categorized)
    - PUT `/projects/{id}/suggestions/{sid}`: Accept/dismiss suggestion
    - POST `/projects/{id}/validate`: Real-time validation (debounced server-side)
    - _Requirements: 5.1, 6.1, 10.1, 10.3, 10.5_

  - [x] 11.4 Implement template management endpoints
    - GET `/templates` (officers see published only, admin sees all)
    - POST/PUT/DELETE `/templates/{id}` (admin only)
    - PUT `/templates/{id}/publish` (admin only, lifecycle: draft → published)
    - Enforce: unpublishing/deleting warns about affected draft TOR projects
    - _Requirements: 7.1, 7.2, 7.4, 7.5, 7.6, 7.8_

  - [x] 11.5 Implement knowledge base management endpoints
    - GET `/knowledge-base`: List documents with status, chunk count
    - POST `/knowledge-base/upload`: Upload and trigger async ingestion
    - DELETE `/knowledge-base/{id}`: Remove document and chunks
    - POST `/knowledge-base/batch-ingest`: Full KB re-ingestion
    - GET `/knowledge-base/{id}/status`: Processing status
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 11.6 Implement file upload endpoints
    - POST `/files/upload`: Multipart upload (max 20MB), store in MinIO, trigger text extraction/OCR
    - GET `/files/{id}/extracted-text`: Return extracted text content
    - Enforce upload rate limit (10/min per user)
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

  - [x] 11.7 Write property test for wizard step data persistence (Property 7)
    - **Property 7: Wizard Step Data Persistence**
    - Submit step data, navigate away, return — data is identical
    - **Validates: Requirements 4.2, 4.3, 4.6**

  - [x] 11.8 Write property test for project version ordering (Property 8)
    - **Property 8: Project Version Ordering**
    - Versions form strictly increasing sequence 1..N with complete snapshots
    - **Validates: Requirements 9.6**

- [x] 12. Export Service (DOCX/PDF Generation)
  - [x] 12.1 Implement DOCX generation with Thai government formatting
    - Create `backend/app/export/docx_generator.py` using python-docx
    - Apply TH Sarabun New 14pt body / 16pt headings, 2.5cm margins, proper headers/page numbering
    - Support Thai/Arabic numeral configuration for section numbering
    - Populate template placeholders with validated TOR content
    - _Requirements: 8.1, 8.3, 8.4, 16.3_

  - [x] 12.2 Implement PDF generation and MinIO upload
    - Create `backend/app/export/pdf_generator.py` using WeasyPrint
    - Ensure PDF content matches DOCX content identically
    - Upload generated files to MinIO, generate signed download URLs (configurable TTL 1–168h, default 24h)
    - _Requirements: 8.2, 8.5_

  - [x] 12.3 Implement export endpoint with retry logic
    - POST `/projects/{id}/export`: Generate DOCX + PDF, return download URLs
    - GET `/projects/{id}/export/status`: Check generation progress
    - GET `/projects/{id}/export/download/{format}`: Redirect to signed MinIO URL
    - Retry once with 30s delay on failure, complete within 120s
    - Support re-export when content updated
    - _Requirements: 8.5, 8.6, 8.7, 8.8_

  - [x] 12.4 Write property test for Thai date format consistency (Property 14)
    - **Property 14: Thai Date Format Consistency**
    - Exported dates always in พ.ศ. (Gregorian + 543)
    - **Validates: Requirements 8.3, 4.7**

  - [x] 12.5 Write property test for export format consistency (Property 10)
    - **Property 10: Export Format Consistency**
    - DOCX and PDF contain identical textual content
    - **Validates: Requirements 8.1, 8.2**

- [~] 13. Checkpoint - Backend Complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Frontend Core (Next.js Setup, Stores, Layout)
  - [x] 14.1 Initialize Next.js 14 project with TypeScript, Tailwind CSS, and shadcn/ui
    - Create `frontend/` with Next.js 14 (App Router), TypeScript strict mode
    - Install and configure Tailwind CSS, shadcn/ui component library
    - Install Zustand for state management, axios for API calls
    - Configure Thai font (TH Sarabun New or Noto Sans Thai for web)
    - _Requirements: 4.1, 16.1, 16.2_

  - [x] 14.2 Implement Zustand stores (auth, project, wizard, UI)
    - Create `useAuthStore`: token, user, isAuthenticated, login/logout, session restore from localStorage
    - Create `useProjectStore`: projects list, activeProject, pagination, fetch/setActive
    - Create `useWizardStore`: currentStep, formData per step, validationErrors, isDirty, auto-save
    - Create `useUIStore`: theme, sidebar, loading, toasts
    - _Requirements: 4.6, 9.10_

  - [x] 14.3 Implement authentication pages and AuthGuard
    - Create login page (`/` or `/login`): Email/password form, Thai UI labels
    - Create registration page: With password policy validation
    - Implement AuthGuard layout wrapper: redirect to login if unauthenticated, preserve session on 401
    - _Requirements: 9.1, 9.10, 16.1_

  - [x] 14.4 Implement project dashboard page
    - Create `/projects` page: List projects with status, last modified, Quality_Score
    - Paginated (20/page), sorted by last modified desc, filterable by status (Draft, In Review, Approved, Rejected, Archived)
    - "New Project" button → template selection → create project
    - _Requirements: 9.5, 9.9_

  - [x] 14.5 Implement root layout with navigation, ThemeProvider, and API client
    - Create root layout with sidebar navigation (Dashboard, Admin links for admin role)
    - Configure axios instance with JWT header injection, 401 interceptor (preserve + redirect)
    - Add global error boundary and toast notification system
    - _Requirements: 15.6, 16.1, 16.7_

- [x] 15. Wizard UI (8-Step Form)
  - [x] 15.1 Implement wizard layout with step indicator and navigation
    - Create `/wizard/[step]/page.tsx` with dynamic routing (steps 1–8)
    - Step progress indicator showing current step, completion %, validation status per step
    - Previous/Next navigation with validation gating (can navigate back freely, forward requires valid)
    - _Requirements: 4.1, 4.3, 4.5_

  - [x] 15.2 Implement Steps 1–3 (Project Info, Problem Description, Objectives)
    - Step 1: Project name, ministry, budget, type, template selection (with overwrite confirmation)
    - Step 2: Problem description, background context text area
    - Step 3: Objectives (SMART format guidance), add/remove objectives
    - Thai language input support, proper word-breaking display
    - _Requirements: 4.1, 7.3, 7.7, 16.2_

  - [x] 15.3 Implement Steps 4–6 (Scope, Qualifications, Budget/Payment)
    - Step 4: Scope of Work with up to 14 subsections, deliverables list
    - Step 5: Vendor qualifications, auto-calculated paid-up capital from budget
    - Step 6: Budget breakdown, payment schedule (installments with % and deliverable linkage), penalty rate
    - _Requirements: 4.1, 5.6, 5.7_

  - [x] 15.4 Implement auto-save with debounce and localStorage fallback
    - 3-second debounce after last keystroke → PUT step data to API
    - On API failure: persist to localStorage, show retry notification
    - Restore from localStorage on reconnection
    - isDirty/isAutoSaving indicators in UI
    - _Requirements: 4.2, 4.6, 4.8_

  - [x] 15.5 Implement Step 8 (Export) with download buttons
    - Trigger export generation (DOCX + PDF)
    - Show export status/progress
    - Provide download buttons for generated files
    - _Requirements: 8.1, 8.2_

- [x] 16. Review & Suggestions UI (Step 7)
  - [x] 16.1 Implement Step 7 Review page with full TOR preview
    - Display assembled TOR document with all sections rendered
    - Show Quality_Score badge with category breakdown (legal, completeness, consistency, format)
    - Inline section editing capability
    - _Requirements: 4.4, 10.4_

  - [x] 16.2 Implement AI suggestions panel
    - Side panel showing 3–20 suggestions categorized: compliance, clarity, completeness, consistency
    - Each suggestion shows: category, affected section, current text, suggested text, predicted score improvement
    - Accept button (applies change, re-validates), Dismiss button (persists as dismissed)
    - Dismissed suggestions don't re-show unless affected content changes
    - _Requirements: 10.1, 10.3, 10.4, 10.5, 10.7_

  - [x] 16.3 Implement real-time validation feedback
    - Debounced validation (3s after last keystroke) while editing in Step 7
    - Display validation results inline with section being edited
    - _Requirements: 10.6_

- [x] 17. Admin UI
  - [x] 17.1 Implement template management admin page
    - List templates (draft/published), CRUD interface
    - Template editor: section structure, placeholder guidance (JSONB editor)
    - Publish/unpublish with affected-projects warning
    - _Requirements: 7.4, 7.6, 7.8_

  - [x] 17.2 Implement knowledge base management admin page
    - List KB documents with name, type, upload date, chunk count, processing status
    - Upload interface (drag-and-drop, multi-file)
    - Processing status indicators, error display for failed documents
    - Delete with confirmation, batch re-ingest trigger
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 18. Checkpoint - Frontend Complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 19. Thai Language Support & Integration
  - [x] 19.1 Configure Thai language processing end-to-end
    - Verify PyThaiNLP integration in RAG chunking (newmm engine)
    - Configure database Thai collation (th_TH.UTF-8 or ICU)
    - Embed TH Sarabun New font in export templates
    - Implement Thai date conversion utility (Gregorian → Buddhist Era, year + 543)
    - Implement configurable Thai/Arabic numeral formatting
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 16.8_

  - [x] 19.2 Configure LLM system prompts for formal Thai register
    - Ensure all agent system prompts enforce ภาษาราชการ (formal government Thai)
    - Validate mixed Thai/English handling in all text processing paths
    - _Requirements: 16.5, 16.7_

- [x] 20. Knowledge Base Seeding
  - [x] 20.1 Create initial knowledge base seed script
    - Create script to ingest core Thai procurement documents: พ.ร.บ. 2560, กฎกระทรวง, ระเบียบกระทรวงการคลัง, หนังสือกรมบัญชีกลาง, คู่มือปฏิบัติงาน
    - Include sample TOR documents for each industry template (IT, Construction, Consulting, General)
    - Report ingestion progress and any failures
    - _Requirements: 3.7, 11.4_

- [x] 21. Integration & E2E Testing
  - [x] 21.1 Write integration tests for full RAG pipeline
    - Test ingest → chunk → embed → store → retrieve end-to-end with testcontainers
    - Test with actual Thai language documents
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 21.2 Write integration tests for LangGraph orchestration
    - Test full drafting workflow with mock LLM → Rule Engine → retry loop
    - Test human-in-the-loop breakpoints
    - Test graceful degradation (RAG failure, LLM timeout)
    - _Requirements: 5.1, 5.2, 5.4, 5.8, 12.2_

  - [x] 21.3 Write integration tests for export pipeline
    - Test content → DOCX → verify formatting (font, margins, dates)
    - Test content → PDF → verify content matches DOCX
    - Test MinIO upload → signed URL download
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 21.4 Write E2E tests with Playwright
    - Test full wizard flow: login → create project → steps 1–8 → export
    - Test auto-save and session restore
    - Test suggestions accept/dismiss flow
    - Test admin template and KB management
    - _Requirements: 4.1, 4.2, 4.6, 9.1_

- [x] 22. Final Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Continuation (Discussion extras)

Tracked after original Kiro tasks 1–22. Implemented in the TOR App Continuation wave:

- [x] In-app คู่มือ `/help` (overview, dashboard, KB, wizard, review, FAQ)
- [x] Standalone ตรวจสอบ TOR `/review` — `POST /api/v1/review/extract`, `/run`, `GET /review/{id}`, `POST /review/compare-projects`
- [x] Phase 0 auto-map — `POST /api/v1/projects/{id}/extraction` + `/extraction/apply` with UI confirm
- [x] Submit / approve / reject workflow on project detail
- [x] Admin user management `/admin/users` + `GET/POST /api/v1/admin/users`
- [x] Authenticated export download (JWT blob stream, not `window.open`)
- [x] Seed CLI `python -m app.seed_db` / `python -m app.seed_kb`

Live Compose walkthrough (operator): `docker compose up --build`, seed, login as `officer@example.go.th` / `Passw0rd!`, create project, steps 1–8. Playwright: `cd app/frontend && E2E=1 npm run test:e2e` against a running stack. RAG ingest with embeddings requires LM Studio or `RUN_INTEGRATION=1`.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at major milestones
- Property tests validate universal correctness properties defined in the design document
- Unit tests validate specific examples and edge cases
- The backend uses Python 3.11+ with FastAPI, the frontend uses TypeScript with Next.js 14
- Docker Compose enables consistent deployment across all environments
- The Provider Factory pattern allows switching deployment modes via environment variable without code changes

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4"] },
    { "id": 2, "tasks": ["2.1"] },
    { "id": 3, "tasks": ["2.2"] },
    { "id": 4, "tasks": ["2.3", "2.4"] },
    { "id": 5, "tasks": ["3.1", "14.1"] },
    { "id": 6, "tasks": ["3.2", "3.3", "3.4", "14.2"] },
    { "id": 7, "tasks": ["4.1", "14.3"] },
    { "id": 8, "tasks": ["4.2", "4.3", "4.4", "4.5", "14.4", "14.5"] },
    { "id": 9, "tasks": ["4.6", "4.7", "6.1"] },
    { "id": 10, "tasks": ["6.2", "6.3", "6.4", "6.5"] },
    { "id": 11, "tasks": ["6.6", "6.7"] },
    { "id": 12, "tasks": ["7.1", "8.1"] },
    { "id": 13, "tasks": ["7.2", "8.2", "8.3", "8.4", "8.5"] },
    { "id": 14, "tasks": ["7.3", "7.4", "8.6", "8.7", "8.8", "8.9"] },
    { "id": 15, "tasks": ["7.5", "7.6", "10.1"] },
    { "id": 16, "tasks": ["10.2", "10.3"] },
    { "id": 17, "tasks": ["10.4", "10.5"] },
    { "id": 18, "tasks": ["10.6", "11.1", "11.2"] },
    { "id": 19, "tasks": ["11.3", "11.4", "11.5", "11.6"] },
    { "id": 20, "tasks": ["11.7", "11.8", "12.1"] },
    { "id": 21, "tasks": ["12.2", "12.3"] },
    { "id": 22, "tasks": ["12.4", "12.5"] },
    { "id": 23, "tasks": ["15.1", "15.2"] },
    { "id": 24, "tasks": ["15.3", "15.4", "15.5"] },
    { "id": 25, "tasks": ["16.1", "16.2", "16.3"] },
    { "id": 26, "tasks": ["17.1", "17.2"] },
    { "id": 27, "tasks": ["19.1", "19.2"] },
    { "id": 28, "tasks": ["20.1"] },
    { "id": 29, "tasks": ["21.1", "21.2", "21.3", "21.4"] }
  ]
}
```
