# Roadmap

## Project Name: AshaShala

This roadmap describes the project phases, community growth plan, and milestones for reaching 10,000+ GitHub stars.

---

## Phase 1: Foundation (Months 1-3)
**Goal**: Core platform ready for early contributors and integration testing

### Backend
- [ ] FastAPI project structure with Poetry/uv
- [ ] Neon Postgres schema: tenants, users, roles, schools, classes, students
- [ ] SQLAlchemy + Qdrant Cloud setup (1GB free tier)
- [ ] Cloudflare R2 bucket setup (10GB free tier)
- [ ] Health checks, global exception handling, service pings
- [ ] Structured logging (structlog) + OpenTelemetry traces

### Auth & Tenancy
- [ ] JWT auth with refresh tokens (RS256)
- [ ] Row-level security policies for multi-tenant isolation
- [ ] Role enum: SuperAdmin, SchoolAdmin, Teacher, Student, Parent
- [ ] Invitation flow for school onboarding

### Model Registry & LLM Router
- [ ] Model registry (YAML/DB): provider, model_id, capabilities, cost, tier
- [ ] LLM Router: task → model mapping with fallback chain
- [ ] Providers: Gemini API (free), NVIDIA NIM (free), local Ollama
- [ ] Token budget tracking per request

### DevEx
- [ ] `.env.example` with all required variables
- [ ] Docker Compose for local dev (Postgres, Qdrant, MinIO for R2)
- [ ] Makefile/Justfile for common tasks
- [ ] Pre-commit hooks (ruff, mypy, black, prettier)
- [ ] GitHub Actions CI: lint, typecheck, test, build

### Documentation
- [ ] Architecture decision records (ADRs) in `docs/adr/`
- [ ] Setup guide for new contributors
- [ ] API reference (auto-generated from FastAPI)

---

## Phase 2: Roles, Tenancy, and Ingestion (Months 3-6)
**Goal**: First school deployment and teacher workflow

### RBAC & Audit
- [ ] Permission matrix per role (CRUD per resource)
- [ ] Audit log table: immutable, append-only, signed
- [ ] Audit events: login, data access, AI calls, grading, exports
- [ ] GDPR/PDPB compliance helpers (data export, deletion)

### Material Ingestion Pipeline
- [ ] Upload API: PDF, DOCX, TXT, MD, URL, YouTube
- [ ] Text extraction: PyMuPDF, python-docx, trafilatura, yt-dlp
- [ ] Chunking strategy: semantic (by heading) + fixed-size fallback
- [ ] Embeddings: NVIDIA NIM (free) or local sentence-transformers
- [ ] Qdrant upsert with tenant-scoped collections
- [ ] Ingestion status tracking + retry logic
- [ ] Teacher UI: drag-drop upload, progress, re-ingest

### School Admin Features
- [ ] School profile, branding, locale settings
- [ ] User management: invite teachers, bulk import students (CSV)
- [ ] Class/section management
- [ ] Curriculum mapping: subjects → chapters → topics

---

## Phase 3: Tutor and Voice (Months 6-9)
**Goal**: Student-facing AI experience with real citations

### Tutor Agent
- [ ] LangGraph state machine: retrieve → reason → respond → cite
- [ ] Dynamic system prompt per role/grade/subject/language, with a mastery-band length budget and an explicit "reply in the student's language" rule (see PROJECT_PROMPT.md §6 — the canonical spec)
- [ ] Few-shot examples per concept type (incl. earned-encouragement GOOD/BAD example)
- [ ] Source citation format: human-readable `[source: filename.pdf, p. 12]` / URL / YouTube-timestamp per PROJECT_PROMPT.md §6, parsed with a forgiving regex and mapped back to chunk metadata → hover shows snippet
- [ ] Guardrails: no hallucination, refuse out-of-scope, escalate to teacher

### Chat & Streaming
- [ ] WebSocket `/chat/stream` with Server-Sent Events fallback
- [ ] Message persistence (tenant-scoped)
- [ ] Conversation history with branching (student can explore alternatives)
- [ ] Teacher view: read-only access to student chats

