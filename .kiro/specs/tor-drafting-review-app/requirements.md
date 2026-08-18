# Requirements Document

## Introduction

This document defines requirements for the **TOR Drafting and Review Application** — a production-grade, full-stack web application that assists Thai government procurement officers in drafting, reviewing, and exporting Terms of Reference (TOR) documents. The system leverages a hybrid AI architecture (LLM + RAG + Rule Engine) running on Docker Compose, fully compliant with พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560.

The application reduces TOR creation time from 3–6 weeks to approximately 30–45 minutes while ensuring legal compliance through automated validation and AI-assisted drafting with human-in-the-loop review.

## Glossary

- **TOR_App**: The full-stack TOR Drafting and Review Application (frontend + backend + infrastructure services)
- **Frontend**: The Next.js 14 / React 18 / TypeScript user interface layer
- **Backend**: The FastAPI or Node.js API server handling business logic, AI orchestration, and data persistence
- **Wizard**: The 8-step guided interface that collects project information and generates TOR sections
- **Rule_Engine**: The deterministic validation component that checks TOR drafts against procurement law rules
- **LLM_Service**: The language model provider (Claude Sonnet API for cloud, LM Studio local model for on-premise)
- **RAG_Pipeline**: The Retrieval-Augmented Generation pipeline that retrieves relevant legal/regulatory context from the knowledge base
- **Vector_Store**: The embedding storage system (PostgreSQL + pgvector as default, Qdrant as optional)
- **Knowledge_Base**: The collection of Thai procurement laws, regulations, guidelines, and example TORs ingested into the vector store
- **Orchestrator**: The LangGraph StateGraph controller that coordinates AI agents, rule checks, and human review loops
- **Provider_Factory**: The abstraction layer that instantiates LLM, embedding, and vector store providers based on deployment mode
- **Deployment_Mode**: One of three configurations — on_prem, cloud, or hybrid — selected via environment variable
- **Quality_Score**: A 0–100 numeric score produced by the Rule Engine assessing TOR compliance and completeness
- **Export_Service**: The component responsible for generating Word (.docx) and PDF output with Thai government formatting

## Requirements

### Requirement 1: Docker Compose Infrastructure

**User Story:** As a system administrator, I want to deploy the entire application stack using a single Docker Compose command, so that I can set up the system consistently across development, staging, and production environments.

#### Acceptance Criteria

1. THE TOR_App SHALL define all services (Frontend, Backend, PostgreSQL, Redis, MinIO, and optionally Qdrant) in a single `docker-compose.yml` file
2. WHEN `docker compose up` is executed, THE TOR_App SHALL start all services with correct inter-service networking and health-check dependencies
3. THE TOR_App SHALL use named Docker volumes for PostgreSQL data, MinIO storage, and Qdrant data to ensure persistence across container restarts
4. THE TOR_App SHALL expose configurable port mappings for Frontend (default 3000), Backend (default 4000), PostgreSQL (default 5432), Redis (default 6379), and MinIO (default 9000/9001)
5. IF any service fails its health check, THEN THE TOR_App SHALL prevent dependent services from starting until the dependency is healthy
6. THE TOR_App SHALL support environment variable overrides via `.env` files for all service configuration
7. THE TOR_App SHALL configure health checks with an interval of 30 seconds, a maximum of 3 retries, and a start period of 40 seconds for each service
8. THE TOR_App SHALL place all services on a shared bridge network where services resolve each other by container name
9. WHEN `docker compose down` is executed, THE TOR_App SHALL preserve all named volume data; WHEN `docker compose down -v` is executed, THE TOR_App SHALL remove all named volumes and their data

### Requirement 2: Hybrid LLM Deployment Modes

**User Story:** As a system administrator, I want to switch between on-premise, cloud, and hybrid LLM configurations using environment variables alone, so that I can comply with data residency policies without modifying application code.

#### Acceptance Criteria

