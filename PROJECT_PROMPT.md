# AshaShala — PROJECT_PROMPT.md

> Paste this entire file into Claude Code (or any AI coding agent) as the first message.
> The agent must read ALL sections before writing a single line of code.
> Build ONLY the current phase. Stop at the checkpoint. Wait for "go" before continuing.

---

## 0. Vision

**AshaShala** is a multi-tenant, role-based, agentic AI tutoring platform for real schools.

A teacher uploads class material. Students learn from it through an AI tutor that:
- Always cites its source (page number, YouTube timestamp, or URL)
- Always leads with a real-life example before a textbook explanation
- Always encourages — never says "wrong" bluntly
- Adapts depth to the student's live mastery score
- Speaks Gujarati, Hindi, and other Indic languages natively

Everyone above the student has the tools to run an actual school on this:
- **Super Admin** onboards schools
- **School Admin** manages teachers, students, classes, parents
- **Teacher** uploads material, approves quizzes, watches class progress
- **Student** chats, takes quizzes, tracks their own mastery
- **Parent** sees only their linked child's progress — read-only

**Five real use cases this build must handle end to end:**
1. A teacher uploads a scanned science chapter photographed on a phone → it gets OCR'd and indexed
2. A Grade 6 student with low mastery asks a voice question in Gujarati → gets an encouraging, cited, example-first answer in Gujarati
3. A school admin onboards a new teacher mid-year → no other class's data is touched
4. A parent checks their child's mastery dashboard → cannot see any other student, including siblings, unless explicitly linked
5. A super admin onboards a second school → its data is fully isolated from the first

**Everything runs on free hosted cloud services. Zero local infrastructure. Zero paid APIs. Zero paid hosting.**

---

## 1. Tech Stack (locked — do not substitute without asking)

| Layer | Choice | Free tier reality |
|---|---|---|
| Frontend | React 18 + Vite + TailwindCSS + TypeScript | Vercel Hobby — free, unlimited deploys, HTTPS |
| State / routing | Zustand, React Router, TanStack Query | OSS |
| Charts | Recharts | OSS |
| Backend | Python 3.11+, FastAPI (async), Uvicorn | — |
| Auth | JWT (access + refresh), `passlib[bcrypt]` | OSS |
| Relational DB | **Neon Postgres** | Free: 0.5 GB/project, 100 CU-hours/month, 10 branches, scale-to-zero, built-in PgBouncer pooler (covers connection pooling for free) |
| Migrations | SQLAlchemy 2.x async + Alembic | OSS |
| Vector DB | **Qdrant Cloud** | Free: 1 GB cluster, ~1M vectors at 768 dims |
| Object storage | **Cloudflare R2** | Free: 10 GB, zero egress — original uploaded files live here |
| LLM primary | **Gemini API** — `gemini-2.5-flash-lite` (default), `gemini-2.5-flash` (reasoning/vision) | Free tier. NEVER default to `gemini-2.5-pro` — paid only since April 2026. `gemini-2.0-flash` is shut down — do not use it. |
| LLM fallback + OCR + ASR + Indic | **NVIDIA NIM** — `https://integrate.api.nvidia.com/v1` (OpenAI-compatible) | Free dev tier. Rate-limited (~40 req/min) and credit-capped. Used for fallback and tasks Gemini can't do. Model IDs live in `config/model_registry.yaml`, never hardcoded. |
| Agent orchestration | LangGraph | OSS |
| Background jobs | FastAPI `BackgroundTasks` | Fine at pilot scale |
| File parsing | `pypdf`, `python-docx` | OSS |
| URL ingestion | `httpx` + `trafilatura` | OSS |
| YouTube ingestion | `youtube-transcript-api` | OSS, no key |
| Streaming | SSE (Server-Sent Events) | — |
| Error monitoring | Sentry free tier | Free up to 5k errors/month |
| Backend hosting | **Render** (primary — free Web Service, Docker, sleeps after 15 min idle; document this tradeoff clearly in README). **Northflank** free sandbox is the named alternative if always-on matters. **Railway excluded** — documented platform outages in 2026. | Free |

**Required env vars — crash loudly on startup if any are missing:**

```
GEMINI_API_KEY          # aistudio.google.com
NVIDIA_API_KEY          # build.nvidia.com — single key for ALL NVIDIA models
NVIDIA_BASE_URL         # https://integrate.api.nvidia.com/v1
DATABASE_URL            # Neon Postgres — postgresql+psycopg://USER:PASS@HOST/DB?sslmode=require
QDRANT_URL              # Qdrant Cloud cluster URL
QDRANT_API_KEY          # Qdrant Cloud API key
R2_ACCOUNT_ID           # Cloudflare R2
R2_ACCESS_KEY_ID        # Cloudflare R2
R2_SECRET_ACCESS_KEY    # Cloudflare R2
R2_BUCKET_NAME          # Cloudflare R2 bucket name
R2_PUBLIC_URL           # Public URL base for R2 (e.g. https://pub-xxx.r2.dev)
JWT_SECRET              # random 64-char string
JWT_REFRESH_SECRET      # separate random 64-char string
SUPER_ADMIN_EMAIL       # seeded on first run
SUPER_ADMIN_PASSWORD    # seeded on first run
ALLOWED_ORIGINS         # comma-separated CORS origins
SENTRY_DSN              # Sentry free tier DSN (optional but set from Phase 1)
```

**Never hardcode any secret. `.env` in `.gitignore` from the very first commit. Ship `.env.example` with placeholder values.**

---

## 2. Model Registry

NVIDIA model names drift and get deprecated regularly. They must NOT be hardcoded anywhere in Python. They live in one YAML file that you fill in by checking the live catalog before building.

**Before Phase 1:** open `https://build.nvidia.com/models?pageSize=96&filters=publisher%3Anvidia`, find the current model ID for each role below, paste it in. Re-check this URL whenever a role starts failing — that's a deprecation, not a bug.

```yaml
# config/model_registry.yaml
roles:
  fast_chat:
    gemini: "gemini-2.5-flash-lite"
    nvidia_fallback: ""        # General chat — check catalog for current Nemotron general model

  reasoning:
    gemini: "gemini-2.5-flash"
    nvidia_fallback: ""        # Heavy reasoning — Nemotron Ultra family, check catalog

  multilingual_indic:
    nvidia_primary: ""         # Sarvam-M — built for Indic languages, check catalog for current ID
    nvidia_fallback: ""        # Llama-4-Maverick multilingual, check catalog

  vision:
    gemini: "gemini-2.5-flash"
    nvidia_fallback: ""        # Vision-language model, check catalog

  ocr:
    nvidia: ""                 # nemotron-ocr-v2 confirmed live — check catalog for exact ID

  asr:
    nvidia: ""                 # nemotron-asr-streaming — multilingual mode covers 40 locales
                               # incl. Hindi, Gujarati — check catalog for exact ID

  embeddings:
    gemini: "text-embedding-004"
    nvidia_fallback: ""        # Multilingual embedding, check catalog

  safety_jailbreak:
    nvidia: ""                 # nemoguard-jailbreak-detect — NOTE: takes a pre-computed
                               # embedding as input, NOT raw text. See Section 7.
```

