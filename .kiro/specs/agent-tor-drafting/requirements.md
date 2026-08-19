# Requirements Document

## Introduction

ระบบ Agent TOR Drafting เป็นการออกแบบใหม่ของกระบวนการร่าง TOR (Terms of Reference) สำหรับการจัดซื้อจัดจ้างภาครัฐไทย โดยเปลี่ยนจากแนวทาง wizard 8 ขั้นตอน (phase-based) เป็นแนวทาง agent-based ที่ทำงานแบบสนทนา (conversational) ผู้ใช้สามารถอัปโหลดเอกสารขนาดใหญ่และวางข้อความยาวในครั้งเดียว ระบบจะวิเคราะห์และจัดทำร่าง TOR ทั้ง 13 ส่วนหลัก (พร้อม 14 ส่วนย่อยของขอบเขตงาน) โดยอัตโนมัติ ตรวจจับข้อมูลที่ขาด ถามคำถามเติมเต็ม และสร้าง TOR ที่ผ่านการตรวจสอบกฎหมายอย่างสมบูรณ์

## Glossary

- **Agent_Orchestrator**: ตัวประสานงานหลักที่ควบคุม workflow การร่าง TOR ทั้งหมดในรูปแบบ agent-based ทำงานผ่าน LangGraph StateGraph
- **Intake_Ingestion_Service**: บริการที่รับเอกสารและข้อความจากผู้ใช้ ทำการสกัดข้อความ แบ่งส่วน และเก็บ cache
- **Section_Mapper**: ส่วนประกอบที่วิเคราะห์เนื้อหาทั้งหมดและจัดสรร (map) เข้าสู่ช่อง TOR ทั้ง 27 ช่อง (s1–s13 + s4.1–s4.14)
- **Gap_Detector**: ส่วนประกอบที่ตรวจสอบความครบถ้วนของข้อมูลในแต่ละช่อง TOR และสร้างคำถามเติมเต็ม
- **Draft_Generator**: ส่วนประกอบที่สร้างร่าง TOR จากข้อมูลที่รวบรวมครบถ้วนแล้ว โดยใช้ RAG context และ agent เฉพาะทาง
- **Rule_Engine**: เครื่องมือตรวจสอบความถูกต้องตามกฎหมาย พ.ร.บ. 2560 ที่มีอยู่แล้วในระบบ
- **Session_Cache**: ระบบ cache ที่เก็บผลลัพธ์การวิเคราะห์ระหว่าง session เพื่อหลีกเลี่ยงการประมวลผลซ้ำ ใช้ Redis เป็น backend
- **TOR_Slot**: ช่องข้อมูลของ TOR (s1–s13 สำหรับส่วนหลัก, s4.1–s4.14 สำหรับส่วนย่อยขอบเขตงาน)
- **Coverage_Map**: แผนภูมิแสดงสถานะความครบถ้วนของข้อมูลในแต่ละ TOR_Slot (filled, gap, reference_only)
- **LLM_Provider**: ส่วนต่อประสาน LLM ที่รองรับหลาย backend (LM Studio, Ollama, OpenAI, Anthropic, Bedrock, Gemini, Azure)
- **Fact_Required_Slots**: ช่อง TOR ที่ต้องมีข้อเท็จจริงจากผู้ใช้โดยตรง ไม่สามารถเติมจากอ้างอิงกฎหมายเพียงอย่างเดียว (s1, s2, s5, s6, s7, s4.1)
- **Knowledge_Chat_Service**: บริการแชทถาม-ตอบที่ค้นหาและตอบคำถามจากฐานความรู้ (Knowledge Base) ทั้งส่วนกลาง (กฎหมาย ระเบียบ ตัวอย่าง TOR) และส่วนเฉพาะของผู้ใช้แต่ละคน (เอกสารที่ผู้ใช้อัปโหลด)
- **Export_Service**: บริการส่งออกเอกสาร TOR ที่ร่างเสร็จแล้วเป็นไฟล์ DOCX และ PDF พร้อมจัดรูปแบบตามมาตรฐานเอกสารราชการ
- **Global_Knowledge_Base**: ฐานความรู้ส่วนกลางที่ผู้ใช้ทุกคนเข้าถึงได้ ประกอบด้วยกฎหมาย ระเบียบ กฎกระทรวง และตัวอย่าง TOR
- **User_Knowledge_Base**: ฐานความรู้เฉพาะผู้ใช้ ประกอบด้วยเอกสารที่ผู้ใช้แต่ละคนอัปโหลดเข้าระบบ มีการควบคุมสิทธิ์การเข้าถึง