1. THE Provider_Factory SHALL instantiate the correct LLM provider based on the `DEPLOYMENT_MODE` environment variable (values: `on_prem`, `cloud`, `hybrid`)
2. WHEN Deployment_Mode is `on_prem`, THE LLM_Service SHALL route all inference requests to a local LM Studio endpoint (OpenAI-compatible API at configurable base URL)
3. WHEN Deployment_Mode is `cloud`, THE LLM_Service SHALL route all inference requests to Claude Sonnet API with prompt caching enabled
4. WHEN Deployment_Mode is `hybrid`, THE Provider_Factory SHALL allow independent provider selection for LLM, Embedding, and Vector Store via separate environment variables
5. THE Provider_Factory SHALL apply the same abstraction to embedding providers (OpenAI text-embedding-3 for cloud, Qwen3-Embedding-4B for on-premise)
6. THE Provider_Factory SHALL apply the same abstraction to vector store providers (pgvector as default, Qdrant as optional)
7. IF the configured LLM endpoint is unreachable, THEN THE Backend SHALL return a structured error response within 10 seconds and log the connection failure
8. IF `DEPLOYMENT_MODE` is not set or contains an invalid value, THEN THE Provider_Factory SHALL reject initialization with an error message indicating accepted values (`on_prem`, `cloud`, `hybrid`)
9. IF Deployment_Mode is `hybrid` and required sub-provider variables (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `VECTOR_STORE_PROVIDER`) are not set, THEN THE Provider_Factory SHALL reject initialization with an error indicating which variable is missing

### Requirement 3: Knowledge Base Ingestion and RAG Pipeline

**User Story:** As a system administrator, I want to ingest Thai procurement law documents into the vector store, so that the AI can retrieve relevant legal context when drafting TOR sections.

#### Acceptance Criteria

1. THE RAG_Pipeline SHALL support ingestion of PDF, Word (.docx), and plain text documents in Thai language
2. WHEN a document is ingested, THE RAG_Pipeline SHALL chunk it into segments of 500–1000 tokens with 100-token overlap, preserving section boundaries
3. THE RAG_Pipeline SHALL generate embeddings for each chunk using the configured embedding provider and store them in the Vector_Store with metadata (source document name, section, page number)
4. WHEN the Orchestrator requests context for a TOR section, THE RAG_Pipeline SHALL retrieve the top-K most relevant chunks (configurable K, default 5) using cosine similarity search
5. THE RAG_Pipeline SHALL support metadata filtering on retrieval (filter by document type, legal reference, or section relevance)
6. THE Vector_Store SHALL store embeddings in PostgreSQL using the pgvector extension with HNSW indexing for sub-100ms retrieval on collections up to 100,000 chunks
7. THE RAG_Pipeline SHALL provide a batch ingestion endpoint that processes the full knowledge base (พ.ร.บ. 2560, กฎกระทรวง, ระเบียบ, คู่มือ, example TORs) and reports progress
8. IF embedding generation fails for any chunk, THEN THE RAG_Pipeline SHALL skip that chunk, log the failure with chunk identifier, and continue processing remaining chunks
9. WHEN retrieval returns fewer chunks than the configured top-K, THE RAG_Pipeline SHALL return all available matching chunks without error

### Requirement 4: 8-Step TOR Drafting Wizard

**User Story:** As a procurement officer, I want a guided 8-step wizard interface to create TOR documents, so that I can provide project information incrementally and receive AI-generated drafts for each section.

#### Acceptance Criteria