`app/services/model_registry.py` — loads this YAML once at startup:

```python
import yaml
from functools import lru_cache

@lru_cache
def get_registry() -> dict:
    with open("config/model_registry.yaml") as f:
        return yaml.safe_load(f)["roles"]

def model_for(role: str, provider: str) -> str:
    reg = get_registry()
    if role not in reg:
        raise ValueError(f"Unknown model role: {role}")
    key = "gemini" if provider == "gemini" else "nvidia_primary" if "nvidia_primary" in reg[role] else "nvidia_fallback"
    model_id = reg[role].get(key, "")
    if not model_id:
        raise RuntimeError(f"Model ID for role={role} provider={provider} not set in model_registry.yaml. "
                           "Check https://build.nvidia.com/models and fill it in.")
    return model_id
```

The LLM router (`app/services/llm_router.py`) always calls `model_for(role, provider)` — never a raw string.

---

## 3. LLM Router

```python
# app/services/llm_router.py
async def chat(messages: list, task: str, lang_hint: str = "en",
               school_id: str | None = None) -> str:
    """
    Routing rules:
    1. Indic language → NVIDIA sarvam-m (primary) → llama-4-maverick (fallback). No Gemini call.
    2. task == "evaluate" → gemini-2.5-flash → on 429: NVIDIA reasoning fallback
    3. task == "vision" → gemini-2.5-flash (vision) → on 429: NVIDIA vision fallback
    4. default → gemini-2.5-flash-lite → on 429: NVIDIA fast_chat fallback
    Logs every call to llm_usage table: provider, model_role, tokens, latency_ms, school_id, task, status
    """
```

Indic language codes that trigger NVIDIA-direct routing (no Gemini):
`{"gu", "hi", "mr", "ta", "te", "bn", "kn", "ml", "pa", "ur"}`

**Per-call timeouts** (configured in `app/core/config.py`):
- Gemini calls: 30s
- NVIDIA calls: 45s (OCR/ASR may be slower)
- Qdrant queries: 10s
- R2 upload: 60s

**Retry policy:** 3 attempts, exponential backoff (1s, 2s, 4s) with jitter on 429 and 5xx. After retries exhausted, fall through to the next provider in the chain.

---

## 4. Roles & Permissions

**Five roles. Every permission check server-side. Tenant-scoped by `school_id` from JWT on every query.**

### 4.1 Super Admin (`school_id = NULL`)
- Create / suspend / reactivate / delete schools
- Create first School Admin for a new school (returns one-time temp password)
- Read-only platform dashboard: active schools, total users, LLM tokens used per school today, error rate
- Cannot read student/teacher/class content. Cross-school support access must be logged as `SUPER_ADMIN_DATA_ACCESS` with a reason.

### 4.2 School Admin (one school)
- Invite/create/deactivate: teachers, students, parents
- CSV bulk-import students (auto-generate credentials)
- Create Classes, Subjects
- Assign teachers to `(class, subject)` pairs
- Enroll students into classes
- Link parents to students (many-to-many; one parent → multiple children; one child → multiple parents)
- School dashboard: per-class mastery averages, engagement, top performers, students needing attention
- Audit log viewer for the school

### 4.3 Teacher (one school, assigned classes)
- Upload class material — scoped to `(class, subject)` they are assigned to:
  - **File** (PDF / DOCX / TXT) — uploaded to R2, then ingested
  - **URL** — fetched via httpx + trafilatura, ingested
  - **YouTube** — transcript via youtube-transcript-api with timestamps, ingested
- Approve quizzes before students see them (status: draft → approved)
- Regular timetable (weekly recurring: day, period, class, subject, room)
- Exam timetable (per exam: date, time, class, subject, duration)
- Teacher dashboard: my classes, materials uploaded, per-student progress, flagged answers for review, upcoming periods + exams, AI-suggested weak topics per class

### 4.4 Student (one school, enrolled classes)
- See materials only from their enrolled `(class, all subjects in that class)`
- Chat with Tutor agent — text or voice
- Take quizzes (approved only)
- View own mastery dashboard, history, upcoming periods + exams
- Cannot see other students' data

### 4.5 Parent (one school, linked children)
- Read-only: child's mastery, recent activity, quiz scores, upcoming timetable
- Cannot chat, cannot take quizzes, cannot see other students (including unlisted siblings)
- Every parent view logged as `PARENT_VIEW_CHILD` in audit

### 4.6 Tenant Isolation — hard rules

- Every table (except `schools` and super-admin `users`) has a `school_id` column
- Every SELECT/UPDATE/DELETE filters on `school_id` from the JWT — enforced by a SQLAlchemy event listener in `app/db/tenant_filter.py`, not by developers remembering
- Qdrant: one collection per school, named `school_{school_id}`. Student retrieval always passes a Qdrant `Filter` on `class_id` — this is the actual security boundary for the knowledge base
- Cross-tenant lookup returns **404, not 403** — do not leak that a resource exists
- Write an integration test that proves this: log in as school A, look up school B's document UUID → 404
- Parent of student X cannot read student Y's data even in the same school. Enforced by `parent_student_link` join check in every parent route.

### 4.7 Feature Flags

`School.features_json` (JSONB) controls which subsystems are active per school:

```json
{ "voice": true, "ocr": true, "quiz": true, "youtube": true }
```

Check the relevant flag before invoking each subsystem. A low-bandwidth school can turn off voice/OCR without a code change.

---

## 5. Audit Logging

Every state-changing action and every sensitive read is recorded in `audit_logs`.

**Columns:** `id, ts, actor_user_id, actor_role, school_id (null for super admin), action, target_type, target_id, ip, user_agent, request_id, payload_hash, status (success|failure), error_msg`