## Requirements

### Requirement 1: Bulk Document Ingestion

**User Story:** As a procurement officer, I want to upload multiple large documents and paste long text in a single interaction, so that the system has all project context needed to draft a complete TOR without requiring me to fill forms step by step.

#### Acceptance Criteria

1. WHEN the user submits one or more documents (PDF, DOCX, PPTX, TXT) along with free-text input, THE Intake_Ingestion_Service SHALL accept and process the combined input in a single request, supporting a maximum of 20 documents per request.
2. IF a single document exceeds 50 MB in size, THEN THE Intake_Ingestion_Service SHALL reject that file and return a per-file error status indicating the file exceeded the 50 MB size limit.
3. WHEN the combined text content of all inputs exceeds 200,000 characters, THE Intake_Ingestion_Service SHALL process the content using a chunked pipeline that maintains document boundaries.
4. THE Intake_Ingestion_Service SHALL extract text from PDF, DOCX, PPTX, and TXT file formats preserving structural elements: headings, lists, and tables.
5. WHEN text extraction is complete, THE Intake_Ingestion_Service SHALL store the extracted content in MinIO object storage with metadata linking to the project ID.
6. IF a file format is unsupported or extraction fails, THEN THE Intake_Ingestion_Service SHALL return a per-file error status indicating the cause of failure without blocking processing of other successfully extracted files.
7. THE Intake_Ingestion_Service SHALL support both cloud storage (MinIO/S3) and local filesystem storage based on the configured deployment_mode.
8. WHEN processing of all submitted files is complete, THE Intake_Ingestion_Service SHALL return a response containing a per-file status (success or error with cause) and the associated project ID within 120 seconds of request submission.

### Requirement 2: Single-Pass Content Analysis and TOR Section Mapping

**User Story:** As a procurement officer, I want the system to automatically analyze all my uploaded content and map it to the appropriate TOR sections, so that I can see which sections are already covered without manually organizing the information.

#### Acceptance Criteria

1. WHEN all intake content has been ingested, THE Section_Mapper SHALL analyze the combined content and produce a slot_map covering all 27 TOR_Slots (s1–s13 and s4.1–s4.14).
2. WHEN producing the slot_map, THE Section_Mapper SHALL classify each TOR_Slot into one of three statuses: "filled" (at least one project-specific factual statement extracted), "gap" (no project-specific factual statements extracted), or "reference_only" (only legal boilerplate or generic template language found with no project-specific facts).
3. WHEN performing section mapping, THE Section_Mapper SHALL perform content analysis in a single pass under normal operation, invoking the LLM_Provider with the full extracted content (or summarized chunks for content exceeding the model context window); multi-pass processing is permitted only during error recovery as specified in criterion 6.
4. WHEN mapping content to a TOR_Slot, THE Section_Mapper SHALL extract and preserve source attribution for each mapped slot, recording the input document name and the relevant section or page reference that contributed to each slot.
5. WHEN the Section_Mapper completes analysis, THE Agent_Orchestrator SHALL persist the resulting slot_map and source metadata in the project's analysis_json field.
6. IF the LLM_Provider fails to respond within 90 seconds or returns an error during analysis, THEN THE Section_Mapper SHALL retry once with the content reduced to no more than 50% of the original token count before reporting a partial mapping with an error status.
7. IF the retry attempt also fails or times out, THEN THE Section_Mapper SHALL return a partial slot_map containing any slots successfully mapped before the failure, mark all remaining slots with status "error", and report the failure reason to the Agent_Orchestrator. A partial slot_map SHALL be returned whenever any slots were successfully mapped, regardless of the specific failure reason.

### Requirement 3: Gap Detection and Follow-Up Question Generation

**User Story:** As a procurement officer, I want the system to identify which TOR sections still lack information and ask me targeted questions, so that I can provide only the missing details efficiently.

#### Acceptance Criteria