1. THE Frontend SHALL present an 8-step wizard with the following sequence: (1) Project Information, (2) Problem Description, (3) Objectives, (4) Scope of Work, (5) Vendor Qualifications, (6) Budget and Payment Schedule, (7) Review and AI Suggestions, (8) Export
2. WHEN the user completes a wizard step (all required fields validated) and advances to the next, THE Frontend SHALL persist the step data to the Backend via API call
3. THE Frontend SHALL allow navigation to any previously completed step without losing entered data
4. WHEN a user is on Step 7 (Review), THE Frontend SHALL display the full assembled TOR with AI-generated suggestions in a side panel
5. THE Frontend SHALL display a progress indicator showing current step, completion percentage (completed steps divided by 8 multiplied by 100), and validation status per step
6. IF a user closes the browser and returns within 30 days, THEN THE Frontend SHALL restore the wizard to the last saved step with all previously entered data intact
7. THE Frontend SHALL render all text content in Thai language with proper Thai Buddhist Era date formatting (พ.ศ.)
8. IF API persistence fails when advancing a step, THEN THE Frontend SHALL display an error message with a retry option and preserve entered data in local storage until persistence succeeds

### Requirement 5: AI-Assisted TOR Section Drafting

**User Story:** As a procurement officer, I want the AI to draft TOR sections based on my input and relevant legal context, so that I can start with a high-quality draft instead of writing from scratch.

#### Acceptance Criteria

1. WHEN the user submits input for a wizard step, THE Orchestrator SHALL invoke the appropriate AI agent to draft the corresponding TOR section using the user input combined with RAG-retrieved context and return the generated draft within 60 seconds
2. THE Orchestrator SHALL use LangGraph StateGraph to coordinate the drafting workflow: Extract → Retrieve → LLM Draft → Rule Guardrail → Human Review
3. WHEN the LLM generates a draft section, THE Rule_Engine SHALL validate it against procurement law rules before presenting it to the user
4. IF the Rule_Engine rejects the draft (Quality_Score below 0.7), THEN THE Orchestrator SHALL re-invoke the LLM with specific feedback and retry up to 3 times
5. IF the draft fails validation after 3 retries, THEN THE Orchestrator SHALL present the best-scoring draft to the user with explicit warning flags indicating non-compliant areas
6. THE LLM_Service SHALL generate drafts for all 10 TOR standard sections: Background, Objectives, Qualifications, Scope of Work (with up to 14 subsections), Timeline, Evaluation Criteria, Budget, Payment Schedule, Penalties and Warranty, and Supporting Documents
7. WHEN generating the Scope of Work section, THE LLM_Service SHALL support up to 14 subsections and maintain internal consistency across them
8. IF RAG retrieval fails during drafting, THEN THE Orchestrator SHALL proceed with user input only and notify the user that legal context was unavailable for this draft

### Requirement 6: Rule Engine Compliance Validation

**User Story:** As a procurement officer, I want automatic compliance checking against Thai procurement law, so that I can be confident the TOR meets all legal requirements before submission.

#### Acceptance Criteria

1. THE Rule_Engine SHALL validate the complete TOR against พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560 and complete validation within 30 seconds
2. THE Rule_Engine SHALL verify that vendor paid-up capital requirements equal budget divided by 4 (ทุนจดทะเบียน = งบประมาณ/4), rounded down to the nearest integer baht
3. THE Rule_Engine SHALL verify that payment schedule percentages sum to exactly 100%, no single installment is less than 5% or greater than 50%, and individual installments fall within legal ranges
4. THE Rule_Engine SHALL flag timeline infeasibility when budget exceeds 100 million baht and duration is less than 180 days, or when budget is less than 10 million baht and duration exceeds 365 days
5. THE Rule_Engine SHALL perform cross-section consistency validation (budget matches scope, timeline matches deliverables, qualifications match scope complexity)
6. THE Rule_Engine SHALL produce a Quality_Score from 0 to 100, with weighted breakdown: legal compliance 40%, completeness 30%, consistency 20%, and format adherence 10%
7. WHEN validation identifies issues, THE Rule_Engine SHALL return structured findings with severity (error, warning, suggestion), the specific rule violated, the affected section, and a recommended correction
8. THE Rule_Engine SHALL validate penalty rates are between 0.01% and 0.20% per day as specified by procurement regulations
9. IF required TOR sections are missing, THEN THE Rule_Engine SHALL halt scoring and return a list of missing sections before proceeding with validation

### Requirement 7: TOR Template System