**Actions to log:**
`LOGIN_SUCCESS, LOGIN_FAILURE, LOGOUT, TOKEN_REFRESH, PASSWORD_RESET,`
`SCHOOL_CREATE, SCHOOL_SUSPEND, SCHOOL_DELETE,`
`USER_CREATE, USER_DEACTIVATE, USER_PASSWORD_RESET,`
`CLASS_CREATE, SUBJECT_CREATE, TEACHER_ASSIGN, STUDENT_ENROLL, PARENT_LINK,`
`MATERIAL_UPLOAD (type=pdf|docx|txt|url|youtube), MATERIAL_DELETE, MATERIAL_REINDEX,`
`TIMETABLE_CREATE, EXAM_TIMETABLE_CREATE,`
`CHAT_MESSAGE (hash of message + retrieved chunk IDs),`
`QUIZ_GENERATE, QUIZ_APPROVE, QUIZ_SUBMIT, ANSWER_FLAGGED, ANSWER_GRADE_OVERRIDE,`
`PARENT_VIEW_CHILD,`
`SUPER_ADMIN_DATA_ACCESS (with reason text)`

Implement as a decorator + middleware — automatic, not manual per-route.

---

## 6. Dynamic Student Prompting

The core teaching philosophy, assembled fresh per request — not a static system prompt.

**Built from every time:**
- Student's grade, age band, subject
- **Reply language** (`lang`) — the ISO 639-1 code detected from the student's question (`lang_detected` in `SessionState`). The answer MUST be in this language.
- Live mastery score for the specific topic (from Progress agent)
- Retrieved, cited chunks from RAG
- Student's stated interests, if any (used to pick personally relevant examples)

```python
# app/agents/prompts/tutor_prompt.py

# Human-readable label for each supported reply language.
LANG_NAMES = {
    "en": "English", "gu": "Gujarati", "hi": "Hindi", "mr": "Marathi",
    "ta": "Tamil", "te": "Telugu", "bn": "Bengali", "kn": "Kannada",
    "ml": "Malayalam", "pa": "Punjabi", "ur": "Urdu",
}

# Sentence budget per mastery band — keeps low-mastery answers short.
LENGTH_BUDGET = {"starting": 4, "building": 7, "mastered": 12}


def build_tutor_prompt(
    student,                 # .name, .grade, .subject, .interests (optional)
    mastery_score: int,
    topic: str | None,       # may be None on a fresh free-form question
    retrieved_chunks: str,
    history: str,
    question: str,
    lang: str = "en",        # ISO 639-1 from lang_detected — answer language
) -> str:
    mastery_band = (
        "just starting out"    if mastery_score < 40 else
        "building confidence"  if mastery_score < 70 else
        "nearly mastered"
    )
    band_key = "starting" if mastery_score < 40 else "building" if mastery_score < 70 else "mastered"
    max_sentences = LENGTH_BUDGET[band_key]
    lang_name = LANG_NAMES.get(lang, "English")

    # Fix #5: topic may be unknown on a free-form question. Fall back to the
    # subject so the mastery band is never anchored to a wrong topic guess.
    topic_label = topic if topic else f"{student.subject} (general)"

    interest_line = (
        f"They've mentioned an interest in {student.interests} — "
        f"use it to pick the real-life example when it fits naturally."
        if student.interests else ""
    )
    return f"""You are a patient, encouraging tutor for {student.name},
a Grade {student.grade} student studying {student.subject}.
Their mastery of "{topic_label}" is currently {mastery_score}/100 ({mastery_band}).
{interest_line}

LANGUAGE RULE (non-negotiable): Write your ENTIRE reply in {lang_name}
(language code: "{lang}") — the language the student asked in. Every
sentence, including the example, the explanation, the encouragement and
the follow-up question, must be in {lang_name}. Keep proper nouns, source
filenames and URLs exactly as they appear in the retrieved material.

GROUNDING RULE: Base every factual claim ONLY on the retrieved material
provided below. Immediately after each claim, cite its source. Emit each
citation on its own line, in this exact format (do NOT translate the tag):
  - PDF/DOCX/TXT  →  [source: filename.pdf, p. 12]
  - URL           →  [source: Article Title, url: https://...]
  - YouTube       →  [source: Video Title, t: 1m24s, url: https://youtu.be/ID?t=84]
Use the filename / title / timestamp EXACTLY as given in the retrieved
context — never invent a page number, title or timestamp. If a field is
missing, omit just that field, keep the rest. If the answer isn't in the
material, say (in {lang_name}):
"I don't see that in your class materials — ask your teacher to upload notes on [topic]."
Do NOT answer from general knowledge.

TEACHING RULES:
1. ALWAYS lead with one real-life, relatable example BEFORE the formal
   explanation. Choose from: sport, food, money, local festivals, distances
   the student actually travels, everyday objects. The example must come
   FIRST, the theory second.
2. NEVER say "wrong" or "incorrect" bluntly. If there is a misconception,
   name what they got right first, then correct gently:
   "You're close — the part to adjust is..."
3. Match depth to mastery — and respect the length budget:
   - Under 40: one idea + one example only, then ask a check-question
     before adding anything more. HARD LIMIT: {max_sentences} sentences.
   - 40–70: two ideas, one example, one follow-up question.
     HARD LIMIT: {max_sentences} sentences.
   - Over 70: move faster, cover the concept fully, offer a challenge.
     Aim for at most {max_sentences} sentences.
4. End EVERY response with:
   a) One specific, EARNED encouragement tied to something the student
      actually did in THIS question — a correct step, a good instinct, real
      effort. Never generic praise. For example:
        GOOD: "You already spotted that the pieces must be equal — that's
               the exact idea most people miss."
        BAD:  "Great job!" / "Well done!" / "You're so smart!"
   b) One optional next-step question to keep them thinking.

Retrieved context:
{retrieved_chunks}

Conversation so far:
{history}

Student's question: {question}"""
```

**Citation parsing (Phase 3) must be forgiving.** The `[source: ...]` tag is a
display convenience, not a contract the model always honours perfectly. The
parser MUST tolerate: extra/missing spaces, a missing page/timestamp, the tag
inline vs on its own line, and casing drift (`Source:`). Match with a lenient
regex (e.g. `\[source:\s*(.+?)\]`) and then map the extracted filename/title
back to the actual `retrieved_chunks` metadata to recover the authoritative
`page_or_ts` and `r2_url` — never trust the model's page number over the
retrieved chunk's own metadata.

**Worked example (Grade 6, mastery 35/100, topic "Fractions", `lang="en"`):**
Question: *"Why isn't 1/2 + 1/3 = 2/5?"*

Expected output shape (not an exact script — the model should produce its own version):
"Picture one roti cut into 2 equal pieces, and a different roti cut into 3 equal pieces. You eat one piece from each. You might think 'I had 2 pieces out of 5 total' — but that's only right if all 5 pieces were the same size. A half-roti piece is bigger than a third-roti piece, so you can't add them directly. You first need both rotis cut into equal-size pieces. Six pieces works (sixths). 1/2 becomes 3/6, and 1/3 becomes 2/6, so together: 5/6. That's what finding a common denominator actually means.
[source: maths_chapter3.pdf, p. 7]
You've already got the intuition that the pieces should be equal — you're right about that, the adjustment is just: equal to each other, not equal to the total. Can you try 1/4 + 1/2 using this same roti idea?"