1. WHEN the slot_map is produced, THE Gap_Detector SHALL identify all TOR_Slots with status "gap" or "reference_only" where the slot belongs to Fact_Required_Slots.
2. WHEN gaps are identified, THE Gap_Detector SHALL generate one follow-up question in Thai per identified gap, where each question references the TOR section name, states the type of information missing, and requests the user to provide a specific value or description.
3. WHEN generating follow-up questions, THE Gap_Detector SHALL present Fact_Required_Slots (s1, s2, s5, s6, s7, s4.1) questions before non-critical slot questions.
4. WHEN presenting follow-up questions, THE Gap_Detector SHALL group questions that share the same TOR section into a single prompt group and present no more than 5 questions per interaction round.
5. WHEN the user provides answers to gap questions, THE Section_Mapper SHALL incrementally update the affected TOR_Slots without re-analyzing previously mapped content.
6. WHEN all Fact_Required_Slots transition to status "filled", THE Agent_Orchestrator SHALL mark the project as ready for full draft generation.
7. IF the user explicitly requests draft generation before all Fact_Required_Slots are filled, THEN THE Agent_Orchestrator SHALL proceed with draft generation; WHEN draft generation is triggered (whether by user request or automatically), THE Draft_Generator SHALL include a warning for each Fact_Required_Slot that does not have status "filled", indicating the section name and the type of information still missing.

### Requirement 4: Session Caching

**User Story:** As a procurement officer, I want the system to remember previous analysis results during my drafting session, so that I do not experience delays from re-processing the same documents when answering follow-up questions.

#### Acceptance Criteria

1. WHEN the Intake_Ingestion_Service completes text extraction, THE Session_Cache SHALL store the extracted text keyed by project_id and a content hash with a TTL of 24 hours.
2. WHEN the Section_Mapper completes slot mapping, THE Session_Cache SHALL store the slot_map result keyed by project_id with a TTL of 24 hours.
3. WHEN a follow-up answer is received, THE Agent_Orchestrator SHALL retrieve the cached slot_map and update only the slots that the user's answer addresses, avoiding full re-analysis of previously mapped content.
4. WHEN the cache entry for a project is found, THE Intake_Ingestion_Service SHALL skip text extraction for documents whose content hash matches the cached version.
5. IF a cache entry has expired or is missing, THEN THE Agent_Orchestrator SHALL trigger re-analysis from the stored raw documents in MinIO without requiring the user to re-upload.
6. THE Session_Cache SHALL use Redis as the caching backend with configurable TTL per cache category: extraction (default 24 hours), mapping (default 24 hours), draft (default 48 hours), with minimum TTL of 1 hour and maximum of 168 hours.
7. IF a cache write operation fails, THEN THE Session_Cache SHALL log the failure and proceed with the operation without blocking the user-facing workflow.
8. IF the user explicitly requests re-analysis or uploads new documents, THEN THE Agent_Orchestrator SHALL trigger full re-analysis regardless of whether cached data exists for the project.

### Requirement 5: Multi-Provider LLM Support for Agent Operations

**User Story:** As a system administrator, I want the agent-based TOR drafting to work with both cloud LLM providers and local on-premises models, so that the system can be deployed in restricted network environments.

#### Acceptance Criteria

1. THE Agent_Orchestrator SHALL obtain LLM instances exclusively through the existing ProviderFactory, supporting all configured providers (LM Studio, Ollama, OpenAI, Anthropic, Bedrock, Gemini, Azure Foundry, OpenAI-compatible).
2. WHILE deployment_mode is "on_prem", THE Agent_Orchestrator SHALL default to local LLM providers (LM Studio, Ollama, or llama.cpp) with a default agent_timeout_seconds of 300 seconds; IF the administrator has explicitly configured a cloud provider, THEN THE Agent_Orchestrator SHALL use the configured provider.
3. WHILE deployment_mode is "cloud", THE Agent_Orchestrator SHALL use cloud LLM providers with a default agent_timeout_seconds of 120 seconds.
4. WHILE deployment_mode is "cloud", THE Agent_Orchestrator SHALL NOT use local LLM providers and SHALL use only cloud providers configured via the ProviderFactory.
5. WHEN the configured LLM_Provider fails to respond within the agent_timeout_seconds limit, THE Agent_Orchestrator SHALL log the timeout event, preserve any in-progress session state, and return an error response indicating the provider timed out without terminating the user session.
6. THE Agent_Orchestrator SHALL pass max_tokens and temperature parameters based on the operation type: full-document analysis (max_tokens: 8192, temperature: 0.2), section drafting (max_tokens: 4096, temperature: 0.3), and gap question generation (max_tokens: 2048, temperature: 0.4).
7. IF the configured LLM_Provider is unreachable due to connection failure or authentication error, THEN THE Agent_Orchestrator SHALL log the failure reason and return an error response indicating the provider is unavailable, without retrying automatically.

