# AshaShala — Phase-by-Phase Implementation Plan

> **Source**: `PROJECT_PROMPT.md` (master specification)
> **Status**: Planning — ready to execute Phase 1
> **Target**: 10,000+ GitHub stars, 100+ contributors, 50+ schools in 18 months

---

## Overview

| Phase | Focus | Duration | Key Deliverable |
|-------|-------|----------|-----------------|
| **1** | Foundation & Service Verification | 2-3 weeks | All external services connected, health endpoint green |
| **2** | Auth, RBAC, Tenancy, RAG Ingestion, Audit | 4-5 weeks | Full admin→school→teacher→student→parent CRUD skeleton |
| **3** | Tutor Agent + Dynamic Prompting + Voice | 3-4 weeks | Student asks question → gets streaming cited answer (Gujarati voice works) |
| **4** | Multi-Agent System (LangGraph) | 3-4 weeks | Quiz Master, Evaluator, Progress agents orchestrated |
| **5** | React Frontend (All 5 Roles) | 4-5 weeks | Real UI for every role, voice in/out, gamified quiz, clickable citations |
| **6** | Safety, Seed Data, Deploy, Polish | 2-3 weeks | Production-ready on $0/month, demo in one command |

**Total**: ~18-24 weeks to Phase 6 launch

---

## Phase 1 — Foundation (Weeks 1-3)

### Prerequisites (Do First)
- [ ] Create GitHub repo `ashashala/ashashala`
- [ ] Set up free-tier accounts:
  - [ ] Neon Postgres (0.5 GB)
  - [ ] Qdrant Cloud (1 GB)
  - [ ] Cloudflare R2 (10 GB)
  - [ ] Google AI Studio (Gemini API key)
  - [ ] NVIDIA NGC (NVIDIA API key)
  - [ ] Render (backend hosting)
  - [ ] Vercel (frontend hosting)
  - [ ] Sentry (error monitoring)
- [ ] Fill `config/model_registry.yaml` from live NVIDIA catalog: `https://build.nvidia.com/models?pageSize=96&filters=publisher%3Anvidia`

### Tasks

#### 1.1 Repo Setup
- [ ] Initialize git repo with `.gitignore` (FIRST — before any `.env`)
- [ ] Create folder structure per Section 12
- [ ] Add `.env.example` with ALL required vars
- [ ] Add `README.md` with setup instructions
- [ ] Configure pre-commit hooks (ruff, black, mypy, eslint, prettier)

#### 1.2 Config & Settings
- [ ] `app/core/config.py` — Pydantic Settings, loads all env vars, crashes if missing
- [ ] `app/core/exceptions.py` — Global exception handler → `{error_code, message, trace_id}`

#### 1.3 Database & Tenancy Foundation
- [ ] `app/db/session.py` — Async SQLAlchemy engine + session factory for Neon
- [ ] `app/db/tenant_filter.py` — SQLAlchemy event listener forcing `school_id` on every query

#### 1.4 Model Registry & LLM Clients
- [ ] `app/services/model_registry.py` — Loads YAML, `model_for(role, provider)` function
- [ ] `app/services/gemini_client.py` — Retry, backoff, timeout, `health_check()`
- [ ] `app/services/nvidia_client.py` — OpenAI SDK → NVIDIA base URL, per-model rate limit, `health_check()`

#### 1.5 LLM Router
- [ ] `app/services/llm_router.py` — Full routing table (Section 3), usage logging to `LlmUsage` table

#### 1.6 External Service Clients
- [ ] `app/services/r2_client.py` — Cloudflare R2 upload/delete/ping
- [ ] `app/services/rag/store.py` — Qdrant Cloud client, `ping_qdrant()`

#### 1.7 FastAPI App
- [ ] `app/main.py` — FastAPI factory, Sentry init, global exception handler mounted
- [ ] `GET /api/v1/health` — Returns status for all 7 services

#### 1.8 Tests
- [ ] `tests/test_phase1_health.py` — Hits `/api/v1/health`, asserts all "ok"
- [ ] `tests/test_phase1_llm_router.py` — 4 tests: English→Gemini, Gujarati→NVIDIA, 429 fallback, evaluate task