*(For a Gujarati question the same answer shape is produced entirely in Gujarati, with the `[source: maths_chapter3.pdf, p. 7]` tag left untranslated.)*

The Quiz Master and Evaluator agents use the same template structure — swap the teaching rules (1–4) for their own rules, keeping the mastery-band logic, the length budget, the language rule, and the interest-based example selection.

---

## 7. Agents (LangGraph)

Five agents share one typed `SessionState`. The LangGraph graph runs:

```
safety_in → Orchestrator → {Tutor | QuizMaster | Evaluator} → safety_out → Progress → END
```

### 7.1 SessionState

```python
class SessionState(TypedDict):
    student_id: str
    school_id: str
    class_id: str
    subject_id: str | None
    message: str
    input_mode: Literal["text", "voice"]
    lang_detected: str          # ISO 639-1 — e.g. "en", "gu", "hi"
    intent: Literal["explain", "quiz", "grade", "progress", "unknown"]
    retrieved_chunks: list[dict]  # {text, source_type, source_ref, page_or_ts, score}
    answer: str | None
    citations: list[dict]         # {source_type, source_ref, page_or_ts, r2_url}
    quiz: dict | None
    grade: dict | None            # {score, feedback, missed_concepts, confidence}
    mastery_updates: list[dict]
    model_role_used: str          # e.g. "fast_chat", "reasoning", "multilingual_indic"
    provider_used: Literal["gemini", "nvidia"]
    safety_blocked: bool
    safety_reason: str | None
    errors: list[str]
```

### 7.2 Orchestrator
Classifies intent from the student's message. Uses `llm_router.chat(task="classify", ...)` — defaults to `fast_chat` role (cheapest). Routes to Tutor, QuizMaster, or Evaluator.

### 7.3 Tutor
1. Detect language of the question (`lang_detected`)
2. Retrieve top-20 from Qdrant, filtered by `school_id` + `class_id` + optional `subject_id`
3. (Reranker optional — add after core loop works, not in Phase 3)
4. Call `build_tutor_prompt(..., lang=lang_detected)` → `llm_router.chat(task="explain", lang_hint=lang_detected)`. The prompt forces the reply into `lang_detected` and applies the mastery-band length budget.
5. Parse citations from the answer with the **forgiving** parser (see §6), then map each parsed source back to the retrieved chunk metadata to recover the authoritative `page_or_ts` + R2 URL for file-type citations
6. Return `{answer, citations}`

Refuses to answer outside context. Always cites. Always replies in the student's language.

### 7.4 Quiz Master
For the current student, picks the topic with the lowest mastery score within their enrolled subjects. Generates 5 questions: 3 MCQ + 2 short-answer. Each question has a difficulty (easy/medium/hard) and XP value. Persists to `quizzes` table with `status = "draft"`. Teacher approves → `status = "approved"`. Students see only approved quizzes.

### 7.5 Evaluator
Grades free-text answers against retrieved source material. Returns `{score: 0-1, feedback: str, missed_concepts: [str], confidence: 0-1}`. Uses `llm_router.chat(task="evaluate")` → `reasoning` role (Gemini `gemini-2.5-flash` → NVIDIA reasoning fallback). If `score < 0.4` AND `confidence < 0.7` → flag for teacher review queue.

### 7.6 Progress
Updates `mastery_score` for `(student_id, subject_id, topic)` using exponential moving average:
`new_score = round(0.7 * old_score + 0.3 * attempt_score * 100)`
Topic extracted from the question via keyword extraction (Phase 4) → upgrade to embedding-based topic clustering later.

### 7.7 Safety (not a LangGraph node — a mandatory wrapper)

**What's in this build:**
- Gemini's built-in safety filtering runs free on every Gemini call — first line of defense, zero extra requests
- Topic-control is a prompting rule in `build_tutor_prompt` — refuses off-subject questions, redirects to teacher
- Every chat message audit-logged

**What's deferred:** the NVIDIA jailbreak classifier (`nemoguard-jailbreak-detect`) is real defense-in-depth but takes a pre-computed embedding as input (not raw text) — that's its own integration task. Add it after Phase 3 when you can measure its free-tier cost per message.

---

## 8. RAG Pipeline

**Ingestion (runs in BackgroundTasks after upload):**

1. **Upload** → original file saved to Cloudflare R2: `school_{school_id}/class_{class_id}/{doc_id}.pdf`
   R2 URL stored in `Document.storage_url` — this is what the citation viewer opens

2. **Extract**:
   - PDF with selectable text → `pypdf`, track page numbers
   - PDF with image-only pages (scanned / photographed) → NVIDIA OCR role from registry; cache result forever in `OcrCache(doc_id, page, text)`
   - DOCX → `python-docx`
   - TXT → direct read
   - URL → `httpx` fetch + `trafilatura` clean
   - YouTube → `youtube-transcript-api`; each chunk retains the start timestamp of its first segment as `page_or_ts`
   - Image upload (`.jpg`/`.png` phone notes) → NVIDIA OCR role

3. **Chunk** → ~600 tokens, ~100 overlap, retain `page_or_ts` + `lang` metadata

4. **Embed** → Gemini `text-embedding-004` (English), NVIDIA embeddings role (non-English / Indic)

5. **Store** → Qdrant Cloud, collection `school_{school_id}`:
   - Payload per point: `{doc_id, class_id, subject_id, source_type, source_ref, page_or_ts, lang, r2_url}`
   - Auto-create the collection on first upload for a school (idempotent, vector size 768, Cosine distance)
   - Mirror chunk metadata in Postgres `chunks` table (Qdrant point ID = chunk UUID) for audit + deletion

6. **Retrieve** → top-k similarity search in Qdrant, always filtered by `class_id` (this filter is the security boundary — test it explicitly with a student from a different class)

---

## 9. Object Storage (Cloudflare R2)

```python
# app/services/r2_client.py
import boto3

def get_r2():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )

def upload_file(file_bytes: bytes, key: str, content_type: str) -> str:
    get_r2().put_object(Bucket=settings.R2_BUCKET_NAME, Key=key,
                        Body=file_bytes, ContentType=content_type)
    return f"{settings.R2_PUBLIC_URL}/{key}"

def delete_file(key: str):
    get_r2().delete_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
```

R2 key pattern: `school_{school_id}/class_{class_id}/{doc_id}.{ext}`

---

## 10. Data Model