### Voice Interface
- [ ] STT: Web Speech API (browser) + Whisper.cpp (server fallback)
- [ ] TTS: Coqui TTS (local) or browser SpeechSynthesis
- [ ] Voice activity detection, push-to-talk, auto-send
- [ ] Gujarati/Hindi voice models (Indic TTS)
- [ ] Offline-first: cache TTS audio in R2

### Multilingual
- [ ] i18n infrastructure: JSON locale files, ICU message format
- [ ] Languages: English, Gujarati, Hindi (Phase 3), + Marathi, Tamil, Telugu, Bengali (Phase 5)
- [ ] RTL support for future Arabic/Urdu
- [ ] Language detection from user input → route to appropriate model

---

## Phase 4: Multi-Agent System (Months 9-12)
**Goal**: Intelligent tutoring loop, not just chat

### Agent Orchestrator
- [ ] LangGraph supervisor: routes to specialized agents
- [ ] Shared state: student profile, mastery, conversation context

### Quiz Master Agent
- [ ] Generate questions from ingested material (Bloom's taxonomy)
- [ ] Question types: MCQ, short answer, fill-blank, matching
- [ ] Difficulty adaptation based on mastery
- [ ] Quiz session: timed, practice, exam modes

### Evaluator Agent
- [ ] Auto-grade short answers with rubric (LLM-as-judge)
- [ ] Partial credit, feedback with citations
- [ ] Teacher review queue for subjective answers
- [ ] Calibration: teacher grades sample → align LLM grader

### Progress Tracker Agent
- [ ] Mastery model: Bayesian knowledge tracing per concept
- [ ] Dashboard: student, class, school views
- [ ] Intervention alerts: struggling students, concepts needing reteach
- [ ] Parent digest: weekly progress email (opt-in)

### Teacher Tools
- [ ] Assignment builder: pick topics → auto-generate quiz
- [ ] Class analytics: heatmaps, mastery distributions
- [ ] Lesson plan assistant: suggest activities, misconceptions

---

## Phase 5: Open Source Community Launch (Months 12-15)
**Goal**: 1,000 stars, active contributor base

### Polish & Harden
- [ ] E2E tests: Playwright for critical user flows
- [ ] Load testing: 100 concurrent students per school
- [ ] Security audit: OWASP Top 10, dependency scan
- [ ] Accessibility audit: WCAG 2.1 AA

### Contributor Experience
- [ ] `good first issue` labels on 20+ issues
- [ ] Contributor guide with video walkthrough
- [ ] Dev container / GitHub Codespaces config
- [ ] Mentorship program: "First PR" buddies

### Community Launch
- [ ] Launch blog post + Hacker News / Reddit / Twitter
- [ ] Discord server with roles, onboarding flow
- [ ] Monthly community calls (recorded)
- [ ] Swag: stickers, t-shirts for contributors
- [ ] Conference talks: PyCon India, FOSSASIA, etc.

### Localization Sprint
- [ ] Translation platform: Weblate or Crowdin (free for open source)
- [ ] Gujarati, Hindi, Marathi, Tamil, Telugu, Bengali
- [ ] Community translation events

---

## Phase 6: Scale and Sponsorship (Months 15-18)
**Goal**: 10,000+ stars, 100+ contributors, real school users

### Production Hardening
- [ ] Blue-green deploy on Render/Vercel
- [ ] Database migration strategy (Alembic)
- [ ] Backup/restore runbook (R2 + Neon point-in-time)
- [ ] Disaster recovery drill
- [ ] Sentry error tracking (free tier)
- [ ] Uptime monitoring (UptimeRobot free)

### Scale Features
- [ ] Multi-region: Neon read replicas, Qdrant Cloud clusters
- [ ] Caching: Redis (Upstash free tier) for sessions, embeddings
- [ ] Background jobs: Celery + Redis for ingestion, grading
- [ ] Webhooks: school LMS integration (Google Classroom, Moodle)

### Content Ecosystem
- [ ] Lesson package format (JSON + media) → import/export
- [ ] Community lesson marketplace (free, CC-BY)
- [ ] 100+ classroom-ready lesson packages
- [ ] Curriculum alignment: CBSE, ICSE, State boards

### Sustainability
- [ ] OpenCollective / GitHub Sponsors
- [ ] Grant applications: Google.org, Mozilla, UNICEF Innovation
- [ ] Corporate sponsorships (infrastructure credits)
- [ ] Annual budget transparency report

### Metrics Dashboard (Public)
- [ ] Stars, contributors, PRs, issues over time
- [ ] Schools deployed, students active, languages
- [ ] Community health: time-to-first-review, contributor retention

---

## Community Growth Plan (Parallel to All Phases)

### Awareness
- **Month 1-3**: Technical blog posts (architecture, RAG, agents)
- **Month 3-6**: Demo videos, teacher testimonials
- **Month 6-9**: Student success stories, voice demo
- **Month 9-12**: Multi-agent deep dives
- **Month 12+**: Case studies from pilot schools

### Contributor Acquisition
- **Good First Issues**: 20+ at all times, labeled by area
- **Hackathons**: Quarterly (virtual), themed (i18n, agents, voice)
- **Google Summer of Code**: Apply as mentoring org (Year 2)
- **University Partnerships**: Capstone projects, research collabs

### Community Retention
- **Welcome Bot**: Auto-assign mentor, link to guide
- **Contributor Spotlight**: Monthly blog/social
- **Swag Tiers**: 1 PR = sticker, 5 PRs = t-shirt, 20 PRs = hoodie
- **Maintainer Path**: Clear criteria, nomination process

### School Adoption
- **Pilot Program**: 5 schools (Phase 2), 20 schools (Phase 4), 50+ (Phase 6)
- **Teacher Training**: Free workshops, certification
- **Parent Communication**: Multilingual consent forms, progress reports
- **Data Privacy**: DPA templates, on-prem deployment guide

---

## Success Metrics

| Metric | Phase 3 | Phase 5 | Phase 6 (18 mo) |
|--------|---------|---------|-----------------|
| GitHub Stars | 100 | 1,000 | **10,000+** |
| Contributors | 10 | 50 | **100+** |
| Schools Deployed | 1 (pilot) | 5 | **50+** |
| Languages | 3 | 6 | **10+** |
| Lesson Packages | 10 | 50 | **100+** |
| Active Students | 50 | 500 | **5,000+** |
| PRs Merged/Month | 20 | 100 | **300+** |
| Time to First Review | <7 days | <3 days | **<48 hrs** |

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Free tier limits exceeded | Medium | High | Multi-cloud strategy, self-host docs, sponsorships |
| Contributor burnout | Medium | High | Shared ownership, mentorship, sustainable pace |
| Security vulnerability | Low | Critical | Dependency scanning, bug bounty, rapid patch |
| School adoption slow | High | High | Pilot program, teacher champions, offline-first |
| AI quality complaints | Medium | Medium | Teacher review loop, eval benchmarks, transparency |

---

## Milestone Gates

### Gate 1 (End of Phase 1): "Contributor Ready"
- CI passes, docs complete, 3+ external contributors onboarded

### Gate 2 (End of Phase 2): "School Ready"
- Pilot school onboarded, teacher creates assignment, student takes quiz

### Gate 3 (End of Phase 3): "Student Ready"
- Student chats with tutor in Gujarati/Hindi, gets cited answers, voice works

### Gate 4 (End of Phase 4): "Intelligent Loop"
- Quiz → grade → mastery update → intervention alert → teacher action

### Gate 5 (End of Phase 5): "Community Launched"
- 1,000 stars, 50 contributors, Discord active, monthly calls running

### Gate 6 (End of Phase 6): "Sustainable Scale"
- 10,000 stars, 100 contributors, 50 schools, grant funding secured

---

*Roadmap is a living document. Propose changes via RFC in `docs/rfcs/`.*