### Requirement 6: Input-First Conversational Agent Workflow

**User Story:** As a procurement officer, I want to start the TOR drafting process by providing project information upfront, have the system analyze and fill slots automatically, ask me only for missing information, and confirm the complete content with me before generating the actual TOR draft.

#### Acceptance Criteria

1. WHEN the user opens a new TOR project, THE Agent_Orchestrator SHALL present a starting interface that requires the user to provide initial input (at least one document or at least 50 characters of text) before any analysis or drafting begins.
2. THE Agent_Orchestrator SHALL NOT allow advancement to drafting or review stages until the user has provided initial input material.
3. WHEN initial input is received, THE Agent_Orchestrator SHALL trigger the Section_Mapper to analyze and map content to TOR_Slots within 30 seconds, displaying a processing indicator to the user that shows the analysis is in progress.
4. IF the Section_Mapper fails to complete analysis or encounters an error, THEN THE Agent_Orchestrator SHALL display an error message indicating the analysis could not be completed and offer the user the option to retry or provide different input.
5. WHEN the Section_Mapper completes, THE Agent_Orchestrator SHALL present the Coverage_Map showing which slots are filled and which remain empty, and begin the gap-filling conversation by asking up to 3 questions per interaction turn, prioritizing Fact_Required_Slots that have no content.
6. WHEN the user provides answers to gap questions, THE Agent_Orchestrator SHALL update affected slots within 5 seconds and re-evaluate readiness by checking whether all Fact_Required_Slots contain content meeting their minimum validation criteria.
7. WHEN all Fact_Required_Slots contain content that meets their validation criteria, THE Agent_Orchestrator SHALL present a final confirmation view showing the complete collected content for all 27 TOR_Slots, requesting explicit user confirmation before proceeding to draft generation.
8. WHEN the user confirms the collected content, THE Draft_Generator SHALL generate the full TOR draft using the confirmed slot data.
9. IF the user rejects or edits content during final confirmation, THEN THE Agent_Orchestrator SHALL update the affected slots and re-present the confirmation view with the changes applied.
10. THE Agent_Orchestrator SHALL support resuming a previously started conversation by loading the session_state from the database and cache, provided the session was last active within 30 days.
11. THE Agent_Orchestrator SHALL implement the workflow as a stateful conversation loop: input → analyze → gap_fill → confirm → draft, allowing the user to move between stages by providing new input or requesting re-analysis at any point without navigating between discrete wizard phases.

### Requirement 7: Full TOR Draft Generation with Validation and Export

**User Story:** As a procurement officer, I want the system to generate a complete, legally compliant TOR draft that resembles established TOR examples, and allow me to download the result as a file.

#### Acceptance Criteria