```python
# Schools
School(id, name, address, is_active, features_json, timezone,
       academic_year_start, academic_year_end, created_at)

# Users (all roles in one table)
User(id, name, email, password_hash,
     role: Enum[super_admin|school_admin|teacher|student|parent],
     school_id,  # NULL for super_admin
     interests,  # optional, for student prompt personalisation
     grade,      # for students
     is_active, created_at)

# Classes & structure
ClassSection(id, school_id, name, grade_level)
Subject(id, school_id, name)
TeacherAssignment(id, teacher_id, class_id, subject_id)
Enrollment(id, student_id, class_id)
ParentStudentLink(id, parent_id, student_id, consent_given_at)

# Documents & chunks
Document(id, class_id, subject_id, uploaded_by_teacher_id, school_id,
         filename, storage_url,  # R2 URL
         source_type: Enum[pdf|docx|txt|url|youtube|image],
         source_ref,             # filename or URL
         status: Enum[pending|indexed|failed],
         uploaded_at)

Chunk(id, doc_id, class_id, subject_id, school_id, page_or_ts, lang,
      qdrant_point_id, created_at)

# Learning
ChatSession(id, student_id, class_id, subject_id, created_at)
Message(id, session_id, role: Enum[user|assistant], content,
        citations_json, model_role_used, provider_used, created_at)

Quiz(id, class_id, subject_id, topic, questions_json,
     created_by_teacher_id, school_id,
     status: Enum[draft|approved], created_at)
QuizAttempt(id, quiz_id, student_id, answers_json, score,
            feedback_json, attempted_at)

ProgressRecord(id, student_id, subject_id, topic, mastery_score,
               last_reviewed_at)

# Timetables
Timetable(id, teacher_id, class_id, subject_id, school_id,
          day_of_week: int,  # 0=Mon … 5=Sat
          period_number: int, room)
ExamTimetable(id, class_id, subject_id, school_id, exam_name,
              exam_date, start_time, duration_minutes, syllabus_ref)

# Ops
AuditLog(id, ts, actor_user_id, actor_role, school_id, action,
         target_type, target_id, ip, user_agent, request_id,
         payload_hash, status, error_msg)
LlmUsage(id, ts, school_id, user_id, provider, model_role,
         task, prompt_tokens, completion_tokens, latency_ms, status)
OcrCache(doc_id, page, model, text, created_at)  # PK: (doc_id, page)
```

---

## 11. API Endpoints

All routes prefixed `/api/v1/`. Every protected route enforces `require_role(...)` + tenant scope.

```
# Auth
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
GET    /api/v1/auth/me
POST   /api/v1/auth/password-reset

# Super Admin
POST   /api/v1/admin/schools
PATCH  /api/v1/admin/schools/{id}
DELETE /api/v1/admin/schools/{id}
POST   /api/v1/admin/schools/{id}/admins
GET    /api/v1/admin/dashboard

# School Admin
POST   /api/v1/school/users
POST   /api/v1/school/users/bulk          # CSV import
GET    /api/v1/school/users
PATCH  /api/v1/school/users/{id}
POST   /api/v1/school/classes
POST   /api/v1/school/subjects
POST   /api/v1/school/teacher-assignments
POST   /api/v1/school/enrollments
POST   /api/v1/school/parent-links
GET    /api/v1/school/dashboard
GET    /api/v1/school/audit

# Teacher
POST   /api/v1/teacher/materials/file     # multipart — PDF/DOCX/TXT
POST   /api/v1/teacher/materials/url
POST   /api/v1/teacher/materials/youtube
GET    /api/v1/teacher/materials
DELETE /api/v1/teacher/materials/{id}
POST   /api/v1/teacher/timetable
POST   /api/v1/teacher/exam-timetable
GET    /api/v1/teacher/dashboard
GET    /api/v1/teacher/classes/{class_id}/progress
GET    /api/v1/teacher/flagged-answers
POST   /api/v1/teacher/flagged-answers/{id}/override
POST   /api/v1/teacher/quizzes/{id}/approve

# Student
GET    /api/v1/student/dashboard
POST   /api/v1/student/chat              # SSE stream
POST   /api/v1/student/voice/stt        # fallback if browser lacks Web Speech
GET    /api/v1/student/voice/tts        # fallback TTS → NVIDIA
GET    /api/v1/student/classes
GET    /api/v1/student/timetable
GET    /api/v1/student/exam-timetable
GET    /api/v1/student/quizzes
POST   /api/v1/student/quizzes/{id}/submit
GET    /api/v1/student/progress
GET    /api/v1/student/history
GET    /api/v1/student/data-export       # GDPR-style JSON export

# Parent
GET    /api/v1/parent/children
GET    /api/v1/parent/children/{id}/dashboard
GET    /api/v1/parent/children/{id}/history
GET    /api/v1/parent/children/{id}/timetable
GET    /api/v1/parent/children/{id}/exam-timetable

# Ops
GET    /api/v1/health
DELETE /api/v1/admin/users/{id}/data    # data deletion (compliance)
```

---

## 12. Folder Structure

