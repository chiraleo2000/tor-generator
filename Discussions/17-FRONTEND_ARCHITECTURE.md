# Frontend architecture

Next.js 14 App Router in `app/frontend`. Production image is standalone Node on port **3000**.

## Request path

Browser JavaScript calls **same-origin** `/api/v1/...`. `next.config.js` rewrites that to `BACKEND_INTERNAL_URL` (`http://backend:4000/api/v1` in Docker). Do not set `NEXT_PUBLIC_API_URL` to the Docker hostname `backend` — the browser cannot resolve it.

Axios `apiClient` uses `withCredentials: true` so the HttpOnly cookie `tor_access_token` is sent. If the in-memory store still has a token (returned in the login JSON), it is also sent as `Authorization: Bearer`. A 401 clears the session and sends the browser to `/login`.

## Route groups

| Group | Routes | Guard |
|-------|--------|--------|
| Public | `/` | Redirects guests to `/login` |
| Auth | `/login`, `/register` | Guest layout (navy card) |
| App | `/projects`, `/projects/[id]/draft`, `/draft`, `/knowledge-base`, `/review`, `/help` | `AuthGuard` + 255px navy sidebar |
| Compat | `/projects/[id]/wizard/[step]`, `/wizard/[step]` | Redirect into the 5-phase draft |
| Admin | `/admin/templates`, `/admin/knowledge-base`, `/admin/users`, `/admin/ai-settings` | Admin layout redirects non-admins |

Main nav: แดชบอร์ด, ฐานความรู้, ร่าง TOR, ตรวจสอบ TOR, คู่มือ. Admin cluster is below. Creating a project opens a form (name, agency, budget, type) then `/projects/{id}/draft`. Reviewer/admin see **อนุมัติ** / **ส่งกลับ** on `in_review` rows (`decideProject` → `POST /projects/{id}/approve|reject`). Officers cannot edit while a project is in review. Phase 3 submit is disabled until 13 sections are filled **and** HITL sections are confirmed.

## Client state (Zustand)

| Store | Responsibility |
|-------|----------------|
| `auth-store` | In-memory user + optional token; `restoreSession` calls `GET /auth/me` using the cookie. JWT is **not** persisted to localStorage |
| `project-store` | Project list, active project, create/update/submit |
| `wizard-store` | Kept for leftover step helpers; the live editor is `DraftWorkspace` |
| `ui-store` | Theme, sidebar, toasts (theme/sidebar persisted) |

## 5-phase workspace

`DraftWorkspace` (`src/components/draft/draft-workspace.tsx`) is the drafting UI.

| Phase | UI |
|-------|-----|
| 0 | Classified upload areas + mapping-box + confirm apply |
| 1 | Requirements / SLA / Q&A / stakeholders |
| 2 | Flow-track of 13 sections; s4 chips; HITL confirm vs save; AI draft |
| 3 | Completeness + Rule Engine + submit |
| 4 | Word / PDF export |

Create-project from the dashboard opens **สร้างโครงการใหม่** (name, agency, ASCII budget, type, optional template) then routes to `/projects/{id}/draft`. Phase is persisted with `PATCH /projects/{id}/phase`. The leftover `/draft` index is not the primary intake path.

Standalone review extracts each compare file (`POST /review/extract`) then calls `POST /review/compare-projects` with `{ extract_ids }` (Jaccard). A 404/405/501 on that path falls back to local Jaccard on `extracted_text`.

Admin **การตั้งค่า AI** (`/admin/ai-settings`) toggles Local vs Cloud vs Hybrid, tests connectivity (`ai-settings-test`), and saves to Postgres. Help FAQ names `google/gemma-4-e4b` and `text-embedding-embeddinggemma-300m`. API error strings are read through `apiErrorMessage` in `src/lib/api-error.ts`. Review findings are mapped in `src/lib/review-findings.ts` so nested objects are never stringified to `[object Object]`.

## UI testing

| Command | What it does |
|---------|----------------|
| `npm run test:unit` | Vitest + Testing Library (jsdom) |
| `npm run test:e2e:headed` | Playwright Chromium **visible** (`HEADED=1`, slowMo) against http://localhost:3000 |
| `npm run test:e2e:guide` | Extra screenshots for the user guideline (`CAPTURE_GUIDE=1`) |
| `npm run test:e2e:ui` | Playwright UI mode |

E2E specs live in `app/frontend/e2e/`. They require `E2E=1` and a running UI (Docker or `next dev`) plus seed users.

Stable selectors: `login-form`, `new-project`, `draft-page`, `phase-0`…`phase-4`, `help-tab-faq`, `nav-knowledge-base`, `nav-admin-ai-settings`, `admin-ai-settings-page`, `ai-settings-test`, `ai-settings-status`, `approve-project`, `reject-project`, `hitl-confirm-s3`.

## Build

Docker multi-stage: `npm ci` → `next build` → copy `.next/standalone` + static assets. After UI changes, rebuild the frontend image:

```bash
docker compose -p tor-app --env-file .env up -d --build frontend
```

`tsconfig.json` maps `@/*` with `"paths": { "@/*": ["./src/*"] }` (no `baseUrl` — that option makes Cursor’s bundled TypeScript 6 warn, and `"ignoreDeprecations": "6.0"` breaks Next 14 / TypeScript 5.4). Point the editor at the workspace compiler: status bar → TypeScript → **Use Workspace Version** (`.vscode/settings.json` sets `typescript.tsdk` to `app/frontend/node_modules/typescript/lib`).

Problems that name `frontend/...` or `backend/...` at the repo root are stale. Those folders are not on disk. Live sources are `app/frontend` and `app/backend`. Close leftover tabs, then **Developer: Reload Window**. SonarLint excludes only `frontend/**` and `backend/**` at the repo root — not `**/frontend/**`, which would skip this app tree. The root `tsconfig.json` lists `.vscode/tsconfig-placeholder.ts` so TypeScript does not raise TS18002 (`files` empty) and does not infer a project over leftover root paths.

Last headed run against Docker `http://localhost:3000` (**18 Aug 2026**): Playwright **13 passed**; extra guide shots via `npm run test:e2e:guide`. Vitest: **104 passed** / **92.47%** statements covering `src/lib`, `src/stores`, and the Admin AI settings page. Screenshots and per-test notes: `discussions/18-TEST_EVIDENCE.md`. User-facing walkthrough: `discussions/13-USER_GUIDELINE.md`.

`e2e/reports.spec.ts` and `e2e/guide-shots.spec.ts` stay out of `npm run test:e2e` unless `CAPTURE_REPORTS=1` / `CAPTURE_GUIDE=1`.

## Accessibility and Sonar

- Component props that Sonar flagged are `Readonly<...>`.
- Live E2E specs keep `test.skip(skipUnlessLive, …)` with a comment: they need a live stack and are skipped unless `E2E=1`.
- Password rules and review-finding mapping live in `src/lib/` so Vitest covers them without rendering pages.
- Nested ternaries in the draft editor were split into `ScopeSubsectionEditor`, `StandardSectionFields`, and `SectionFieldControl`.
- Date/money regexes on the backend stay `[0-9]`; Sonar `python:S6353` is ignored on purpose.
