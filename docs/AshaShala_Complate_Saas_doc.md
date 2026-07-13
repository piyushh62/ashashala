# AshaShala — Complete SaaS Master Document
## Fully Dynamic, Fully Agentic AI Education Platform
### Architecture · Roles & Permissions · Agent Mesh · Frontend & Backend Spec · Roadmap

**This is the single source-of-truth document**, merging all prior analysis:
- Part 1–13: Vision, current-state audit, dynamic RBAC design, agent architecture, gaps, compliance, phased roadmap
- Part 14–20: Every dashboard page, table, form, field, and backend API (current vs. target) for all 5 roles

Based on direct audit of `piyushh62/ashashala` (backend routes, models, agents, frontend pages) + industry research, as of July 2026.

## Table of Contents

**Architecture & Strategy**
- Part 1 — Vision Recap
- Part 2 — Current State (Ground Truth)
- Part 3 — Dynamic Role, Permission & CRUD-Hierarchy Architecture
- Part 4 — Dynamic Dashboards (principle)
- Part 5 — Full Agent Mesh (existing + new agents, governance)
- Part 6 — Data Model Additions Needed
- Part 7 — Notification Channels (India context: SMS/WhatsApp)
- Part 8 — Security, Privacy & Compliance
- Part 9 — Non-Functional Considerations
- Part 10 — Business/Extensibility Considerations
- Part 11 — Consolidated Gap Table
- Part 12 — Phased Roadmap (pilot-aware)
- Part 13 — Immediate Next Step

**Frontend + Backend Complete Spec**
- Part 14 — Super Admin (pages, tables, forms, APIs)
- Part 15 — School Admin (pages, tables, forms, APIs)
- Part 16 — Teacher (pages, tables, forms, APIs)
- Part 17 — Student (pages, tables, forms, APIs)
- Part 18 — Parent (pages, tables, forms, APIs)
- Part 19 — Shared/Cross-Role Components
- Part 20 — Summary: All New Backend Endpoints Needed

---


## Part 1 — Vision Recap

A SaaS education platform where:
- **Only Super Admin role is fixed**; every other role (School Admin, Teacher, Student, Parent, and any future role like Accountant/Librarian) is **dynamically defined per school** — no hardcoded roles in code.
- **CRUD hierarchy cascades naturally**: Super Admin → School → Classes → Teachers (mapped) → Students (mapped) → Parents (mapped) — and *who* is allowed to create *what* is itself a **permission**, not a hardcoded rule.
- **Every role has its own dashboard**, showing only what its permissions allow — dynamically, not a fixed React page-per-role.
- **AI is proactive everywhere**, not just a chatbot: timetable suggestions, schedule-driven learning, auto-reports — always with a human-approval step for anything consequential.
- Currently pre-monetization: **5–10 pilot users, free-tier LLM APIs only**, paid keys added later.

---

## Part 2 — Current State (Ground Truth, from code)

| Layer | Exists | Confirmed detail |
|---|---|---|
| Backend | ✅ | FastAPI, async SQLAlchemy, Alembic, LangGraph, Qdrant |
| Roles | ⚠️ Hardcoded | `UserRole(str, enum.Enum)` — 5 fixed values in Python |
| Who can create users | ⚠️ Hardcoded | Only `school_admin` role; `_CREATABLE = {teacher, student, parent}` hardcoded set — **teacher cannot create students/parents today** |
| Class/Subject/Enrollment/TeacherAssignment/ParentStudentLink | ✅ | Full CRUD exists, tenant-scoped |
| AI Agents | ✅ (reactive only) | Tutor, Quiz Master, Evaluator, Progress — all triggered by student chat message |
| Orchestrator | ⚠️ | Pure intent classifier (`explain\|quiz\|grade\|progress`), not a supervisor |
| Scheduler/event bus | ❌ | None — no Celery, no APScheduler, no pub/sub |
| Timetable | ⚠️ Manual only | Plain CRUD, zero AI involvement |
| Safety layer | ✅ | Keyword block + subject guard + optional NeMo-Guard jailbreak classifier — solid |
| Notifications | ⚠️ In-app only | No SMS/WhatsApp/email channel field on `Notification` model |
| i18n (frontend UI) | 🟡 Chrome only | `react-i18next` wired with en/hi/gu locale files; nav, layout chrome, Login, Settings translated + language switcher in Settings. ~50 remaining route/component files still hardcoded English |
| Audit log | ✅ | Exists, immutable pattern |
| Feature flags | ✅ | `School.features_json` — reusable for optional modules (Fee, etc.) |
| Frontend pages per role | ⚠️ Fixed | Admin (2), School Admin (4), Teacher (4), Student (4), Parent (2) — hardcoded React routes, not permission-driven |

---

## Part 3 — Dynamic Role, Permission & CRUD-Hierarchy Architecture

### 3.1 Schema (replaces the enum)

```sql
CREATE TABLE role_templates (id UUID PK, name TEXT UNIQUE, is_system BOOLEAN, description TEXT);
CREATE TABLE permissions (id UUID PK, resource TEXT, action TEXT, UNIQUE(resource, action));
CREATE TABLE template_permissions (template_id UUID, permission_id UUID, PK(template_id, permission_id));

CREATE TABLE roles (
    id UUID PK, school_id UUID NULL,     -- NULL = platform-level (super_admin only)
    name TEXT, template_id UUID NULL, is_custom BOOLEAN
);
CREATE TABLE role_permissions (role_id UUID, permission_id UUID, PK(role_id, permission_id));
CREATE TABLE user_roles (user_id UUID, role_id UUID, school_id UUID, PK(user_id, role_id, school_id));
```