1. WHEN the user triggers full draft generation (after confirmation), THE Draft_Generator SHALL generate content for all 13 TOR sections using the collected slot_map data, RAG-retrieved legal context, and section-specific agents.
2. WHEN all 13 sections have been generated, THE Draft_Generator SHALL invoke the existing Rule_Engine on the complete generated TOR to validate legal compliance, penalty rates, payment schedules, and budget consistency.
3. WHEN the Rule_Engine reports findings with severity "error" at any point during or after generation, THE Draft_Generator SHALL attempt automatic correction by re-drafting affected sections with the Rule_Engine feedback included in the prompt, for a maximum of 3 correction attempts per section.
4. IF automatic correction fails to resolve all severity "error" findings after the maximum 3 attempts, THEN THE Draft_Generator SHALL present the draft to the user with unresolved findings highlighted and a summary of remaining errors requiring manual resolution.
5. THE Draft_Generator SHALL produce a quality_score (0–100) for the complete TOR and present it alongside the draft to the user, where a score below 60 triggers a warning indicating the draft may require significant manual revision.
6. WHEN sections requiring mandatory human review (s3, s6, s8, s10, s13) are generated, THE Agent_Orchestrator SHALL flag those sections with a visible indicator for user attention, and THE system SHALL prevent export until the user has explicitly acknowledged each flagged section.
7. THE Draft_Generator SHALL generate all sections in formal Thai register (ภาษาราชการ) consistent with พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560.
8. WHEN drafting individual sections, THE Draft_Generator SHALL use the existing specialized agents (background_agent, objectives_agent, scope_agent, etc.) to maintain domain expertise per section.
9. THE Draft_Generator SHALL produce output that matches the section ordering, heading hierarchy, and clause-numbering conventions found in the established TOR examples stored in the knowledge base.
10. WHEN the TOR draft is finalized, THE Export_Service SHALL automatically generate DOCX and PDF formats and make them immediately available for download, preserving Thai character rendering, section numbering, and heading hierarchy as displayed in the draft preview, without requiring a separate user request.
11. THE Export_Service SHALL apply a standard TOR document template including headers with the procuring agency name, footers with page numbers in the format "page X of Y", and section numbering consistent with the knowledge-base TOR examples.

### Requirement 8: RAG-Enhanced Drafting with Graceful Degradation

**User Story:** As a procurement officer, I want the system to reference relevant legal regulations and past TOR examples when drafting, so that the output is legally sound and follows established patterns.

#### Acceptance Criteria

1. WHEN drafting each TOR section, THE Draft_Generator SHALL retrieve relevant legal context via the existing hybrid_retrieve function (pgvector + GraphRAG).
2. THE Draft_Generator SHALL include up to 5 relevant RAG chunks as reference context for each section's LLM invocation.
3. IF the RAG retrieval returns no chunks with a relevance score above 0.5, THEN THE Draft_Generator SHALL proceed with drafting using only the user-provided slot content and append a warning to the draft output indicating that legal references could not be verified for that section.
4. IF the RAG retrieval fails due to database connection error or timeout, THEN THE Draft_Generator SHALL proceed with drafting using only the user-provided slot content, append a warning to the draft output indicating that legal references could not be retrieved, and log the retrieval failure with the error details.
5. THE Draft_Generator SHALL pass section_relevance metadata to the retriever to obtain section-specific legal references.

### Requirement 9: Knowledge Base Chat Tool

**User Story:** As a procurement officer, I want a separate chat tool that lets me ask questions and get answers from the knowledge base (both shared regulations and my personal uploaded documents), so that I can research procurement rules and reference materials without starting a TOR drafting process.

#### Acceptance Criteria

1. THE Knowledge_Chat_Service SHALL provide a conversational interface where users can submit questions in Thai or English (up to 1000 characters per message) and receive answers derived from content in the knowledge base.
2. THE Knowledge_Chat_Service SHALL search across two scopes: global knowledge base (shared legal regulations, government rules, example TORs) and user-specific knowledge base (documents uploaded by the current user).
3. WHEN answering a question, THE Knowledge_Chat_Service SHALL use the existing hybrid_retrieve function to find relevant chunks and generate an answer using the LLM_Provider with retrieved context.
4. WHEN the Knowledge_Chat_Service generates an answer from retrieved chunks, THE Knowledge_Chat_Service SHALL include source citations referencing the document name and, where available in the chunk metadata, the page number and section title from which the information was found; citations are included only when source material is successfully retrieved.
5. IF the hybrid_retrieve function returns no chunks meeting the configured relevance score threshold for a user question, THEN THE Knowledge_Chat_Service SHALL respond with a message indicating that no relevant information was found in the knowledge base, without generating a synthesized answer from the LLM_Provider alone.
6. THE Knowledge_Chat_Service SHALL maintain conversation history within a session, retaining up to the most recent 20 message pairs (user question and system response), to support follow-up questions and contextual clarification.
7. WHEN a user starts a new chat interaction, THE Knowledge_Chat_Service SHALL create a new session; the session SHALL remain active until the user explicitly ends it or until 30 minutes of inactivity has elapsed.
8. THE Knowledge_Chat_Service SHALL respect access controls: users can access global knowledge base content and their own uploaded documents, but cannot access other users' private documents.
9. WHILE deployment_mode is "on_prem", THE Knowledge_Chat_Service SHALL function using local LLM providers without requiring external network access.