**User Story:** As a procurement officer, I want to select from predefined TOR templates based on project type, so that I can start with industry-appropriate structure and content.

#### Acceptance Criteria

1. THE TOR_App SHALL provide a base TOR template with all 13 standard sections as defined in the procurement law
2. THE TOR_App SHALL provide industry-specific templates for at minimum: IT Systems, Construction, Consulting Services, and General Procurement
3. WHEN the user selects a template at Step 1 of the wizard, THE Frontend SHALL pre-populate section structures and placeholder guidance text appropriate to that industry
4. THE TOR_App SHALL allow administrators to create, edit, and publish new templates via an admin interface
5. THE TOR_App SHALL store templates in the database with versioning so that changes to templates do not affect previously created TOR documents
6. THE TOR_App SHALL support template lifecycle states (Draft and Published), where only Published templates are visible to procurement officers
7. IF a user has modified pre-populated content and selects a different template, THEN THE Frontend SHALL display a confirmation dialog warning that modifications will be overwritten
8. IF an administrator unpublishes or deletes a template that is referenced by active draft TOR projects, THEN THE TOR_App SHALL display a warning listing the affected projects before proceeding

### Requirement 8: Document Export

**User Story:** As a procurement officer, I want to export the finalized TOR as a Word document or PDF with proper Thai government formatting, so that I can submit it through official procurement channels.

#### Acceptance Criteria

1. WHEN the user requests export at Step 8, THE Export_Service SHALL generate a Word (.docx) file with Thai government document formatting (TH Sarabun New font, 14pt body text, 16pt headings, 2.5cm margins, correct headers, and page numbering)
2. THE Export_Service SHALL generate a PDF version of the same document with identical formatting
3. THE Export_Service SHALL format all dates in Thai Buddhist Era (พ.ศ.) format
4. THE Export_Service SHALL include proper Thai numbering for sections and subsections (๑, ๒, ๓ or 1, 2, 3 as configurable)
5. THE Export_Service SHALL store generated files in MinIO object storage and provide download URLs valid for a configurable duration between 1 and 168 hours (default 24 hours)
6. THE Export_Service SHALL support repeated export — regenerating files when the TOR content is updated
7. IF export generation fails, THEN THE Export_Service SHALL retry once with a 30-second delay before reporting failure to the user with a descriptive error message
8. THE Export_Service SHALL complete document generation within 120 seconds

### Requirement 9: User Authentication and Project Management

**User Story:** As a procurement officer, I want to securely log in and manage my TOR projects, so that my work is persisted and only accessible to authorized users.

#### Acceptance Criteria

1. THE Backend SHALL authenticate users via JWT tokens with configurable expiration (default 24 hours)
2. THE Backend SHALL hash passwords using bcrypt with a minimum of 12 salt rounds
3. THE TOR_App SHALL support role-based access: Officer (create/edit own TORs), Reviewer (review and approve TORs), Admin (manage templates, users, and system settings)
4. WHEN an authenticated user creates a new TOR project, THE Backend SHALL persist it with project metadata (name, ministry, budget, type, creation date, status)
5. THE Frontend SHALL display a project dashboard listing all TOR projects for the current user with status, last modified date, and Quality_Score, paginated at 20 items per page and sorted by last modified date descending
6. THE Backend SHALL support project versioning — saving draft snapshots at each wizard step so users can revert to previous versions, with a maximum of 50 versions per project
7. IF an unauthorized user attempts to access a project, THEN THE Backend SHALL return HTTP 403 and log the access attempt
8. THE Backend SHALL enforce a password policy requiring minimum 8 characters, at least 1 uppercase letter, 1 lowercase letter, 1 digit, and 1 special character
9. THE TOR_App SHALL use defined project status values: Draft, In Review, Approved, Rejected, and Archived
10. IF a JWT token expires (HTTP 401 response), THEN THE Frontend SHALL preserve session data in local storage and redirect the user to re-authenticate without losing unsaved work

### Requirement 10: AI Suggestions and Review Panel