### Phase 1 Checkpoint
```
✅ /api/v1/health → all 7 services "ok" against real free-tier accounts
✅ model_registry.yaml filled with verified current model IDs
✅ Gemini client: gemini-2.5-flash-lite default (NOT 2.0-flash — shut down)
✅ NVIDIA client: health_check passes
✅ LLM router: Gujarati → Sarvam-M, English → Gemini Flash-lite, 429 fallback works
✅ Neon Postgres ping passes
✅ Qdrant Cloud ping passes
✅ Cloudflare R2 ping passes
✅ Sentry initialised (DSN in env, no crash on startup)
✅ Global exception handler installed
✅ .env gitignored, .env.example committed
✅ All Phase 1 tests pass
```

---

## Phase 2 — Auth, RBAC, Tenancy, RAG Ingestion, Timetables, Audit (Weeks 4-8)

### Prerequisites
- Phase 1 complete and verified
- All external services accessible

### Tasks

#### 2.1 Data Models & Migrations
- [ ] All SQLAlchemy models from Section 10 (one file per table in `app/models/`)
- [ ] Alembic first migration (`alembic revision --autogenerate -m "initial"`)
- [ ] Run migration against Neon

#### 2.2 Auth System
- [ ] `app/auth/jwt.py` — JWT access + refresh tokens (RS256)
- [ ] `app/auth/password.py` — bcrypt hashing via passlib
- [ ] `app/auth/routes.py` — `/login`, `/refresh`, `/me`, `/password-reset`
- [ ] JWT payload: `{sub, role, school_id, class_ids, subject_ids, linked_student_ids}`

#### 2.3 Dependencies & Authorization
- [ ] `app/deps.py` — `get_db`, `get_current_user`, `require_role(*roles)`, `get_tenant_db`
- [ ] Tenant-scoped DB session via SQLAlchemy event listener (inject `school_id` from JWT)

#### 2.4 Audit Logging
- [ ] `app/services/audit_service.py` — Decorator + middleware (automatic, not manual)
- [ ] All actions from Section 5 logged with correct schema

#### 2.5 Role Routes (Section 11)
- [ ] Super Admin: schools CRUD, create school admin, platform dashboard
- [ ] School Admin: users CRUD, CSV bulk import, classes/subjects, teacher assignments, enrollments, parent links, school dashboard, audit viewer
- [ ] Teacher: materials upload (file/URL/YouTube), timetable, exam timetable, dashboard, flagged answers, quiz approval
- [ ] Student: dashboard, chat (stub), classes, timetable, exam timetable, quizzes, progress, history, data export
- [ ] Parent: children list, per-child dashboard, history, timetable, exam timetable

#### 2.6 Feature Flags
- [ ] Check `School.features_json` before invoking voice/OCR/YouTube subsystems

#### 2.7 RAG Ingestion Pipeline (BackgroundTasks)
- [ ] `app/services/ingestion/` — pdf.py, docx.py, txt.py, url.py, youtube.py, image.py
- [ ] `app/services/rag/chunker.py` — ~600 tokens, ~100 overlap, retain metadata
- [ ] `app/services/rag/embedder.py` — Uses embed_router (Gemini for EN, NVIDIA for Indic)
- [ ] `app/services/rag/store.py` — Qdrant upsert with tenant-scoped collections
- [ ] Auto-create Qdrant collection on first school upload (idempotent, 768 dims, Cosine)
- [ ] Mirror chunk metadata in Postgres `chunks` table
- [ ] Scanned/image-only PDF pages → NVIDIA OCR → cache in `OcrCache`

#### 2.8 Parent Consent & Compliance
- [ ] `ParentStudentLink.consent_given_at` set at link time
- [ ] `/api/v1/student/data-export` — GDPR-style JSON export
- [ ] `/api/v1/admin/users/{id}/data` — Data deletion (Super Admin only)
- [ ] `docs/privacy.md` — One-page data retention + deletion + export policy