### 3.2 CRUD Hierarchy — Made a Permission, Not a Hardcoded Rule

Instead of "only School Admin can create Teacher/Student/Parent" being baked into code, model it as data:

```sql
CREATE TABLE role_creation_rights (
    creator_role_id UUID REFERENCES roles(id),
    creatable_template_id UUID REFERENCES role_templates(id)
    -- e.g. School Admin role → can create Teacher, Student, Parent templates
    -- e.g. Teacher role → can create Student, Parent templates (if school enables it)
);
```

This directly fixes your Point 1: whether a **Teacher can create Students/Parents** becomes a **per-school toggle**, not a code change. Tuition-style small schools enable it; larger schools with a dedicated office keep it School-Admin-only.

**Cascading mapping table (what maps to what):**

| Entity created | Must be mapped to | Mapping table |
|---|---|---|
| Teacher | Class + Subject | `TeacherAssignment` (exists ✅) |
| Student | Class | `Enrollment` (exists ✅) |
| Parent | Student(s) | `ParentStudentLink` (exists ✅, but creation locked to School Admin — fix via §3.2 rights table) |

**Edge cases to handle (thought through, not obvious at first glance):**
- One parent → multiple children (already supported by `ParentStudentLink` being many-to-many) ✅
- One student → multiple parents/guardians (same table supports it, just needs UI) — currently unclear if enforced
- Student transferred mid-year between classes → needs `Enrollment` history (currently likely overwrites, not versioned) — **gap**
- Teacher leaves school mid-year → `TeacherAssignment` needs an `end_date`, not hard delete (for audit/history) — **gap**
- Parent consent already tracked (`consent_given_at` field exists ✅) — good for compliance

---

## Part 4 — Dynamic Dashboards (Point 2)

### 4.1 Principle: Sidebar = rendered from permissions, not from role

```
On login → fetch user's resolved permissions (from user_roles → roles → role_permissions)
         → frontend renders sidebar menu items whose required permission is present
         → NO role-name check anywhere in frontend code ("if role == teacher") 
```

This is what makes dashboards **truly dynamic** — add a new "Librarian" role tomorrow with `library:*` permission, and a Library menu item appears automatically for anyone holding it — zero frontend redeploy.

### 4.2 Full page-map (current vs. target)

| Role | Current pages | Target pages (permission-gated) |
|---|---|---|
| Super Admin | Schools, Platform Dashboard | + Role Template Manager, Billing/Plans, Global Audit Viewer |
| School Admin | Structure, Users, Audit, Dashboard | + Custom Role Manager, Fee (if enabled), Admissions inbox |
| Teacher | Materials, Timetable, Dashboard, Flagged | + Student/Parent create (if permitted), Assignment builder, Class-progress page |
| Student | Chat, Dashboard, History, Quiz | + "Today's Learning" feed (Point 4) |
| Parent | Children, Child detail | + Messages, Weekly Report/Digest |
| *(future custom role, e.g. Accountant)* | — | Fee dashboard only — nothing else, by permission |

---

## Part 5 — Full Agent Mesh (Points 3, 4, 5 + governance)

### 5.1 Existing agents (keep as-is, reactive-by-design is correct for these)
Tutor · Quiz Master · Evaluator · Progress

### 5.2 New proactive agents required

| Agent | Trigger | Output | Approval needed? |
|---|---|---|---|
| **Scheduling Agent** (Point 3) | Teacher requests timetable | 2–4 draft options (different trade-offs: workload-balanced vs. subject-clustered vs. room-optimized) | Teacher picks + can edit; re-validated on edit |
| **Scheduled-Learning Agent** (Point 4) | Timetable period starts (cron check) | Topic explainer + 2–3 micro-questions pushed to student's "Today" feed | No approval needed (low-risk, student-facing only) |
| **Reporting Agent** (Point 5) | Weekly/monthly cron | Parent-facing report: mastery trend, quiz scores, attendance, teacher notes — human-readable, not raw tables | Teacher reviews before send (first few cycles), then auto-send once trusted |
| **Communication Agent** | Report ready / at-risk detected | Drafts parent message, sends via enabled channel(s) | Low-risk (digest) auto-sends; high-risk (concern flag) needs teacher approval |
| **Insight/Intervention Agent** | Nightly cron on `ProgressRecord` | "Student X struggling with Fractions 3 weeks running" → alert to teacher | Alert only, no auto-action |
| **Staffing Agent** | Teacher marked absent | Suggests substitute from available teachers | Admin approves |
| **Enrollment Agent** *(optional, if admissions flow built)* | New inquiry submitted | Verifies docs, drafts response | Admin approves |
| **Fee Agent** *(optional, feature-flagged — §9.3 earlier)* | Due-date cron | Reminder draft, defaulter flag | Accountant/Admin approves send |

### 5.3 Agent Governance (the part most teams skip — critical to think through)