```
ashashala/
├── config/
│   └── model_registry.yaml           # fill before Phase 1
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI factory, Sentry init, global exception handler
│   │   ├── core/
│   │   │   ├── config.py             # pydantic-settings, loads .env, crashes if missing
│   │   │   └── exceptions.py         # global exception handler → {error_code, message, trace_id}
│   │   ├── db/
│   │   │   ├── session.py            # async SQLAlchemy engine + session factory
│   │   │   └── tenant_filter.py      # event listener forcing school_id on every query
│   │   ├── auth/
│   │   │   ├── jwt.py
│   │   │   ├── password.py
│   │   │   └── routes.py
│   │   ├── deps.py                   # get_db, get_current_user, require_role, get_tenant_db
│   │   ├── models/                   # SQLAlchemy 2.x typed models (one file per table)
│   │   ├── schemas/                  # Pydantic v2 request / response schemas
│   │   ├── routes/
│   │   │   ├── admin.py
│   │   │   ├── school_admin.py
│   │   │   ├── teacher.py
│   │   │   ├── student.py
│   │   │   ├── parent.py
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── model_registry.py     # loads config/model_registry.yaml
│   │   │   ├── gemini_client.py      # retry, backoff, timeout, usage logging
│   │   │   ├── nvidia_client.py      # openai SDK → NVIDIA base URL, per-model rate limit
│   │   │   ├── llm_router.py         # task + lang routing, fallback chain, usage logging
│   │   │   ├── embed_router.py       # Gemini text-embedding-004 + NVIDIA fallback
│   │   │   ├── r2_client.py          # Cloudflare R2 upload/delete/url
│   │   │   ├── ocr_service.py        # NVIDIA OCR, result cached in OcrCache
│   │   │   ├── asr_service.py        # NVIDIA ASR server-side fallback
│   │   │   ├── tts_service.py        # NVIDIA TTS server-side fallback
│   │   │   ├── translate_service.py  # NVIDIA translation (deferred — wire up if needed)
│   │   │   ├── audit_service.py      # emit + query audit_logs
│   │   │   ├── rag/
│   │   │   │   ├── chunker.py
│   │   │   │   ├── embedder.py       # uses embed_router
│   │   │   │   ├── store.py          # Qdrant Cloud wrapper
│   │   │   │   └── retriever.py      # top-k filtered by class_id
│   │   │   └── ingestion/
│   │   │       ├── pdf.py            # pypdf + OCR for image-only pages
│   │   │       ├── docx.py
│   │   │       ├── txt.py
│   │   │       ├── url.py            # httpx + trafilatura
│   │   │       ├── youtube.py        # youtube-transcript-api with timestamps
│   │   │       └── image.py          # phone-photo → OCR → chunk
│   │   ├── agents/
│   │   │   ├── state.py              # SessionState TypedDict
│   │   │   ├── orchestrator.py
│   │   │   ├── tutor.py
│   │   │   ├── quiz_master.py
│   │   │   ├── evaluator.py
│   │   │   ├── progress.py
│   │   │   ├── safety.py             # Gemini built-in + topic-control prompt guard
│   │   │   ├── graph.py              # LangGraph wiring
│   │   │   └── prompts/
│   │   │       ├── tutor_prompt.py   # build_tutor_prompt() — Section 6
│   │   │       ├── quiz_prompt.py
│   │   │       └── eval_prompt.py
│   ├── alembic/                      # migrations
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_phase1_health.py
│   │   ├── test_phase1_llm_router.py
│   │   ├── test_phase2_rbac.py
│   │   ├── test_phase2_tenant_isolation.py
│   │   ├── test_phase2_rag.py
│   │   ├── test_phase2_ingestion_url.py
│   │   ├── test_phase2_ingestion_youtube.py
│   │   ├── test_phase2_timetable.py
│   │   ├── test_phase2_parent.py
│   │   ├── test_phase2_audit.py
│   │   ├── test_phase3_tutor.py
│   │   ├── test_phase3_gujarati.py
│   │   └── test_phase4_agents.py
│   ├── scripts/
│   │   └── seed.py                   # super admin from .env; full demo data for Phase 6
│   ├── .env.example
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── routes/
│   │   │   ├── login.tsx
│   │   │   ├── admin/                # super admin dashboards
│   │   │   ├── school/               # school admin dashboards
│   │   │   ├── teacher/              # teacher screens
│   │   │   ├── student/              # student chat + quiz + progress
│   │   │   └── parent/               # parent read-only dashboards
│   │   ├── components/
│   │   │   ├── voice/                # VoiceInputButton (Web Speech API) + TTSPlayer
│   │   │   ├── citations/            # ClickableCitation — PDF/YouTube/URL
│   │   │   ├── quiz/                 # gamified: timer, streak, XP, badges
│   │   │   ├── dashboard/            # MasteryRadar (Recharts), ActivityFeed, TimetableGrid
│   │   │   └── layout/               # Sidebar, RoleGuard, Loading skeletons
│   │   ├── api/                      # typed client from FastAPI OpenAPI schema
│   │   ├── stores/                   # zustand: auth, voice settings
│   │   └── .env.example
│   ├── package.json
│   ├── tailwind.config.ts
│   └── vite.config.ts
├── deploy/
│   ├── render.yaml                   # primary backend deploy
│   └── northflank.json               # alternative backend deploy
├── vercel.json                       # frontend deploy + SPA rewrite rules
├── .github/
│   └── workflows/
│       ├── ci.yml                    # pytest + vitest on every PR
│       └── deploy.yml                # build Docker image + trigger Render redeploy on main
├── .gitignore                        # .env, __pycache__/, *.pyc, .venv/, node_modules/, dist/
├── README.md
└── PROJECT_PROMPT.md                 # this file
```

---

## 13. Global Rules for the Coding Agent

1. **Phased execution.** Build ONLY the current phase. Stop at the checkpoint. Print the done-checklist. Wait for "go" before the next phase.
2. **Verify before declaring done.** Run the phase's test suite. Fix failures before stopping.
3. **No secrets in code.** Every secret from `.env` via `pydantic-settings`. Crash on startup if missing.
4. **No hardcoded model names** in any Python file. Always call `model_for(role, provider)`.
5. **Type everything.** Pydantic v2 for every request/response. SQLAlchemy 2.x typed models. No `dict[str, Any]` in public signatures.
6. **Tenant safety.** Every query filtering on `school_id` from JWT via the event listener. Write and pass a cross-tenant isolation test.
7. **`/api/v1/` prefix** on every route from day one.
8. **Global exception handler** from day one — returns `{error_code, message, trace_id}`, never a raw stack trace.
9. **Per-call timeouts** on every external call (Gemini, NVIDIA, Qdrant, R2). Configured in `config.py`.
10. **Small commits.** One logical change per commit. Conventional Commits style.
11. **Ask before changing the stack.** Propose + explain, do not silently swap.

---

## 14. Phase Plan

### Phase 1 — Foundation

**Goal:** repo set up, all external service connections verified, model registry loaded, one real Gemini call and one real NVIDIA call both return text.

**Deliverables:**
- `.gitignore` committed FIRST (before any `.env` can be added)
- `config/model_registry.yaml` with all role IDs filled in from the live catalog
- `app/core/config.py` — pydantic-settings, loads ALL env vars, crashes if any missing
- `app/core/exceptions.py` — global exception handler → `{error_code, message, trace_id}`
- `app/db/session.py` — async Neon Postgres, `ping_db()` runs `SELECT 1`
- `app/services/model_registry.py` — `model_for(role, provider)` loader
- `app/services/gemini_client.py` — retry, backoff, timeout, `health_check()`
- `app/services/nvidia_client.py` — openai SDK → NVIDIA, per-model rate-limit, `health_check()`
- `app/services/llm_router.py` — full routing table from Section 3, usage logging to `LlmUsage`
- `app/services/r2_client.py` — `upload_file()`, `delete_file()`, `ping_r2()`
- `app/services/rag/store.py` — Qdrant Cloud client, `ping_qdrant()`
- `app/main.py` — FastAPI app, Sentry init, global exception handler mounted
- `GET /api/v1/health` — returns:
  ```json
  {
    "status": "ok",
    "db": "ok",
    "vector_db": "ok",
    "r2": "ok",
    "gemini": "ok",
    "nvidia_llm": "ok",
    "nvidia_ocr": "ok",
    "version": "0.1.0"
  }
  ```