#### 2.9 Tests
- [ ] `test_phase2_rbac.py` — All role permissions work
- [ ] `test_phase2_tenant_isolation.py` — Cross-school access returns 404
- [ ] `test_phase2_rag.py` — Upload PDF → correct chunks in Qdrant
- [ ] `test_phase2_ingestion_url.py` — URL ingestion works
- [ ] `test_phase2_ingestion_youtube.py` — Timestamps present in chunks
- [ ] `test_phase2_timetable.py` — Timetable CRUD works
- [ ] `test_phase2_parent.py` — Read own child OK; read other child 403
- [ ] `test_phase2_audit.py` — Every action produces correct audit row

### Phase 2 Checkpoint
```
✅ All Phase 2 tests pass
✅ Manual smoke: Super Admin creates school → School Admin sets up class/subject/teacher/student/parent/timetable → Teacher uploads file+URL+YouTube → Parent sees child's name + timetable
✅ Cross-tenant isolation test passes (404, not 403)
✅ Audit log captures every action correctly
✅ RAG ingestion works for all 5 source types
✅ Feature flags gate subsystems correctly
```

---

## Phase 3 — Tutor Agent + Dynamic Prompting + Voice (Weeks 9-12)

### Prerequisites
- Phase 2 complete
- RAG ingestion working end-to-end
- Qdrant collections populated with test data

### Tasks

#### 3.1 Dynamic Prompt Builder
- [ ] `app/agents/prompts/tutor_prompt.py` — `build_tutor_prompt()` exactly as Section 6 (takes a `lang` arg)
- [ ] Mastery bands: <40 "just starting out", 40-70 "building confidence", >70 "nearly mastered"
- [ ] **Language rule**: reply entirely in the student's language (`lang` / `lang_detected`); citation tags left untranslated
- [ ] **Length budget** per mastery band (≤4 / ≤7 / ≤12 sentences) so low-mastery answers stay short
- [ ] **Earned-encouragement few-shot** (GOOD vs BAD praise example) baked into the prompt
- [ ] **Topic fallback**: when `topic` is None (free-form question), anchor to the subject, not a wrong guess
- [ ] Interest-based example selection
- [ ] Citation format rules for PDF/URL/YouTube