**User Story:** As a procurement officer, I want to see AI-powered improvement suggestions alongside my TOR draft, so that I can iteratively improve document quality.

#### Acceptance Criteria

1. WHEN the user reaches Step 7 (Review), THE Frontend SHALL display a suggestions panel showing a minimum of 3 and maximum of 20 AI-identified improvements categorized by type (compliance, clarity, completeness, consistency)
2. THE Orchestrator SHALL invoke a dedicated review agent that analyzes the full assembled TOR for cross-section consistency issues
3. WHEN the user accepts a suggestion, THE Frontend SHALL apply the recommended change to the relevant section and re-validate the affected area
4. THE suggestions panel SHALL display the current Quality_Score with a breakdown by category and indicate the predicted score improvement for each suggestion
5. THE Frontend SHALL allow the user to dismiss individual suggestions without applying them, and dismissed suggestions SHALL persist as dismissed and not be re-shown unless the affected TOR content changes
6. WHILE the user is editing a section in Step 7, THE Backend SHALL provide real-time validation feedback within 3 seconds of the user stopping typing (debounced with a 3-second delay after last keystroke)
7. THE Frontend SHALL display each suggestion with: category, affected section, current text, suggested replacement text, and predicted score improvement

### Requirement 11: Knowledge Base Management

**User Story:** As an administrator, I want to manage the knowledge base documents that feed the RAG system, so that the AI drafting stays current with the latest regulations and guidelines.

#### Acceptance Criteria

1. THE TOR_App SHALL provide an admin interface for uploading, viewing, and removing knowledge base documents
2. WHEN a new document is uploaded, THE RAG_Pipeline SHALL automatically process it (extract text, chunk, embed, store) and report completion status
3. THE admin interface SHALL display the current knowledge base inventory with document name, type, upload date, chunk count, and processing status
4. THE TOR_App SHALL support the following knowledge base source types: พ.ร.บ. 2560, กฎกระทรวง, ระเบียบกระทรวงการคลัง, หนังสือกรมบัญชีกลาง, คู่มือปฏิบัติงาน, and example TOR documents
5. IF document processing fails (unsupported format, OCR failure, embedding error), THEN THE RAG_Pipeline SHALL log the error with details and mark the document as failed without affecting other documents

### Requirement 12: Multi-Agent AI Architecture

**User Story:** As a system architect, I want the AI drafting system to use specialized agents for different TOR sections, so that each section receives domain-specific expertise and the system can scale its capabilities.

#### Acceptance Criteria

1. THE Orchestrator SHALL support a minimum of 10 specialized AI agents — one per standard TOR section — each with a dedicated system prompt containing section-specific guidance and examples
2. THE Orchestrator SHALL coordinate agents via LangGraph StateGraph with conditional routing, retry loops, and human-in-the-loop breakpoints
3. WHEN the Rule_Engine returns rejection feedback, THE Orchestrator SHALL pass the specific violations back to the drafting agent as structured correction instructions
4. THE Orchestrator SHALL maintain conversation state across the full wizard flow so that later sections can reference information from earlier sections
5. THE Orchestrator SHALL enforce that the Rule_Engine (deterministic) always validates LLM output before presenting to users — the LLM never makes final decisions on legal/numeric matters
6. THE Orchestrator SHALL support configurable maximum retry count (default 3, maximum 10) and timeout per agent invocation (default 60 seconds, maximum 300 seconds)
7. THE Orchestrator SHALL trigger human-in-the-loop breakpoints for sections containing legal references, budget calculations, and penalty clauses
8. IF an agent invocation exceeds the configured timeout, THEN THE Orchestrator SHALL terminate the invocation, log the timeout with agent identifier and elapsed time, and present an error to the user with a manual retry option
9. IF maximum retries are exhausted for any agent, THEN THE Orchestrator SHALL preserve all previously completed sections unchanged and present only the failing section for manual intervention

### Requirement 13: Database and Data Persistence

