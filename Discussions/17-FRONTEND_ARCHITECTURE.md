# Frontend architecture

Next.js 14 App Router in `app/frontend`. Production image is standalone Node on port **3000**.

## Request path

Browser JavaScript calls **same-origin** `/api/v1/...`. `next.config.js` rewrites that to `BACKEND_INTERNAL_URL` (`http://backend:4000/api/v1` in Docker) and sets `experimental.proxyTimeout` to **300000** ms so Phase 2 AI draft and chat SSE are not cut at the default 30s rewrite limit. Do not set `NEXT_PUBLIC_API_URL` to the Docker hostname `backend` — the browser cannot resolve it.

Axios `apiClient` uses `withCredentials: true` so the HttpOnly cookie `tor_access_token` is sent. If the in-memory store still has a token (returned in the login JSON), it is also sent as `Authorization: Bearer`. A 401 clears the session and sends the browser to `/login`.

## Route groups

| Group | Routes | Guard |
|-------|--------|--------|
| Public | `/` | Redirects guests to `/login` |
| Auth | `/login`, `/register` | Guest layout (navy card) |
| App | `/projects`, `/projects/[id]/draft`, `/draft`, `/chat`, `/knowledge-base`, `/review`, `/help` | `AuthGuard` + 255px navy sidebar |
| Compat | `/projects/[id]/wizard/[step]`, `/wizard/[step]` | Redirect into the 5-phase draft |
| Admin | `/admin/templates`, `/admin/knowledge-base`, `/admin/users`, `/admin/ai-settings` | Admin layout redirects non-admins |

- Officers browse `/knowledge-base`: shared groups (`mandatory_handbook`, `mandatory_raw`) plus **เอกสารของฉัน**. Upload goes to `POST /knowledge-base/mine` (owner-only RAG). Admins still push shared files via `/knowledge-base/upload` and `/admin/knowledge-base`.
- Main nav: แดชบอร์ด, ฐานความรู้, ร่าง TOR, ตรวจสอบ TOR, **ถาม-ตอบ** (`/chat`), คู่มือ. Admin cluster is below. Creating a project opens a form (name, agency, budget, type) then `/projects/{id}/draft`. Reviewer/admin see **อนุมัติ** / **ส่งกลับ** on `in_review` rows (`decideProject` → `POST /projects/{id}/approve|reject`). Officers cannot edit while a project is in review. Phase 3 submit is disabled until 13 sections are filled **and** HITL sections are confirmed.

## Client state (Zustand)

| Store | Responsibility |
|-------|----------------|
| `auth-store` | In-memory user + optional token; `restoreSession` calls `GET /auth/me` using the cookie. JWT is **not** persisted to localStorage |
| `project-store` | Project list, active project, create/update/submit |
| `wizard-store` | Kept for leftover step helpers; the live editor is `DraftWorkspace` |
| `ui-store` | Theme, sidebar, toasts (theme/sidebar persisted) |

## 5-phase workspace

`DraftWorkspace` (`src/components/draft/draft-workspace.tsx`) is the drafting UI. Shared chat chrome lives in `src/components/chat/chat-shell.tsx` + `mini-room-list.tsx`.

| Phase | UI |
|-------|-----|
| 0 | Bulk upload + project intake chat (`IntakeChatPanel`) — no 9-class form |
| 1 | Same chat: coverage table, gap questions, fill-reference, confirm ready |
| 2 | Flow-track of 13 sections; s4 chips; HITL confirm vs save; AI draft writes `content` |
| 3 | Completeness + Rule Engine + ReviewAgent suggestions (`GET …/suggestions`) + submit |
| 4 | Word / PDF export (MinIO) — surfaces failed/timeout status instead of silent return |

Create-project from the dashboard opens **สร้างโครงการใหม่** (name, agency, ASCII budget, type, optional template) then routes to `/projects/{id}/draft`. Phase is persisted with `PATCH /projects/{id}/phase`. The leftover `/draft` index is not the primary intake path. `/chat` uses `kind=kb` (typing dots while streaming; `formatChatTimestamp` when `created_at` is present); Phase 0–1 uses `kind=draft_intake`.

Standalone `/review` extracts each compare file (`POST /review/extract`) then calls `POST /review/compare-projects` with `{ extract_ids }` (Jaccard). A 404/405/501 on that path falls back to local Jaccard on `extracted_text`. Errors use `role="alert"`; score &lt; 70 is shown as not meeting the threshold. Admin/officer list pages that used to swallow load failures now set `apiErrorMessage` + `role="alert"`.