- **Confidence scoring**: every agent output carries a confidence/risk score. High-confidence + low-risk (e.g. "send today's practice questions") → auto-executes. Low-confidence or high-risk (e.g. "flag student for intervention", "send fee defaulter notice") → routes to approval queue.
- **Generalized approval queue**: extend the existing `FlaggedAnswer` pattern into a generic `AgentAction` table (`agent_name`, `action_type`, `payload_json`, `confidence`, `status: pending/approved/rejected/auto_applied`, `reviewed_by`). One inbox for *all* agent proposals, not a separate table per agent.
- **Rollback**: any auto-applied action must be reversible (e.g. undo a sent notification's effect, revert a timetable change) — store enough state to undo, not just a log.
- **Audit**: every agent action (proposed, approved, auto-applied, rejected) goes into the existing `AuditLog` — already have the pattern, just extend coverage.
- **Prompt/version tracking**: agents' prompts change over time (already tracked partially via `model_role_used`, `provider_used` on `Message`) — extend this to all new agents so you can measure "did the new prompt version perform better?"

---

## Part 6 — Data Model Additions Needed

| New/changed table | Purpose |
|---|---|
| `roles`, `permissions`, `role_permissions`, `user_roles`, `role_creation_rights` | Dynamic RBAC (§3) |
| `AgentAction` (generalize `FlaggedAnswer`) | Universal approval queue (§5.3) |
| `Timetable.topic` (new field) | Links schedule slot to a specific chapter/topic, not just subject (Point 4 needs this) |
| `Enrollment.end_date` / history table | Mid-year class transfer tracking |
| `TeacherAssignment.end_date` | Mid-year teacher departure tracking |
| `Notification.channel` (`in_app`/`sms`/`whatsapp`/`email`) | Multi-channel delivery (§7) |
| `Report` (new) | Stores generated parent reports (for history/re-send, not regenerate every time) |

---

## Part 7 — Notification Channels (India-context specific — easy to overlook)

Many parents, especially in rural/low-income school contexts (which AshaShala explicitly targets per its README), **do not reliably use a smartphone app**. In-app-only notifications will silently fail to reach them.

- **SMS fallback** for critical alerts (fee due, at-risk alert, report ready) — cheapest, most reliable reach in India
- **WhatsApp Business API** (very high adoption in India) as a richer channel for reports/digests
- Email as a distant third (many parents won't check it)
- This is a **should-do-early** item — better an MVP with SMS than a polished app nobody opens

---

## Part 8 — Security, Privacy & Compliance (full scenario check)

| Concern | Status | Action |
|---|---|---|
| Tenant data isolation | ✅ `TenantScoped` mixin pattern exists | Keep enforcing on every new table |
| Parent consent tracking | ✅ `consent_given_at` exists | Good — extend to cover new data uses (e.g. WhatsApp opt-in) |
| Data export (right to access) | ✅ `/student/data-export` exists | Extend same pattern to parent/teacher data |
| Data deletion (right to be forgotten) | ✅ Super Admin route exists | Verify cascades correctly across new tables as schema grows |
| India-specific: DPDP Act 2023 (children's data) | ✅ School Admin must explicitly confirm guardian consent before a parent-student link is created (`POST /school/parent-links` rejects `consent_confirmed: false`) | Formal legal review of the full DPDP "Data Fiduciary" obligation set (breach notification, grievance officer, etc.) beyond this consent gate is still outstanding |
| Content safety (student chat) | ✅ Solid — keyword block + subject guard + optional jailbreak classifier | Keep as-is |
| Agent action audit | ✅ Pattern exists, needs extension (§5.3) | — |
| Rate limiting / abuse prevention | ⚠️ `slowapi` dependency exists but usage not confirmed everywhere | Verify applied to all public-facing endpoints (esp. chat, voice) |

---

## Part 9 — Non-Functional Considerations (often missed)

| Area | Consideration |
|---|---|
| **Accessibility** | Roadmap mentions WCAG 2.1 AA (Phase 5) — currently no evidence of implementation; low-literacy parent UX also matters (icons + voice over text-heavy UI) |
| **Offline/low-bandwidth** | Roadmap flags this as a risk already; voice TTS caching in R2 was planned — not yet built. Rural connectivity means this isn't optional long-term |
| **Localization (UI itself)** | Backend supports multilingual chat; frontend UI strings are English-only — parents/students with low English literacy face a wall before even reaching the AI |
| **Testing/QA** | `pytest` configured (good foundation) — but agent behavior (LLM outputs) needs eval harnesses, not just unit tests, since correctness isn't deterministic |
| **Monitoring/Observability** | `structlog`, `sentry-sdk` present in dependencies — confirm actually wired for the new proactive agents (silent background failures are the top risk of going agentic) |
| **Cost governance dashboard** | `LLMUsage` model exists (good) — extend to per-school budget alerts before scaling past pilot |
| **Disaster recovery** | ✅ Backup/restore runbook exists (`docs/runbook.md`) covering Postgres PITR, Qdrant snapshot restore, and R2 off-site sync — the runbook's own "restore drill checklist" is written but not yet executed against real infra; that's a one-time, credentialed pre-launch task, not a doc gap |

---

## Part 10 — Business/Extensibility Considerations

- **Open-source + optional modules**: Fee module (and similarly Admissions, HR, Library, Transport later) should follow the same `features_json` toggle pattern — keeps core lean, lets schools/contributors add modules without bloating the base product
- **Plugin-style agent registry**: as agent count grows (8+ agents planned), maintain a simple registry (`agent_name → trigger event → handler`) so adding agent #9 doesn't require touching the orchestrator's core logic
- **Avoid vendor lock-in**: LLM router already abstracts Gemini/NVIDIA/OpenAI — good, keep new agents going through the same router, not calling providers directly

---

## Part 11 — Consolidated Gap Table (everything, in one place)

| # | Gap | Priority | Effort |
|---|---|---|---|
| 1 | Hardcoded role enum → dynamic role/permission schema | 🟡 Dynamic schema built (`app/models/rbac.py`: `RoleTemplate`, `Permission`, `Role`, `RolePermission`, `UserRoleAssignment`, `RoleCreationRight`, full CRUD) but `User.role` column is still the fixed `UserRole` enum — not yet migrated onto the dynamic tables | Medium (migration remains) |
| 2 | Role-creation-rights as data, not hardcoded set | ✅ Done — `role_creation_rights` DB table + CRUD routes (`school_admin.py`); `DEFAULT_CREATION_RIGHTS` in `core/permissions.py` is only a bootstrap seed | — |
| 3 | Permission-driven sidebar/dashboard | ✅ Done — `navForUser()` filters the nav by live `permissions[]` from the API; routes gated by explicit permission strings. (Nav item list itself is still a hardcoded array, filtered rather than server-generated) | — |
| 4 | Scheduler (APScheduler at pilot scale) | ✅ Done — `app/core/scheduler.py`, `AsyncIOScheduler` with 4 jobs, started in `main.py` | — |
| 5 | Scheduling Agent (AI timetable) | ✅ Done — `app/agents/scheduling.py`, teacher-triggered slot proposals validated against the real free-slot grid, queued via `AgentAction` | — |
| 6 | Scheduled-Learning Agent (timetable-driven topics + micro-quiz) | ✅ Done — `app/agents/scheduled_learning.py`, daily cron job pushes feed items proactively | — |
| 7 | Reporting + Communication Agents (parent report) | ✅ Done — `app/agents/reporting.py` weekly cron job calls `communication.send_report_message()`, delivered via each parent's enabled channels | — |
| 8 | Generalized `AgentAction` approval queue | ✅ Done — `app/models/agent_action.py` + `routes/agent_actions.py` (list/approve/reject) | — |
| 9 | Multi-channel notifications (SMS/WhatsApp) | 🟡 Infrastructure done (`NotificationChannel` enum, pluggable `_SENDERS` dispatch in `notification_dispatch.py`) but senders are `LogSender` stubs — no real Twilio/WhatsApp Business API integration yet | Small (swap in real provider — documented as a one-file change) |
| 10 | Insight/Intervention Agent (at-risk alerts) | ✅ Done — `app/agents/insight.py`, daily cron job creates alerts and drafts a parent message via the communication agent, held pending teacher approval | — |
| 11 | Frontend i18n (UI localization) | 🟡 Foundation + chrome shipped (en/hi/gu, nav/layout/Login/Settings); remaining ~50 route files still English | Medium |
| 12 | Mid-year transfer history (`Enrollment`/`TeacherAssignment` end dates) | ✅ Done — both models have `end_date: Date \| None` (NULL = active, non-null = transfer/reassignment date) | — |
| 13 | Fee/Admissions/HR/Library modules (feature-flagged, optional) | 🟢 Low (deferred) | Large |
| 14 | DPDP Act explicit compliance review | ✅ Consent-confirmation gate shipped; full legal review still pending | Small (review + doc) |
| 15 | Offline/low-bandwidth support | 🟡 First cut shipped (installable app shell + connectivity banner); full offline mutation sync still deferred | Large |
| 16 | Disaster recovery runbook | ✅ Shipped (`docs/runbook.md`); live restore drill still pending | Small |

---

## Part 12 — Phased Roadmap (pilot-aware: 5–10 users, free-tier APIs)

**Phase 1 — Foundation: ✅ done**
Dynamic RBAC schema tables (#1 — schema built, `User.role` migration still open) → Permission-driven sidebar filtering (#3, done) → Generalized `AgentAction` queue (#8, done)

**Phase 2 — Infrastructure: ✅ done**
APScheduler (#4, done) → Notification channel model + pluggable dispatch (#9 — real SMS/WhatsApp provider still stubbed) → `Enrollment`/`TeacherAssignment` history fields (#12, done)

**Phase 3 — First proactive agents: ✅ done**
Scheduling Agent (#5, done) → Insight Agent (#10, done) → Scheduled-Learning Agent (#6, done)

**Phase 4 — Parent-facing: ✅ done**
Reporting Agent + Communication Agent (#7, done)

**Phase 5 (deferred until pilot grows past ~10 users / multiple schools):**
Fee/Admissions/HR modules (#13), Celery migration if APScheduler hits limits. Started early, ahead of schedule: DPDP consent gate + DR runbook status correction (#14, #16 — legal review and live restore drill still pending), i18n foundation + chrome translation (#11 — remaining route files still pending), offline app-shell + connectivity banner (#15 — full offline mutation sync still deferred)

**Phase 6 (remaining open items, not yet scheduled):**
`User.role` migration onto the dynamic RBAC schema (#1 completion), real SMS/WhatsApp provider integration (#9 completion — currently a one-file `LogSender` swap)

---

## Part 13 — Immediate Next Step

Phases 1–4 and the Phase 5 quick wins (DR/DPDP status, i18n foundation, offline first cut) are done. Two genuine gaps remain from the original roadmap, plus the deferred Phase 5 modules:

- **#1 completion**: migrate `User.role` off the fixed `UserRole` enum onto the already-built dynamic RBAC schema (`rbac.py`) — the schema and creation-rights CRUD exist, but the base user table hasn't been cut over. This is the one item that's genuinely "critical infra debt" left over from the original plan.
- **#9 completion**: wire a real SMS/WhatsApp provider (e.g. Twilio, Meta WhatsApp Business API) into `notification_dispatch.py`'s `_SENDERS` map, replacing the `LogSender` stub — documented as a one-file change, gated mainly on which provider/credentials the user wants.
- **Phase 5 remainder**: Fee/Admissions/HR modules (#13, large, deferred until pilot scale grows), plus finishing the deferred parts of #11/#14/#15/#16 (i18n across remaining routes, DPDP legal review, offline mutation sync, DR restore drill).

Recommended next PR: **#1 (User.role migration)** — it's the last piece of "critical" infra debt, and every day it's left undone increases migration risk as more schools/data onboard.

---

*Document owner: keep as living source of truth at `docs/ARCHITECTURE_MASTER.md`. Update after each phase.*

---


## Part 14. SUPER ADMIN

### 14.1 Page: `/admin/schools` — Schools List
| Element | Detail |
|---|---|
| **Table columns** | School Name, Address, Status (Active/Inactive), Created Date, Actions ✅ |
| **Form: Create School** | name*, address (optional) ✅ |
| **Form: Edit School** | name, is_active toggle ✅ |
| **Row action** | Delete school (with confirm) ✅ |
| **APIs** | `GET /api/v1/admin/schools` ✅ · `POST /api/v1/admin/schools` ✅ · `PATCH /api/v1/admin/schools/{id}` ✅ · `DELETE /api/v1/admin/schools/{id}` ✅ |
| 🆕 **Missing form** | Create School Admin inline from this page — API exists (`createSchoolAdmin`) but check if UI form is wired |

### 14.2 Page: `/admin/dashboard` — Platform Dashboard
| Element | Detail |
|---|---|
| **Widgets** | Total Schools, Total Teachers, Total Students, Total Classes (last N days) ✅ |
| **Drill-down** | Per-school dashboard (`/admin/schools/{id}/dashboard`) ✅ API exists |
| **APIs** | `GET /api/v1/admin/dashboard?days=` ✅ · `GET /api/v1/admin/schools/{id}/dashboard` ✅ |

### 14.3 🆕 Page: `/admin/roles` — Role Template Manager (NEW)
| Element | Detail |
|---|---|
| **Table columns** | Template Name, System/Custom, # Permissions, # Schools Using It |
| **Form: Create/Edit Template** | Name, Description, Permission checklist (grouped by resource: Student, Class, Fee, Timetable, AI Agent, etc.) |
| **APIs (new)** | `GET/POST /api/v1/admin/role-templates` 🆕 · `PATCH/DELETE /api/v1/admin/role-templates/{id}` 🆕 · `GET /api/v1/admin/permissions` 🆕 (full permission catalog) |

### 14.4 🆕 Page: `/admin/billing` — Billing & Plans (NEW, deferred until monetization)
| Element | Detail |
|---|---|
| **Table** | School, Plan Tier, Usage (LLM tokens/month), Status |
| **APIs (new)** | `GET /api/v1/admin/billing` 🆕 — low priority, build when moving past free-tier pilot |

### 14.5 🆕 Page: `/admin/audit` — Global Audit Viewer (NEW)
| Element | Detail |
|---|---|
| **Table columns** | Timestamp, School, User, Action, Resource, IP |
| **Filters** | By school, by action type, by date range |
| **APIs (new)** | `GET /api/v1/admin/audit?school_id=&action=` 🆕 (school-level audit exists at `/school/audit` ✅ — needs a cross-tenant version for Super Admin) |

---

## Part 15. SCHOOL ADMIN

### 15.1 Page: `/school/dashboard`
| Element | Detail |
|---|---|
| **Widgets** | Teacher count, Student count, Class count ✅ |
| **At-risk students widget** | Table: Student Name, Class, Subject, Mastery Score (sorted weakest-first) ✅ |
| **Mastery-by-class chart** | Bar/heatmap: Class vs. Avg Mastery ✅ |
| **LLM usage widget** | Tokens used, cost estimate (last 7 days) ✅ |
| **APIs** | `GET /api/v1/school/dashboard` ✅ · `GET /api/v1/school/dashboard/at-risk` ✅ · `GET /api/v1/school/dashboard/mastery-by-class` ✅ · `GET /api/v1/school/llm-usage` ✅ |

### 15.2 Page: `/school/users` — User Management
| Element | Detail |
|---|---|
| **Table columns** | Name, Email, Role, Status, Created Date, Actions ✅ |
| **Filter** | By role (dropdown) ✅ |
| **Form: Create User** | name*, email*, role* (dropdown), grade (if student), interests (if student) ✅ |
| **Form: Edit User** | name, is_active, grade, interests ✅ |
| **Action: Reset Password** | Generates temp password ✅ |
| **Action: Bulk Import** | CSV upload form ✅ |
| **APIs** | `GET/POST /api/v1/school/users` ✅ · `PATCH /api/v1/school/users/{id}` ✅ · `POST /api/v1/school/users/{id}/reset-password` ✅ · `POST /api/v1/school/users/bulk` ✅ |
| 🔧 **Change needed** | Role field should become a dynamic dropdown fetched from `role_templates` + school's custom `roles`, not a fixed enum dropdown |

### 15.3 Page: `/school/structure` — Classes, Subjects, Assignments, Enrollments
| Sub-tab | Table columns | Form fields | APIs |
|---|---|---|---|
| **Classes** | Name, Grade Level ✅ | name*, grade_level* ✅ | `GET/POST /api/v1/school/classes` ✅ |
| **Subjects** | Name ✅ | name* ✅ | `GET/POST /api/v1/school/subjects` ✅ |
| **Teacher Assignments** | Teacher, Class, Subject ✅ | teacher_id*, class_id*, subject_id* (all dropdowns) ✅ | `GET/POST/DELETE /api/v1/school/teacher-assignments` ✅ |
| **Enrollments** | Student, Class ✅ | student_id*, class_id* ✅ | `GET/POST/DELETE /api/v1/school/enrollments` ✅ |
| **Parent Links** | Parent, Student ✅ | parent_id*, student_id* ✅ | `GET/POST/DELETE /api/v1/school/parent-links` ✅ |
| 🆕 **Missing field** | Teacher Assignment needs `end_date` (mid-year departure tracking) | | `PATCH .../teacher-assignments/{id}` 🆕 |
| 🆕 **Missing field** | Enrollment needs `end_date`/history (mid-year transfer tracking) | | `PATCH .../enrollments/{id}` 🆕 |

### 15.4 Page: `/school/audit` — School Audit Log
| Element | Detail |
|---|---|
| **Table columns** | Timestamp, User, Action, Resource | ✅ |
| **Filter** | By action type ✅ |
| **APIs** | `GET /api/v1/school/audit?action=` ✅ |

### 15.5 🆕 Page: `/school/roles` — Custom Role Manager (NEW)
| Element | Detail |
|---|---|
| **Table columns** | Role Name, Based-on Template, # Users Assigned |
| **Form: Create Custom Role** | Name, Base Template (dropdown, optional), Permission checklist, **"Can this role create Students/Parents?" toggle** (implements Point 1's dynamic creation rights) |
| **APIs (new)** | `GET/POST /api/v1/school/roles` 🆕 · `PATCH/DELETE /api/v1/school/roles/{id}` 🆕 |

### 15.6 🆕 Page: `/school/fee` — Fee Management (feature-flagged, optional)
| Element | Detail |
|---|---|
| **Table columns** | Student, Fee Structure, Due Date, Status (Paid/Due/Overdue) |
| **Form: Fee Structure** | Class, Amount, Due Date, Installments |
| **Widget** | Defaulter list (auto-flagged by Fee Agent) |
| **APIs (new)** | `GET/POST /api/v1/school/fees` 🆕 · `GET /api/v1/school/fees/defaulters` 🆕 |
| **Visibility** | Only shown if `School.features_json.fee_management = true` |

### 15.7 🆕 Page: `/school/admissions` — Admissions Inbox (optional, deferred)
| Element | Detail |
|---|---|
| **Table columns** | Applicant Name, Submitted Date, Documents, Status |
| **APIs (new)** | `GET/POST /api/v1/school/admissions` 🆕 — low priority, build only if public admission flow is needed |

---

## Part 16. TEACHER

### 16.1 Page: `/teacher/dashboard`
| Element | Detail |
|---|---|
| **Widgets** | Assigned classes summary, pending flagged answers count, upcoming timetable slots ✅ |
| **APIs** | `GET /api/v1/teacher/dashboard` ✅ |

### 16.2 Page: `/teacher/materials` — Material Upload
| Element | Detail |
|---|---|
| **Table columns** | Filename/URL, Type (PDF/DOCX/URL/YouTube), Class, Subject, Ingestion Status ✅ |
| **Form: Upload File** | class_id*, subject_id, file* (drag-drop) ✅ |
| **Form: Upload URL** | class_id*, subject_id, url* ✅ |
| **Form: Upload YouTube** | class_id*, subject_id, url* ✅ |
| **APIs** | `POST /api/v1/teacher/materials/file` ✅ · `POST .../materials/url` ✅ · `POST .../materials/youtube` ✅ · `GET .../materials` ✅ · `DELETE .../materials/{id}` ✅ |
| 🆕 **Missing action** | "Generate quiz from this material" button (wires into Quiz Master proactively) — `POST /api/v1/teacher/materials/{id}/suggest-quiz` 🆕 |

### 16.3 Page: `/teacher/timetable`
| Element | Detail |
|---|---|
| **Table columns (current)** | Day, Period, Class, Subject, Room ✅ |
| **Form: Create Entry (current)** | day, period, class_id, subject_id, room — manual, one at a time ✅ |
| 🆕 **New: "AI Suggest" button** | Opens Scheduling Agent flow → shows 2–4 draft options side-by-side |
| 🆕 **New: Option comparison view** | Cards per option: workload balance chart, conflict count, "why this option" summary |
| 🆕 **New: Topic field** | Each timetable entry should also carry `topic_id` (chapter/topic being taught that slot) — needed for the scheduled-learning feature |
| **APIs (current)** | `GET/POST/DELETE /api/v1/teacher/timetable` ✅ |
| **APIs (new)** | `POST /api/v1/teacher/timetable/ai-suggest` 🆕 (returns array of draft timetables) · `POST /api/v1/teacher/timetable/{option_id}/select` 🆕 · `PATCH /api/v1/teacher/timetable/{id}` 🆕 (add `topic_id`) |

### 16.4 🆕 Page: `/teacher/exam-timetable`
| Element | Detail |
|---|---|
| **Table columns** | Class, Subject, Exam Date, Duration — backend route exists (`create_exam_timetable`) ✅ but **no frontend page found** — needs one |
| **Form** | class_id*, subject_id*, exam_date*, duration* |
| **APIs** | `POST /api/v1/teacher/exam-timetable` ✅ (backend exists, frontend page 🆕) |

### 16.5 🆕 Page: `/teacher/assignments` — Assignment Builder (NEW)
| Element | Detail |
|---|---|
| **Table columns** | Topic, Class, Due Date, Submission Count — backend `list_assignments` route exists ✅, dedicated builder UI 🆕 |
| **Form** | Pick topic(s) from material → auto-generate quiz (via Quiz Master) → set due date |
| **APIs** | `GET /api/v1/teacher/assignments` ✅ · `POST /api/v1/teacher/assignments` 🆕 (create+auto-generate) |

### 16.6 Page: `/teacher/flagged` — Flagged Answer Review
| Element | Detail |
|---|---|
| **Table columns** | Student, Question, AI Score, AI Feedback, Status ✅ |
| **Form: Override** | score*, feedback (optional) ✅ |
| **APIs** | `GET /api/v1/teacher/flagged-answers` ✅ · `POST .../flagged-answers/{id}/override` ✅ |
| 🆕 **Extend to** | Generic `AgentAction` approval queue — not just grading, all agent proposals (scheduling picks, fee reminders, etc.) |

### 16.7 🆕 Page: `/teacher/students` — Student/Parent Creation (NEW, conditional)
| Element | Detail |
|---|---|
| **Visible only if** | Teacher's role has `student:create` / `parent:create` permission (per-school toggle) |
| **Form: Create Student** | name*, email*, class_id* (auto-enrolls) |
| **Form: Create Parent + Link** | name*, email*, student_id* (auto-links) |
| **APIs (new)** | `POST /api/v1/teacher/students` 🆕 · `POST /api/v1/teacher/parents` 🆕 (mirrors school_admin equivalents, gated by permission not role name) |

### 16.8 🆕 Page: `/teacher/class-progress/{classId}` — Class Progress Detail
| Element | Detail |
|---|---|
| **Table columns** | Student, Subject, Topic, Mastery Score, Last Reviewed — backend route exists ✅ (`class_progress`), **no dedicated frontend page found** |
| **APIs** | `GET /api/v1/teacher/classes/{id}/progress` ✅ (backend), frontend page 🆕 |

---

## Part 17. STUDENT

### 17.1 Page: `/student/dashboard`
| Element | Detail |
|---|---|
| **Widgets** | Embedded Timetable grid ✅, Progress/mastery snapshot ✅ |
| **APIs** | `GET /api/v1/student/dashboard` ✅ · `GET /api/v1/student/timetable` ✅ · `GET /api/v1/student/progress` ✅ |
| 🆕 **New widget** | "Today's Learning" feed — topic explainer + micro-questions pushed by Scheduled-Learning Agent |
| **APIs (new)** | `GET /api/v1/student/today` 🆕 (returns today's scheduled topic content + micro-quiz) |

### 17.2 Page: `/student/chat` — Tutor Chat
| Element | Detail |
|---|---|
| **Elements** | Message stream (SSE), citation hover cards, voice input/output toggle ✅ |
| **APIs** | `POST /api/v1/student/chat` (streaming) ✅ · `POST /api/v1/student/voice/stt` ✅ · `GET /api/v1/student/voice/tts` ✅ |

### 17.3 Page: `/student/quiz`
| Element | Detail |
|---|---|
| **Form: Start Quiz** | class_id*, subject_id ✅ |
| **Quiz-taking UI** | Question, answer input, submit ✅ |
| **APIs** | `POST /api/v1/student/quiz/start` ✅ · `POST /api/v1/student/quiz/{id}/submit` ✅ · `GET /api/v1/student/quizzes` ✅ |

### 17.4 Page: `/student/history`
| Element | Detail |
|---|---|
| **Table columns** | Quiz Topic, Date, Score, Feedback ✅ (paginated) |
| **APIs** | `GET /api/v1/student/history` ✅ |

### 17.5 🆕 Page: `/student/exams` — Exam Timetable
| Element | Detail |
|---|---|
| **Table columns** | Subject, Exam Date, Duration — backend exists ✅, needs dedicated page |
| **APIs** | `GET /api/v1/student/exam-timetable` ✅ |

---

## Part 18. PARENT

### 18.1 Page: `/parent/children`
| Element | Detail |
|---|---|
| **Table/cards** | Child name, class, quick mastery snapshot ✅ |
| **APIs** | `GET /api/v1/parent/children` ✅ |

### 18.2 Page: `/parent/children/{id}` — Child Detail
| Element | Detail |
|---|---|
| **Widgets** | Timetable grid ✅, Exam timetable ✅, Quiz history table ✅ |
| **APIs** | `GET /api/v1/parent/children/{id}/dashboard` ✅ · `.../timetable` ✅ · `.../exam-timetable` ✅ · `.../history` ✅ |

### 18.3 🆕 Page: `/parent/reports` — Weekly/Monthly Reports (NEW)
| Element | Detail |
|---|---|
| **Table columns** | Report Period, Generated Date, Summary snippet, "View Full Report" |
| **Full report view** | Mastery trend chart, quiz score trend, attendance summary, teacher notes — human-readable narrative, not raw tables |
| **Action** | Download PDF, Share via WhatsApp |
| **APIs (new)** | `GET /api/v1/parent/children/{id}/reports` 🆕 · `GET /api/v1/parent/children/{id}/reports/{reportId}/pdf` 🆕 (Reporting Agent output) |

### 18.4 🆕 Page: `/parent/messages` — Communication (NEW)
| Element | Detail |
|---|---|
| **Table/thread view** | Message from teacher, timestamp, read status |
| **Form: Reply** | text message |
| **APIs (new)** | `GET/POST /api/v1/parent/messages` 🆕 · `GET/POST /api/v1/teacher/messages` 🆕 (both sides) |

### 18.5 🆕 Notification preferences (settings, small addition)
| Element | Detail |
|---|---|
| **Form** | Channel toggle: In-app / SMS / WhatsApp / Email, phone number field |
| **APIs (new)** | `GET/PATCH /api/v1/parent/notification-preferences` 🆕 |

---

## Part 19. SHARED / CROSS-ROLE

### 19.1 `NotificationBell` component ✅ (exists)
| **APIs** | `GET /api/v1/notifications` ✅ · `POST .../{id}/read` ✅ · `POST .../read-all` ✅ |
| 🆕 **Extend** | Backend `Notification` model needs `channel` field + dispatch logic for SMS/WhatsApp |

### 19.2 🆕 `Approval Queue` component (NEW, shared across School Admin / Teacher / Accountant)
| Element | Detail |
|---|---|
| **Table columns** | Agent Name, Action Type, Proposed Payload (summary), Confidence Score, Status |
| **Row actions** | Approve, Reject, View Details |
| **APIs (new)** | `GET /api/v1/agent-actions?status=pending` 🆕 · `POST /api/v1/agent-actions/{id}/approve` 🆕 · `POST /api/v1/agent-actions/{id}/reject` 🆕 |
| **Note** | This generalizes the existing `flagged-answers` UI pattern — same table/row-action shape, reused for every agent (scheduling picks, fee reminders, at-risk alerts, etc.) |

### 19.3 🆕 `RoleGuard` component — change needed
| Current | `RoleGuard.tsx` likely checks `user.role === "teacher"` (hardcoded) 🔧 |
| Target | Checks `user.permissions.includes("resource:action")` — sidebar items and route access driven by resolved permissions, not role name |

---

## Part 20. Summary: New Backend Endpoints Needed (all in one list)

```
# Dynamic RBAC
GET/POST/PATCH/DELETE  /api/v1/admin/role-templates
GET                     /api/v1/admin/permissions
GET/POST/PATCH/DELETE  /api/v1/school/roles
GET/PATCH               /api/v1/school/roles/{id}/creation-rights

# Agent actions (generalized approval queue)
GET   /api/v1/agent-actions?status=
POST  /api/v1/agent-actions/{id}/approve
POST  /api/v1/agent-actions/{id}/reject

# Scheduling Agent
POST  /api/v1/teacher/timetable/ai-suggest
POST  /api/v1/teacher/timetable/{option_id}/select
PATCH /api/v1/teacher/timetable/{id}          # add topic_id

# Scheduled-Learning Agent
GET   /api/v1/student/today

# Reporting + Communication Agents
GET   /api/v1/parent/children/{id}/reports
GET   /api/v1/parent/children/{id}/reports/{reportId}/pdf
GET/POST /api/v1/parent/messages
GET/POST /api/v1/teacher/messages
GET/PATCH /api/v1/parent/notification-preferences

# Teacher-side user creation (permission-gated)
POST  /api/v1/teacher/students
POST  /api/v1/teacher/parents

# Quiz auto-suggestion
POST  /api/v1/teacher/materials/{id}/suggest-quiz
POST  /api/v1/teacher/assignments        # create + auto-generate

# History/versioning
PATCH /api/v1/school/teacher-assignments/{id}   # add end_date
PATCH /api/v1/school/enrollments/{id}           # add end_date

# Fee module (optional, feature-flagged)
GET/POST /api/v1/school/fees
GET      /api/v1/school/fees/defaulters

# Frontend pages missing for EXISTING backend routes (no new API needed, just UI)
/teacher/exam-timetable        -> uses existing POST/GET /api/v1/teacher/exam-timetable
/teacher/class-progress/{id}   -> uses existing GET /api/v1/teacher/classes/{id}/progress
/student/exams                 -> uses existing GET /api/v1/student/exam-timetable
```

---

*This document is the frontend+backend companion to `AshaShala_Final_Master_Plan.md`. Keep both in sync in `docs/`.*

---

*This is the complete, final, merged AshaShala SaaS planning document. Recommended location in repo: `docs/ARCHITECTURE_MASTER.md`. Update after each phase of implementation.*