#### 3.2 Tutor Agent
- [ ] `app/agents/tutor.py` — LangGraph node
  - Detect language of question → `lang_detected`
  - Retrieve top-20 from Qdrant (filtered by class_id)
  - Assemble prompt → `build_tutor_prompt(..., lang=lang_detected)` → `llm_router.chat(task="explain", lang_hint=lang_detected)`
  - Parse citations with a **forgiving regex**, then map each source back to retrieved-chunk metadata to recover authoritative `page_or_ts` + R2 URL (never trust the model's page number)
  - Return `{answer, citations}`

#### 3.3 Safety Wrapper
- [ ] `app/agents/safety.py` — Topic-guard wrapper (Gemini built-in + prompt rule)
- [ ] Refuses off-subject questions, redirects to teacher

#### 3.4 Chat Endpoint (SSE)
- [ ] `POST /api/v1/student/chat` — SSE stream
- [ ] Final event: `event: citations` carries citation array
- [ ] Chat message audit log entry (hashed content + retrieved chunk IDs)

#### 3.5 Voice Endpoints
- [ ] `POST /api/v1/student/voice/stt` — Server-side fallback → NVIDIA ASR role
- [ ] `GET /api/v1/student/voice/tts` — Server-side fallback TTS → NVIDIA TTS role

#### 3.6 Tests
- [ ] `test_phase3_tutor.py` — Seed tiny PDF + URL + fake YouTube transcript; ask one question per source type; assert citation parsed correctly (forgiving parser tolerates spacing/casing/missing-field drift)
- [ ] `test_phase3_gujarati.py` — Gujarati question routes to Sarvam-M (or Maverick fallback); answer non-empty **and detected as Gujarati** (language rule holds)
- [ ] `test_phase3_length_budget.py` — mastery 35 answer respects the ≤4-sentence cap

### Phase 3 Checkpoint
```
✅ All Phase 3 tests pass
✅ Manual: curl POST /api/v1/student/chat with Accept: text/event-stream → see streaming tokens + final citations event
✅ Gujarati voice question routes to Sarvam-M and produces non-empty answer THAT IS IN Gujarati (not English)
✅ Citations correct for PDF (page), URL (title+url), YouTube (title+timestamp+url); forgiving parser survives format drift
✅ Dynamic prompt adapts to mastery band + length budget (test with mastery 35, 55, 80)
✅ Safety wrapper blocks off-topic questions
```

---

## Phase 4 — Multi-Agent System (LangGraph) (Weeks 13-16)

### Prerequisites
- Phase 3 complete
- Tutor agent working with streaming + citations

### Tasks

#### 4.1 Shared State
- [ ] `app/agents/state.py` — `SessionState` TypedDict from Section 7.1

#### 4.2 Orchestrator
- [ ] `app/agents/orchestrator.py` — Intent classifier (cheap fast_chat call)
- [ ] Routes to: Tutor, QuizMaster, Evaluator, Progress

#### 4.3 Quiz Master Agent
- [ ] `app/agents/quiz_master.py` — Weakest-topic quiz, 3 MCQ + 2 short-answer
- [ ] Difficulty + XP per question
- [ ] Persists to `quizzes` table with `status = "draft"`
- [ ] Teacher approves → `status = "approved"`

#### 4.4 Evaluator Agent
- [ ] `app/agents/evaluator.py` — Grades free-text against retrieved source
- [ ] Returns `{score: 0-1, feedback, missed_concepts, confidence}`
- [ ] Uses `llm_router.chat(task="evaluate")` → reasoning role
- [ ] If `score < 0.4` AND `confidence < 0.7` → flag for teacher review queue

#### 4.5 Progress Agent
- [ ] `app/agents/progress.py` — EMA mastery update
- [ ] `new_score = round(0.7 * old_score + 0.3 * attempt_score * 100)`
- [ ] Topic extraction via keyword extraction (Phase 4) → embedding-based later

#### 4.6 LangGraph Wiring
- [ ] `app/agents/graph.py` — `safety_in → orchestrator → {tutor|quiz|evaluator} → safety_out → progress → END`
- [ ] `app/agents/prompts/quiz_prompt.py`, `eval_prompt.py` — Same mastery-aware, encouraging style

#### 4.7 New Routes
- [ ] `POST /api/v1/student/quiz/start`
- [ ] `POST /api/v1/student/quiz/{id}/submit`
- [ ] `GET /api/v1/student/progress`
- [ ] `GET /api/v1/teacher/flagged-answers`
- [ ] `POST /api/v1/teacher/flagged-answers/{id}/override`
- [ ] `POST /api/v1/teacher/quizzes/{id}/approve`

#### 4.8 Tests
- [ ] `test_phase4_agents.py` — Full loop: ask → quiz → submit → mastery updates → next quiz pulls weakest topic → teacher flags queue populated

### Phase 4 Checkpoint
```
✅ All Phase 4 tests pass
✅ Full loop works in curl: student asks → gets quiz → submits → mastery updates → next quiz targets weakest topic
✅ Teacher flagged-answers queue populated for low-confidence grades
✅ Quiz Master generates from weakest mastery topic
✅ Evaluator uses reasoning model (gemini-2.5-flash → NVIDIA fallback)
✅ Progress agent updates mastery with EMA formula
```

---

## Phase 5 — React Frontend (All 5 Roles) (Weeks 17-21)

### Prerequisites
- Phase 4 complete
- All API endpoints working and tested

### Tasks

#### 5.1 Project Setup
- [ ] `frontend/` — React 18 + Vite + TailwindCSS + TypeScript
- [ ] `package.json`, `tailwind.config.ts`, `vite.config.ts`
- [ ] `vercel.json` — SPA rewrite rules, `VITE_API_URL` from env
- [ ] Typed API client from FastAPI OpenAPI schema

#### 5.2 Auth & Routing
- [ ] Login page, JWT in memory + refresh token in httpOnly cookie
- [ ] Redirect-by-role after login
- [ ] `RoleGuard` component on every protected route
- [ ] Zustand stores: auth, voice settings

#### 5.3 Super Admin UI
- [ ] Schools table (create/suspend/delete)
- [ ] Platform metrics card (active schools, total users, LLM tokens today per school from `LlmUsage`)

#### 5.4 School Admin UI
- [ ] Users tab (filter by role)
- [ ] Classes & Subjects management
- [ ] Teacher Assignments
- [ ] Enrollments (CSV upload)
- [ ] Parent Links
- [ ] School Dashboard: Recharts per-class mastery bar chart, engagement
- [ ] Audit Log viewer (filter by action type + date range)

#### 5.5 Teacher UI
- [ ] My Classes & Subjects
- [ ] Materials: tabbed (File drag-drop + URL paste + YouTube paste + preview)
- [ ] Regular Timetable grid (weekly)
- [ ] Exam Timetable list
- [ ] Class Progress table (per-student mastery)
- [ ] Flagged Answers queue (review + override grade)

#### 5.6 Student UI
- [ ] Dashboard: MasteryRadar (Recharts), today's periods, upcoming exams, recommended next topic
- [ ] Chat:
  - Text input + send, streaming answer via SSE
  - Push-to-talk mic button using `SpeechRecognition` (Web Speech API)
  - Browser fallback → audio uploaded to `/student/voice/stt`
  - TTS toggle: streamed answer spoken via `SpeechSynthesis`
  - Server fallback: `/student/voice/tts`
  - Voice settings (rate, pitch, voice) in Zustand + localStorage
  - Citations render as chips: PDF opens at page via R2 URL; YouTube opens at timestamp; URL opens in new tab
- [ ] Quiz Games: countdown timer, streak counter, XP gain animation, level-up modal, badges
- [ ] History: all chats, all quiz attempts, all mastery changes

#### 5.7 Parent UI
- [ ] Children list → per-child dashboard (MasteryRadar, read-only)
- [ ] History feed, timetable

#### 5.8 Polish
- [ ] Loading skeletons + error toasts + empty states everywhere
- [ ] Web Speech API degrades gracefully (hide mic button + show tooltip if unsupported)
- [ ] Responsive design (mobile-first for student/parent)

### Phase 5 Checkpoint
```
✅ End-to-end browser demo:
  1. Super Admin creates school
  2. School Admin sets up teacher/student/parent
  3. Teacher uploads PDF + YouTube + timetable
  4. Student asks voice question → hears answer
  5. Student clicks YouTube citation at correct timestamp
  6. Student takes quiz → earns XP → level up
  7. Parent sees updated mastery
✅ All 5 roles have functional UI
✅ Voice in/out works in Chrome/Edge/Firefox
✅ Citations clickable and correct
✅ Gamified quiz engaging
```

---

## Phase 6 — Safety, Seed Data, Deploy, Polish (Weeks 22-24)

### Prerequisites
- Phase 5 complete
- Full stack working locally

### Tasks

#### 6.1 Safety Hardening
- [ ] Test Gemini's built-in safety fires on inappropriate messages
- [ ] Add rate-limiting with `slowapi` on chat endpoint (protect free Gemini quota)
- [ ] Document safety behavior in `docs/safety.md`

#### 6.2 Seed Data Script
- [ ] `scripts/seed.py` — Idempotent:
  - 1 school, 1 school admin, 2 teachers, 6 students (mix of grades/mastery)
  - 2 parents each linked to different student
  - Sample PDF + YouTube URL pre-ingested and indexed
  - Prints demo credentials to console

#### 6.3 Cost Monitoring
- [ ] LLM cost mini-dashboard: query over `LlmUsage` in School Admin dashboard
- [ ] Tokens used per provider per day, over-quota warnings

#### 6.4 Documentation
- [ ] `docs/privacy.md` — Data retention + deletion + export policy
- [ ] `docs/runbook.md` — "If X breaks, do Y" for 5 failure modes:
  - Neon connectivity
  - Qdrant 503
  - Gemini quota exhausted
  - Render cold start
  - R2 upload failure
- [ ] Backup documentation: Neon PITR window, Qdrant snapshot export tested, restore procedure

#### 6.5 Docker & Deploy
- [ ] `Dockerfile` — Multi-stage build, confirmed building cleanly
- [ ] `deploy/render.yaml` — Render free Web Service, Docker, auto-deploy from `main`
- [ ] `deploy/northflank.json` — Alternative always-on deploy config
- [ ] `.github/workflows/ci.yml` — `pytest` + `vitest` on every PR
- [ ] `.github/workflows/deploy.yml` — Build Docker image on `main` → push GHCR → trigger Render redeploy via webhook

#### 6.6 README Final Polish
- [ ] Architecture diagram
- [ ] One-command local setup
- [ ] Demo credentials
- [ ] Render cold-start tradeoff documented
- [ ] How to re-verify `model_registry.yaml` against live NVIDIA catalog

#### 6.7 Pre-commit Hooks
- [ ] ruff, black, mypy, eslint, prettier

### Final Pre-Launch Checklist
```
✅ Real scanned-PDF page ingests correctly via NVIDIA OCR
✅ Cross-tenant access returns 404 in test_phase2_tenant_isolation.py
✅ Gujarati voice question routes to Sarvam-M and produces non-empty Gujarati answer
✅ Fractions worked example produces encouraging, example-first answer (not textbook wall)
✅ PDF citation chip opens original file from R2 at correct page
✅ YouTube citation chip opens at correct timestamp
✅ /api/v1/health fully green against live free-tier accounts
✅ .env gitignored, .env.example committed with all vars
✅ Backup restore tested once (not just documented)
✅ Data export endpoint returns valid JSON
✅ Data deletion endpoint actually removes rows + Qdrant points + R2 file
✅ Render cold-start tradeoff documented in README
✅ Demo seed script works in one command and prints login credentials
```

---

## Dependency Graph

```
Phase 1 (Foundation)
    │
    ├──→ Phase 2 (Auth, RBAC, Tenancy, RAG, Audit)
    │       │
    │       ├──→ Phase 3 (Tutor Agent + Voice)
    │       │       │
    │       │       └──→ Phase 4 (Multi-Agent LangGraph)
    │       │               │
    │       │               └──→ Phase 5 (React Frontend)
    │       │                       │
    │       │                       └──→ Phase 6 (Deploy, Polish)
    │       │
    │       └──→ (Parallel) Docs: PURPOSE, GOVERNANCE, ROADMAP, CONTRIBUTING, CODE_OF_CONDUCT
    │
    └──→ (Parallel) Community docs creation ✅ DONE
```

---

## Risk Mitigation

| Risk | Phase Impact | Mitigation |
|------|--------------|------------|
| NVIDIA model IDs deprecated | All phases | Check catalog before each phase; `model_registry.yaml` is single source of truth |
| Free tier limits exceeded | Phase 1-6 | Multi-cloud strategy; document limits; implement rate limiting early |
| Render cold start (15s) | Phase 5-6 | Document tradeoff; Northflank alternative; keep-alive ping if needed |
| Gujarati/Hindi model quality | Phase 3-4 | Test early; have Maverick fallback; involve native speakers |
| Cross-tenant leakage | Phase 2 | SQLAlchemy event listener + Qdrant filter + integration test (404 not 403) |
| Contributor onboarding friction | Phase 5-6 | Good first issues, dev container, mentor program, clear CONTRIBUTING.md |

---

## Success Metrics per Phase

| Phase | Metric | Target |
|-------|--------|--------|
| 1 | Health endpoint | All 7 services "ok" |
| 2 | RBAC test coverage | 100% of permission matrix |
| 2 | Tenant isolation | Cross-school 404 verified |
| 3 | Tutor citation accuracy | 100% correct format per source type |
| 3 | Gujarati response quality | Non-empty, encouraging, cited |
| 4 | Agent loop | Full ask→quiz→mastery→next quiz works |
| 5 | E2E browser demo | All 5 roles functional |
| 6 | Deploy | $0/month on free tiers |

---

## Next Action

**Start Phase 1 now:**

1. Open `https://build.nvidia.com/models?pageSize=96&filters=publisher%3Anvidia`
2. Fill `config/model_registry.yaml` with current model IDs for all 8 roles
3. Create repo structure per Section 12
4. Implement Phase 1 tasks in order
5. Run tests, verify checkpoint, then stop and wait for "go"

---

*This plan is derived from `PROJECT_PROMPT.md`. Update this document as phases complete.*