Admin **การตั้งค่า AI** (`/admin/ai-settings`) lists every chat and embedding vendor in every mode — `on_prem` / `cloud` / `hybrid` is a label only and does **not** remap the other side. Mix example: Claude chat + local EmbeddingGemma (`LOCAL_EMBEDDING_SERVER`). Test (`ai-settings-test`) probes chat and embeddings separately. Cloud providers: Anthropic, OpenAI, Gemini, Bedrock, Azure Foundry, OpenAI-compatible. Help FAQ names `google/gemma-4-e4b` and `text-embedding-embeddinggemma-300m`. API error strings are read through `apiErrorMessage` in `src/lib/api-error.ts`. Review findings are mapped in `src/lib/review-findings.ts` so nested objects are never stringified to `[object Object]`.

There are **no Next.js pages** for `/api/v1/agent` or `/api/v1/kb-chat` in v0.2.0. The live UI stays on the 5-phase draft workspace and `/chat`. Those endpoints are backend-only until a later UI wave.

## UI testing

| Command | What it does |
|---------|----------------|
| `npm run test:unit` | Vitest + Testing Library (jsdom) |
| `npm run test:e2e:headed` | Playwright Chromium **visible** (`HEADED=1`, slowMo) against http://localhost:3000 |
| `npm run test:e2e:guide` | Extra screenshots for the user guideline (`CAPTURE_GUIDE=1`) |
| `npm run test:e2e:ui` | Playwright UI mode |

E2E specs live in `app/frontend/e2e/` with their own `e2e/tsconfig.json` (`types: ["node"]`) so opening a spec does not raise TS2580 on `Buffer`. They require `E2E=1` and a running UI (Docker or `next dev`) plus seed users. A locked Phase 2 chip uses `aria-disabled`; the walk-through clicks it with `{ force: true }` to prove the UI stays on Phase 0.

Stable selectors: `login-form`, `new-project`, `draft-page`, `phase-0`…`phase-4`, `intake-chat-panel`, `intake-upload`, `intake-confirm-ready`, `chat-page`, `chat-shell`, `nav-chat`, `help-tab-faq`, `nav-knowledge-base`, `nav-admin-ai-settings`, `admin-ai-settings-page`, `ai-settings-test`, `ai-settings-status`, `approve-project`, `reject-project`, `hitl-confirm-s3`.

## Build

Docker multi-stage: `npm ci` → `next build` → copy `.next/standalone` + static assets. After UI changes, rebuild the frontend image:

```bash
docker compose -p tor-app --env-file .env up -d --build frontend
```

`tsconfig.json` maps `@/*` with `"paths": { "@/*": ["./src/*"] }` (no `baseUrl` — that option makes Cursor’s bundled TypeScript 6 warn, and `"ignoreDeprecations": "6.0"` breaks Next 14 / TypeScript 5.4). Point the editor at the workspace compiler: status bar → TypeScript → **Use Workspace Version** (`.vscode/settings.json` sets `typescript.tsdk` to `app/frontend/node_modules/typescript/lib`).

Problems that name `frontend/...` or `backend/...` at the repo root are stale. Those folders are not on disk. Live sources are `app/frontend` and `app/backend`. Close leftover tabs, then **Developer: Reload Window**. SonarLint excludes only `frontend/**` and `backend/**` at the repo root — not `**/frontend/**`, which would skip this app tree. The root `tsconfig.json` lists `.vscode/tsconfig-placeholder.ts` so TypeScript does not raise TS18002 (`files` empty) and does not infer a project over leftover root paths.

Last headed run numbers and screenshots: `discussions/18-TEST_EVIDENCE.md`. User-facing walkthrough: `discussions/13-USER_GUIDELINE.md`. Playwright now includes `e2e/chat.spec.ts` (ถาม-ตอบ + intake upload).

`e2e/reports.spec.ts` and `e2e/guide-shots.spec.ts` stay out of `npm run test:e2e` unless `CAPTURE_REPORTS=1` / `CAPTURE_GUIDE=1`.

## Accessibility and Sonar

- Component props that Sonar flagged are `Readonly<...>`.
- Live E2E specs keep `test.skip(skipUnlessLive, …)` with a comment: they need a live stack and are skipped unless `E2E=1`.
- Playwright e2e is excluded from `sonar.sources`; Node globals come from `e2e/tsconfig.json` plus `import { Buffer } from "node:buffer"`.
- Password rules and review-finding mapping live in `src/lib/` so Vitest covers them without rendering pages.
- Nested ternaries in the draft editor were split into `ScopeSubsectionEditor`, `StandardSectionFields`, and `SectionFieldControl`.
- Date/money regexes on the backend stay `[0-9]`; Sonar `python:S6353` is ignored on purpose.