- `tests/test_phase1_health.py` — hits `/api/v1/health`, asserts all services "ok"
- `tests/test_phase1_llm_router.py` — four tests:
  (a) English question → Gemini `gemini-2.5-flash-lite`
  (b) Gujarati question (`lang_hint="gu"`) → NVIDIA Sarvam-M (primary)
  (c) Simulated Gemini 429 → falls back to NVIDIA fast_chat
  (d) `task="evaluate"` → `gemini-2.5-flash`, simulated 429 → NVIDIA reasoning
- `.env.example` with ALL placeholder var names
- `README.md` — Neon setup, Qdrant Cloud setup, R2 setup, Gemini key, NVIDIA key, `uvicorn` run command, how to fill `model_registry.yaml`

**Checkpoint:**
```
✅ Phase 1 complete
- [ ] /api/v1/health → all services "ok" against real free-tier accounts
- [ ] model_registry.yaml filled with verified current model IDs
- [ ] Gemini client: gemini-2.5-flash-lite default (not 2.0-flash — shut down)
- [ ] NVIDIA client: health_check passes
- [ ] LLM router: Gujarati → Sarvam-M, English → Gemini Flash-lite, 429 fallback works
- [ ] Neon Postgres ping passes
- [ ] Qdrant Cloud ping passes
- [ ] Cloudflare R2 ping passes
- [ ] Sentry initialised (DSN in env, no crash on startup)
- [ ] Global exception handler installed
- [ ] .env gitignored, .env.example committed
- [ ] All Phase 1 tests pass

Ready for Phase 2? (yes/no)
```

---

### Phase 2 — Auth, RBAC, 5 Roles, Tenancy, RAG Ingestion, Timetables, Audit

**Goal:** the full admin → school → teacher → student → parent skeleton. Super Admin creates a school, School Admin sets up classes and users, Teacher uploads all three material types (file/URL/YouTube), Parent sees their linked child's name. Every action in `audit_logs`.

**Deliverables:**
- All SQLAlchemy models from Section 10 + Alembic first migration
- Tenant-scoped DB session via SQLAlchemy event listener (inject `school_id` from JWT on every query)
- Auth routes: `/login`, `/refresh`, `/me`, `/password-reset`. JWT payload includes `{sub, role, school_id, class_ids, subject_ids, linked_student_ids}`
- `require_role(*roles)` + tenant-scope dependency
- `audit_service.py` as a decorator + middleware — automatic, not manual
- All routes from Section 11, every role implemented (no AI yet — CRUD only)
- Feature flags: check `School.features_json` before invoking voice/OCR/YouTube subsystems
- Parent routes: every request writes `PARENT_VIEW_CHILD` to audit log
- RAG ingestion pipeline (BackgroundTasks):
  - PDF/DOCX/TXT: parse → detect language → chunk → embed (Gemini or NVIDIA by lang) → upsert to Qdrant + mirror in Postgres chunks table
  - Scanned/image-only PDF pages: NVIDIA OCR role → cache in `OcrCache(doc_id, page)` → chunk → embed
  - URL: httpx + trafilatura → chunk → embed
  - YouTube: youtube-transcript-api → chunk with timestamps → embed
  - All material: upload original file to R2 first, store `storage_url` on Document row
  - Auto-create Qdrant collection on first school upload (idempotent, 768 dims, Cosine)
- Parent-consent capture: `ParentStudentLink.consent_given_at` set at link time
- Data export endpoint: `/api/v1/student/data-export` → student's messages, quiz attempts, mastery records as JSON
- Data deletion endpoint: `/api/v1/admin/users/{id}/data` (Super Admin only)
- One-page privacy policy statement in `docs/privacy.md`

**Tests:** `test_phase2_rbac.py`, `test_phase2_tenant_isolation.py` (cross-school 404), `test_phase2_rag.py` (upload PDF → correct chunks in Qdrant), `test_phase2_ingestion_url.py`, `test_phase2_ingestion_youtube.py` (timestamps present), `test_phase2_timetable.py`, `test_phase2_parent.py` (read own child ok; read other child 403), `test_phase2_audit.py` (every action above produces a correct audit row)

**Checkpoint:** all tests pass. Manual smoke: Super Admin creates school → School Admin creates class/subject/teacher/student/parent/timetable → Teacher uploads file+URL+YouTube → Parent sees child's name + timetable. **Stop, ping me.**

---

### Phase 3 — Tutor Agent with Dynamic Prompting + Voice

**Goal:** student asks a question (text or voice), gets a streaming cited answer built from Section 6's dynamic prompt. Gujarati voice question must work end to end.