### Requirement 10: Coverage Map Presentation

**User Story:** As a procurement officer, I want to see a visual summary of which TOR sections are complete and which need more information, so that I can understand my progress at a glance.

#### Acceptance Criteria

1. WHEN the Section_Mapper produces a slot_map, THE Agent_Orchestrator SHALL return a Coverage_Map response containing all 27 slots with their status (filled, gap, reference_only), label in Thai, and whether the slot is fact-required.
2. THE Coverage_Map SHALL classify each gap as either "critical" (the slot belongs to Fact_Required_Slots and has status "gap" or "reference_only") or "non-critical" (the slot does not belong to Fact_Required_Slots or can be filled from legal references).
3. WHEN a slot status changes from "gap" to "filled" after a user answer, THE Agent_Orchestrator SHALL return an updated Coverage_Map reflecting the new state within the same response.
4. THE Coverage_Map response SHALL include a readiness_score (float 0.0–1.0) representing the fraction of Fact_Required_Slots that have status "filled" with non-empty content, and a ready boolean that is true only when readiness_score equals 1.0.

### Requirement 11: Incremental Slot Update from User Answers

**User Story:** As a procurement officer, I want to answer gap-filling questions in natural language and have the system intelligently update the relevant TOR sections, so that I do not need to manually specify which section my answer belongs to.

#### Acceptance Criteria

1. WHEN the user provides a free-text answer during the gap-filling conversation, THE Section_Mapper SHALL identify which TOR_Slots the answer addresses and populate each identified slot with the relevant portion of the answer within 5 seconds.
2. WHEN the user provides an answer that addresses multiple TOR_Slots in a single response, THE Section_Mapper SHALL split the answer content and distribute each segment to the corresponding slot based on semantic relevance.
3. WHEN updating a TOR_Slot that already contains content, THE Section_Mapper SHALL append the new content to the existing slot content by default; IF the new content contradicts or supersedes the existing content, THEN THE Section_Mapper SHALL replace the existing content with the new content.
4. WHEN the user provides a direct correction or override for a specific slot by explicitly referencing the slot name or section title, THE Section_Mapper SHALL replace the entire slot content with the user's new input.
5. IF the Section_Mapper cannot map an answer to a single slot with sufficient confidence, THEN THE Agent_Orchestrator SHALL ask a clarifying question that lists no more than 5 candidate target sections for the user to choose from.
6. WHEN the Section_Mapper updates one or more TOR_Slots from a user answer, THE Agent_Orchestrator SHALL present a summary to the user indicating which slots were updated and the content assigned to each, before proceeding to the next question.

### Requirement 12: Timeout and Resource Protection

**User Story:** As a system administrator, I want the agent workflow to have bounded resource usage, so that long-running operations do not exhaust system resources or block other users.

#### Acceptance Criteria

1. WHEN any single LLM invocation exceeds the configured agent_timeout_seconds (default 60s for cloud, up to 300s for on_prem), THE Agent_Orchestrator SHALL terminate the invocation and return a timeout error to the calling component.
2. THE Intake_Ingestion_Service SHALL limit the total processing time for a single ingestion batch to 600 seconds; IF the limit is reached, THEN the service SHALL return a partial result containing per-file statuses for all files processed before the timeout and an error status for remaining files.
3. THE Agent_Orchestrator SHALL limit the total number of gap-filling iterations to 20 per session; WHEN the limit is reached, THE Agent_Orchestrator SHALL inform the user that the maximum number of interactions has been reached and offer to proceed with draft generation using the currently collected slot data.
4. WHEN the full draft generation is triggered, THE Draft_Generator SHALL impose a total timeout of 900 seconds (15 minutes) for generating all 13 sections; IF the timeout is reached, THEN the generator SHALL finalize with whatever sections completed successfully.
5. IF a timeout occurs during draft generation, THEN THE Draft_Generator SHALL return the partially completed sections along with a list of section keys that were not generated, and preserve all session state so the user can retry generation of the missing sections.