**User Story:** As a system administrator, I want all application data persisted in PostgreSQL with proper schema, so that data is durable, queryable, and supports the vector storage needs.

#### Acceptance Criteria

1. THE Backend SHALL use PostgreSQL 15+ as the primary database with the pgvector extension enabled for vector storage
2. THE Backend SHALL implement database migrations that create and maintain the schema for: users, projects, TOR sections, templates, knowledge base documents, embeddings, and audit logs
3. THE Backend SHALL use Redis for session caching, rate limiting counters, and background job queues
4. WHEN the application starts, THE Backend SHALL run pending migrations automatically and verify database connectivity before accepting requests
5. THE Backend SHALL implement connection pooling with a configurable maximum pool size (default 20 connections)
6. THE TOR_App SHALL support database backup via standard PostgreSQL pg_dump without requiring application downtime

### Requirement 14: File Upload and OCR Processing

**User Story:** As a procurement officer, I want to upload existing documents (PDF, Word) as reference material, so that the AI can extract information and use it when drafting the TOR.

#### Acceptance Criteria

1. THE Backend SHALL accept file uploads of PDF and Word (.docx) format with a configurable maximum file size (default 20 MB)
2. WHEN a PDF file is uploaded, THE Backend SHALL extract text content using a server-side PDF parser, falling back to OCR (Tesseract with Thai + English language support) for scanned documents
3. WHEN a Word file is uploaded, THE Backend SHALL extract text content preserving document structure (headings, paragraphs, tables)
4. THE Backend SHALL store uploaded files in MinIO object storage, separate from the database
5. IF OCR processing exceeds the configured timeout (default 30 seconds), THEN THE Backend SHALL terminate the OCR process and return a partial result with a timeout warning
6. THE Backend SHALL enforce rate limiting on upload endpoints (configurable, default 10 uploads per minute per user)

### Requirement 15: API Rate Limiting and Security

**User Story:** As a system administrator, I want the application to enforce security best practices, so that it is protected against common attacks and abuse.

#### Acceptance Criteria

1. THE Backend SHALL enforce rate limiting of API requests (configurable, default 100 requests per minute per user)
2. THE Backend SHALL validate and sanitize all user input before processing or storage
3. THE Backend SHALL use HTTPS for all external communication and require TLS for database connections in production
4. THE Backend SHALL never expose secrets (API keys, database passwords, JWT secrets) in logs or API responses
5. IF rate limit is exceeded, THEN THE Backend SHALL return HTTP 429 with a Retry-After header indicating when the user may retry
6. THE Backend SHALL implement CORS configuration restricting origins to the configured frontend domain
7. THE Backend SHALL log all authentication events (login, logout, failed attempts) with timestamp and IP address for audit purposes

### Requirement 16: Thai Language Support

**User Story:** As a procurement officer, I want the entire application to support Thai language input, display, and document generation, so that I can work entirely in my native language.

#### Acceptance Criteria

1. THE Frontend SHALL render all UI labels, navigation, error messages, and help text in Thai language
2. THE Frontend SHALL support Thai text input with proper word-breaking and display in all form fields and text editors
3. THE Export_Service SHALL use Thai-compatible fonts (TH Sarabun New or equivalent) that support all Thai Unicode code points (U+0E00–U+0E7F) in generated Word and PDF documents
4. THE RAG_Pipeline SHALL process Thai language documents correctly during chunking, preserving Thai word boundaries using dictionary-based tokenization (PyThaiNLP or equivalent)
5. THE LLM_Service SHALL generate TOR content in formal Thai register (ภาษาราชการ) appropriate for government procurement documents
6. THE Backend SHALL store all text data in UTF-8 encoding and the database SHALL use Unicode collation supporting Thai character sorting based on Royal Institute Dictionary ordering (ก–ฮ)
7. THE Frontend SHALL render mixed Thai and English content without garbled characters in all views and exported documents
8. IF a text encoding issue is detected during processing, THEN THE Backend SHALL return a Thai-language error message describing the issue and preserve all other form data submitted in the same request