**Deliverables:**
- `app/agents/prompts/tutor_prompt.py` — `build_tutor_prompt()` exactly as in Section 6
- `app/agents/tutor.py` — detect lang → retrieve from Qdrant (filtered by class_id) → assemble prompt → call `llm_router.chat(task="explain", lang_hint=...)` → parse citations → attach R2 URLs
- `app/agents/safety.py` — topic-guard wrapper (Gemini's built-in + prompt rule)
- `POST /api/v1/student/chat` — SSE stream. Final event: `event: citations` carries citation array
- `POST /api/v1/student/voice/stt` — server-side fallback when browser lacks Web Speech API → NVIDIA ASR role
- `GET /api/v1/student/voice/tts` — server-side fallback TTS → NVIDIA TTS role
- Chat message audit log entry on every message (hashed content + retrieved chunk IDs)

**Tests:** `test_phase3_tutor.py` — seed a tiny PDF + URL fixture + fake YouTube transcript; ask one question per source type; assert citation format correct for each. `test_phase3_gujarati.py` — Gujarati question routes to Sarvam-M (or Maverick fallback), answer is non-empty.

**Checkpoint:** test passes. Manual: curl `POST /api/v1/student/chat` with `Accept: text/event-stream`, see streaming tokens + final citations event. **Stop, ping me.**

---

### Phase 4 — Multi-Agent System (LangGraph)

**Goal:** full five-agent system behind one chat endpoint. Quiz Master generates from weak topics. Evaluator grades with feedback. Progress updates mastery.

**Deliverables:**
- `app/agents/state.py` — `SessionState` TypedDict from Section 7.1
- `app/agents/orchestrator.py` — intent classifier (cheap fast_chat call)
- `app/agents/quiz_master.py` — weakest-topic quiz, 3 MCQ + 2 short-answer, status=draft
- `app/agents/evaluator.py` — grades free-text, flags low-confidence for teacher queue, uses reasoning role
- `app/agents/progress.py` — EMA mastery update
- `app/agents/graph.py` — LangGraph: `safety_in → orchestrator → {tutor|quiz|evaluator} → safety_out → progress → END`
- `app/agents/prompts/quiz_prompt.py`, `eval_prompt.py` — same mastery-aware, encouraging style as tutor prompt
- New routes: `POST /api/v1/student/quiz/start`, `POST /api/v1/student/quiz/{id}/submit`, `GET /api/v1/student/progress`, `GET /api/v1/teacher/flagged-answers`, `POST /api/v1/teacher/flagged-answers/{id}/override`, `POST /api/v1/teacher/quizzes/{id}/approve`

**Tests:** `test_phase4_agents.py` — full loop: ask → quiz → submit → mastery updates → next quiz pulls weakest topic → teacher flags queue populated.

**Checkpoint:** test passes. Full loop works in curl. **Stop, ping me.**

---

### Phase 5 — React Frontend

**Goal:** real UI for all five roles. Voice in/out. Gamified quiz. Clickable citations. Timetable grid.

**Deliverables:**

**Auth:** login page, JWT in memory + refresh token in httpOnly cookie, redirect-by-role after login, RoleGuard component on every protected route

**Super Admin:** schools table (create/suspend/delete), platform metrics card (active schools, total users, LLM tokens used today per school from `LlmUsage`)

**School Admin:** Users tab (filter by role), Classes & Subjects, Teacher Assignments, Enrollments (CSV upload), Parent Links, School Dashboard (Recharts: per-class mastery bar chart, engagement), Audit Log viewer (filter by action type + date range)

**Teacher:** My Classes & Subjects, Materials (tabbed: File drag-drop + URL paste + YouTube paste + preview), Regular Timetable grid (weekly), Exam Timetable list, Class Progress table (per-student mastery), Flagged Answers queue (review + override grade)

**Student:**
- Dashboard: MasteryRadar (Recharts), today's periods, upcoming exams, recommended next topic
- Chat:
  - Text input + send, streaming answer via SSE
  - Push-to-talk mic button using `SpeechRecognition` (Web Speech API). While held → captures audio → fills input. If browser lacks support → audio uploaded to `/student/voice/stt`
  - TTS toggle: streamed answer spoken via `SpeechSynthesis`. Server fallback: `/student/voice/tts`
  - Voice settings (rate, pitch, voice) in Zustand + localStorage
  - Citations render as chips: PDF chip opens document at page via R2 URL; YouTube chip opens video at timestamp; URL chip opens in new tab
- Quiz Games: countdown timer, streak counter, XP gain animation, level-up modal, badges
- History: all chats, all quiz attempts, all mastery changes

**Parent:** Children list → per-child dashboard (MasteryRadar, read-only), history feed, timetable

Loading skeletons + error toasts + empty states everywhere. Web Speech API degrades gracefully (hide mic button + show tooltip if unsupported).

**Checkpoint:** end-to-end browser demo: Super Admin creates school → School Admin sets up teacher/student/parent → Teacher uploads PDF + YouTube + timetable → Student asks voice question → hears answer → clicks YouTube citation at correct timestamp → takes quiz → earns XP → Parent sees updated mastery. **Stop, ping me.**

---

### Phase 6 — Safety, Seed Data, Deploy, Polish

**Goal:** everything ships on the public internet at $0/month. Demo is one command.

**Deliverables:**
- Safety hardening: explicitly test Gemini's built-in safety fires correctly on a test inappropriate message. Add rate-limiting with `slowapi` on the chat endpoint to protect free Gemini quota.
- Seed data script (`scripts/seed.py`): 1 school, 1 school admin, 2 teachers, 6 students (mix of grades/mastery levels), 2 parents each linked to a different student, sample PDF + YouTube URL pre-ingested and indexed. Print demo credentials to console. Idempotent (safe to run twice).
- LLM cost mini-dashboard: a query over `LlmUsage` surfaced in the School Admin dashboard — tokens used per provider per day, over quota warnings.
- `docs/privacy.md` — one-page data retention + deletion + export policy (required before touching any real students' data)
- Backup documentation: Neon's PITR window documented; a manual Qdrant snapshot export tested once; restore procedure documented in `docs/runbook.md`
- `docs/runbook.md` — "if X breaks, do Y" for the five most likely failure modes (Neon connectivity, Qdrant 503, Gemini quota, Render cold start, R2 upload failure)
- Dockerfile confirmed building cleanly
- `deploy/render.yaml` — Render free Web Service, Docker, auto-deploy from `main`
- `deploy/northflank.json` — alternative always-on deploy config
- `vercel.json` — SPA rewrite rules, `VITE_API_URL` from env
- `.github/workflows/ci.yml` — `pytest` + `vitest` on every PR
- `.github/workflows/deploy.yml` — build Docker image on `main` → push GHCR → trigger Render redeploy via webhook
- README updated: architecture diagram, one-command local setup (`cp .env.example .env` → fill 5 values → `uvicorn` + `npm run dev`), demo credentials, Render cold-start tradeoff documented, how to re-verify `model_registry.yaml` against the live NVIDIA catalog
- `pre-commit` hooks: ruff, black, mypy, eslint, prettier

**Final pre-launch checklist:**
- [ ] Real scanned-PDF page ingests correctly via NVIDIA OCR
- [ ] Cross-tenant access returns 404 in `test_phase2_tenant_isolation.py`
- [ ] Gujarati voice question routes to Sarvam-M and produces a non-empty Gujarati answer
- [ ] The fractions worked example produces an encouraging, example-first answer (not a textbook wall)
- [ ] PDF citation chip opens the original file from R2 at the correct page
- [ ] YouTube citation chip opens at the correct timestamp
- [ ] `/api/v1/health` is fully green against live free-tier accounts
- [ ] `.env` is gitignored, `.env.example` committed with all vars
- [ ] Backup restore tested once (not just documented)
- [ ] Data export endpoint returns valid JSON
- [ ] Data deletion endpoint actually removes rows + Qdrant points + R2 file
- [ ] Render cold-start tradeoff documented in README
- [ ] Demo seed script works in one command and prints login credentials

---

## 15. Start Now

Build **Phase 1 only**.

First action before any code: open `https://build.nvidia.com/models?pageSize=96&filters=publisher%3Anvidia`, find the current model ID for each role in `config/model_registry.yaml`, and fill them all in. Then write `app/services/model_registry.py`. Then build everything else in Phase 1. Do not hardcode any model name string in any Python file.

When Phase 1 is done, print the Phase 1 checkpoint checklist with every item marked ✅ or ❌, fix any ❌, then stop and wait.