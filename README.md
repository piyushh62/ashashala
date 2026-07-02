# AshaShala 🎓

> **A multi-tenant, role-based, agentic AI tutoring platform for real schools.**  
> Built 100% open source. Zero paid APIs. Zero paid hosting.

---

## 📋 Table of Contents

- [Vision](#vision)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
- [LLM Router & Model Registry](#llm-router--model-registry)
- [Architecture](#architecture)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## 🎯 Vision

**AshaShala** enables real schools to run an AI-powered tutoring platform at zero cost. Teachers upload material, students learn through an AI tutor that:

- 🌍 **Speaks natively in Indic languages** (Gujarati, Hindi, Marathi, Tamil, Telugu, Bengali, Kannada, Malayalam, Punjabi, Urdu)
- 📚 **Always cites sources** (page numbers, YouTube timestamps, URLs)
- 💡 **Leads with real-life examples** before textbook explanations
- 🎯 **Adapts to student mastery** with dynamic difficulty levels
- ✨ **Encourages always** — never says "wrong" bluntly

**Five roles. Complete school management:**

| Role | Purpose |
|------|---------|
| **Super Admin** | Onboards schools, monitors platform usage |
| **School Admin** | Manages teachers, students, classes, parents |
| **Teacher** | Uploads material, approves quizzes, tracks class progress |
| **Student** | Chats with AI tutor, takes quizzes, tracks mastery |
| **Parent** | Monitors linked child's progress (read-only) |

---

## ✨ Key Features

### 🔒 Multi-Tenant with Complete Isolation
- Each school's data is fully isolated (tenant-scoped queries on every database call)
- Parents see only their linked child — no data leakage

### 🛡️ Role-Based Access Control (RBAC)
- Server-side permission checks on every API call
- JWT tokens include `school_id` and `role` — used to scope all queries
- 5 distinct roles with granular permissions

### 🤖 Intelligent LLM Routing
- **Indic languages** → NVIDIA multilingual models (Sarvam-M, Maverick)
- **Reasoning tasks** → Gemini 2.5-Flash with fallback
- **Default chat** → Gemini 2.5-Flash-Lite with fallback
- Automatic retry with exponential backoff on 429 (rate limit) and 5xx errors
- Every call logged for audit and usage tracking

### 📚 Content Ingestion
- **PDF parsing** (OCR support for scanned documents)
- **YouTube** (automatic transcript extraction)
- **Web URLs** (content extraction with Trafilatura)
- **Vector RAG** (semantic search via Qdrant Cloud)

### 📊 Audit & Compliance
- Every API call logged with user, action, resource, timestamp
- LLM token usage tracked per school per day
- Super Admin can access support logs when needed

### 🚀 100% Free Hosting
- **Backend**: Render free tier (Python FastAPI)
- **Database**: Neon Postgres (0.5 GB free, scale-to-zero)
- **Vector DB**: Qdrant Cloud (1 GB free)
- **Storage**: Cloudflare R2 (10 GB free, zero egress)
- **LLMs**: Gemini API free tier + NVIDIA NIM dev tier
- **Frontend**: Vercel hobby tier

---

## 🛠️ Tech Stack

| Component | Technology | Free Tier |
|-----------|-----------|-----------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn | ✅ OSS |
| **Database** | Neon Postgres (async SQLAlchemy 2.x + Alembic) | ✅ 0.5 GB, 100 CU-hrs/mo, scale-to-zero |
| **Vector DB** | Qdrant Cloud | ✅ 1 GB, ~1M vectors @ 768 dims |
| **Object Storage** | Cloudflare R2 | ✅ 10 GB, zero egress |
| **LLM Primary** | Google Gemini API (gemini-2.5-flash-lite, gemini-2.5-flash) | ✅ Free tier |
| **LLM Fallback** | NVIDIA NIM (https://integrate.api.nvidia.com/v1) | ✅ Dev tier, rate-limited |
| **Auth** | JWT (access + refresh), bcrypt password hashing | ✅ OSS |
| **Agent Orchestration** | LangGraph | ✅ OSS |
| **Content Parsing** | `pypdf`, `python-docx`, `youtube-transcript-api`, `trafilatura` | ✅ OSS |
| **Streaming** | Server-Sent Events (SSE) | ✅ Built-in |
| **Error Monitoring** | Sentry free tier | ✅ 5k errors/month free |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Git**
- **Free tier accounts**:
  - [Google AI Studio](https://aistudio.google.com) — Gemini API key
  - [NVIDIA NGC](https://build.nvidia.com) — NVIDIA API key
  - [Neon Postgres](https://neon.tech) — Database
  - [Qdrant Cloud](https://qdrant.tech/cloud) — Vector DB
  - [Cloudflare R2](https://www.cloudflare.com/products/r2) — Object storage
  - [Render](https://render.com) — Hosting (optional for local dev)

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/piyushh62/ashashala.git
cd ashashala

# Set up backend
cd ashashala/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Create .env file from template
cp .env.example .env
# Edit .env with your credentials from above
```

### Environment Variables

**Required** (see `.env.example`):

```env
# LLM Providers
GEMINI_API_KEY=<from Google AI Studio>
NVIDIA_API_KEY=<from NVIDIA NGC>
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

# Database & Vector DB
DATABASE_URL=postgresql+psycopg://user:password@host/dbname?sslmode=require
QDRANT_URL=https://your-cluster.qdrant.io:6333
QDRANT_API_KEY=<from Qdrant Cloud>

# Object Storage (Cloudflare R2)
R2_ACCOUNT_ID=<your account ID>
R2_ACCESS_KEY_ID=<R2 access key>
R2_SECRET_ACCESS_KEY=<R2 secret>
R2_BUCKET_NAME=ashashala-uploads
R2_PUBLIC_URL=https://pub-xxx.r2.dev

# Auth
JWT_SECRET=<64-character random string>
JWT_REFRESH_SECRET=<64-character random string>
SUPER_ADMIN_EMAIL=admin@school.example.com
SUPER_ADMIN_PASSWORD=<temporary, must be changed on first login>

# CORS
ALLOWED_ORIGINS=http://localhost:5173,https://yourdomain.com

# Optional: Error Monitoring
SENTRY_DSN=<from Sentry if using>
```

### Run the Server

```bash
# Development mode (auto-reload)
uvicorn app.main:app --reload --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Access the API

- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

---

## 📁 Project Structure

```
ashashala/
├── backend/                          # FastAPI backend
│   ├── app/
│   │   ├── main.py                   # FastAPI app factory & lifespan
│   │   ├── auth/
│   │   │   ├── jwt.py                # JWT token encode/decode
│   │   │   ├── password.py           # Bcrypt password hashing
│   │   │   └── routes.py             # Login, refresh, logout endpoints
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic Settings (all env vars)
│   │   │   └── exceptions.py         # Custom exceptions & global error handler
│   │   ├── db/
│   │   │   ├── base.py               # SQLAlchemy declarative base
│   │   │   ├── session.py            # Async engine & session factory
│   │   │   └── tenant_filter.py      # Automatic school_id filtering
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── user.py               # User (super_admin, school_admin, teacher, student, parent)
│   │   │   ├── school.py             # School (tenant)
│   │   │   ├── structure.py          # Class, Subject, StudentClass, ClassTeacher
│   │   │   ├── document.py           # Document (uploads), DocumentChunk (RAG)
│   │   │   ├── learning.py           # Quiz, QuizQuestion, StudentQuizAttempt
│   │   │   ├── timetable.py          # Period, TimeSlot (class schedule)
│   │   │   ├── llm_usage.py          # LlmUsage (audit trail)
│   │   │   ├── audit.py              # AuditLog (all API calls)
│   │   │   └── mixins.py             # Common fields (UUIDPk, timestamps)
│   │   ├── routes/                   # API endpoints (role-scoped)
│   │   │   ├── admin.py              # Super Admin endpoints
│   │   │   ├── school_admin.py       # School Admin endpoints
│   │   │   ├── teacher.py            # Teacher endpoints
│   │   │   ├── student.py            # Student endpoints
│   │   │   ├── parent.py             # Parent endpoints
│   │   │   └── health.py             # Health check endpoint
│   │   ├── schemas/                  # Pydantic request/response models
│   │   │   ├── auth.py               # Login, token schemas
│   │   │   ├── admin.py              # Admin schemas
│   │   │   ├── school_admin.py       # School Admin schemas
│   │   │   └── teacher.py            # Teacher schemas
│   │   └── services/
│   │       ├── model_registry.py     # Loads config/model_registry.yaml
│   │       ├── gemini_client.py      # Gemini API wrapper
│   │       ├── nvidia_client.py      # NVIDIA NIM client
│   │       ├── llm_router.py         # Task-based LLM routing
│   │       ├── r2_client.py          # Cloudflare R2 upload/delete
│   │       ├── audit_service.py      # Audit logging middleware
│   │       ├── lang_detect.py        # Language detection
│   │       ├── ingestion/
│   │       │   ├── extractors.py     # PDF, DOCX, YouTube, URL extractors
│   │       │   └── pipeline.py       # Ingest → chunk → embed → store
│   │       └── rag/
│   │           ├── chunker.py        # Semantic chunk splitting
│   │           ├── embedder.py       # Gemini embeddings
│   │           ├── retriever.py      # Qdrant similarity search
│   │           └── store.py          # Qdrant client
│   ├── alembic/                      # Database migrations
│   ├── tests/
│   │   ├── conftest.py               # Pytest fixtures
│   │   └── test_*.py                 # Phase-specific tests
│   ├── config/
│   │   └── model_registry.yaml       # LLM model IDs (SINGLE SOURCE OF TRUTH)
│   ├── pyproject.toml                # Dependencies & tool config
│   ├── requirements.txt               # Pinned dependencies
│   ├── requirements-dev.txt          # Dev dependencies (pytest, black, ruff, etc.)
│   ├── .env.example                  # Template for environment variables
│   └── README.md                     # Backend-specific docs
│
├── config/
│   └── model_registry.yaml           # Shared LLM model registry
│
├── docs/
│   ├── CODE_OF_CONDUCT.md            # Community guidelines
│   ├── CONTRIBUTING.md               # How to contribute
│   ├── GOVERNANCE.md                 # Project governance
│   ├── PURPOSE.md                    # Project purpose & mission
│   ├── IMPLEMENTATION_PLAN.md        # 6-phase delivery roadmap
│   ├── ROADMAP.md                    # Feature roadmap
│   └── privacy.md                    # Privacy & data handling
│
├── LICENSE                           # Open source license
├── PROJECT_PROMPT.md                 # Master specification (READ FIRST)
└── README.md                         # This file
```

---

## 🔧 Configuration

### Model Registry (`config/model_registry.yaml`)

The model registry is the **single source of truth** for all LLM model IDs. Never hardcode model names in Python.

```yaml
roles:
  fast_chat:
    gemini: "gemini-2.5-flash-lite"
    nvidia_fallback: "meta/llama-3.1-8b-instruct"

  reasoning:
    gemini: "gemini-2.5-flash"
    nvidia_fallback: "nvidia/llama-3.1-nemotron-ultra-253b-v1"

  multilingual_indic:
    nvidia_primary: "sarvamai/sarvam-m"
    nvidia_fallback: "meta/llama-4-maverick-17b-128e-instruct"

  vision:
    gemini: "gemini-2.5-flash"
    nvidia_fallback: "meta/llama-3.2-90b-vision-instruct"

  ocr:
    nvidia_primary: "baidu/paddleocr"

  asr:
    nvidia_primary: "nvidia/canary-1b-asr"

  embeddings:
    gemini: "text-embedding-004"
    nvidia_fallback: "nvidia/nv-embedqa-e5-v5"
```

**⚠️ Important**: NVIDIA model IDs drift and get deprecated regularly. Update from the [live catalog](https://build.nvidia.com/models?pageSize=96&filters=publisher%3Anvidia) before each phase.

---

## 👥 Role-Based Access Control (RBAC)

Every API endpoint checks permissions server-side. Tenant isolation is enforced automatically via the `tenant_filter.py` middleware.

### Super Admin (`school_id = NULL`)
- Onboard / suspend / delete schools
- Create first School Admin for a school (one-time password)
- Platform-wide dashboard: active schools, total users, token usage, error rates
- **Cannot** read student/teacher/class content

### School Admin
- Invite/create/deactivate: teachers, students, parents
- Bulk import students (CSV → auto-generate credentials)
- Create classes and subjects
- Assign teachers to `(class, subject)` pairs
- Enroll students into classes
- View class-level progress dashboard

### Teacher
- Upload class material (PDF, image, DOCX, YouTube, URL)
- Create quizzes and questions
- Review student quiz submissions
- View class and individual student progress
- Approve/reject student learning goals

### Student
- Chat with AI tutor (cite-enabled)
- Upload voice messages
- Take quizzes
- View personal mastery dashboard
- Track learning progress

### Parent
- View only linked child's progress (read-only)
- Cannot see other students (including siblings unless explicitly linked)
- Receive progress notifications

---

## 🤖 LLM Router & Model Registry

### Routing Rules

The LLM router automatically chooses the right provider and model based on language and task:

```
Rule 1: Indic Language (gu, hi, mr, ta, te, bn, kn, ml, pa, ur)
        → NVIDIA sarvam-m (primary) → NVIDIA llama-4-maverick (fallback)
        → NO Gemini call

Rule 2: task == "evaluate"
        → Gemini 2.5-Flash → NVIDIA Nemotron Ultra (on 429)

Rule 3: task == "vision"
        → Gemini 2.5-Flash (vision) → NVIDIA vision model (on 429)

Rule 4: Default (explain, chat, classify)
        → Gemini 2.5-Flash-Lite → NVIDIA Llama-3.1-8b (on 429)
```

### Retry Policy

- **Max retries**: 3 attempts
- **Backoff**: Exponential (1s, 2s, 4s) + jitter
- **Triggers**: 429 (rate limit), 5xx (server errors)
- **Fallthrough**: After all retries exhausted, try the next provider in the chain

### Per-Call Timeouts

- Gemini calls: 30s
- NVIDIA calls: 45s (OCR/ASR may be slower)
- Qdrant queries: 10s
- R2 uploads: 60s

---

## 🏗️ Architecture

### Multi-Tenancy

Every query is automatically scoped to `school_id`. The tenant filter middleware (SQLAlchemy event listener) ensures:

```python
# Even if a request tries to access another school's data,
# the filter silently adds: WHERE school_id = <user's school_id>
```

### Authentication & Authorization

1. **Login** → Server validates email/password, returns JWT access + refresh tokens
2. **JWT payload** contains: `user_id`, `role`, `school_id`, expiry
3. **Every endpoint** reads JWT, extracts `school_id`, applies tenant filter
4. **Refresh token** generates new access token after expiry

### LLM Usage Tracking

Every LLM call logs:
- Provider (Gemini, NVIDIA)
- Model role (fast_chat, reasoning, multilingual_indic, etc.)
- Token count (input + output)
- Latency (milliseconds)
- School ID (for billing simulation)
- Task type
- Status (success, error)

### Audit Logging

Every API call logs:
- User ID & role
- School ID
- Action (POST, PUT, DELETE, GET)
- Resource type & ID
- Timestamp
- Response status

---

## 📡 API Documentation

### Health Check

```bash
GET /api/v1/health
```

Returns status of all external services:

```json
{
  "status": "ok",
  "services": {
    "database": { "status": "ok", "latency_ms": 12 },
    "qdrant": { "status": "ok", "latency_ms": 45 },
    "r2": { "status": "ok", "latency_ms": 78 },
    "gemini": { "status": "ok", "latency_ms": 234 },
    "nvidia": { "status": "ok", "latency_ms": 312 },
    "redis": { "status": "ok", "latency_ms": 2 }
  }
}
```

### Authentication

```bash
# Login
POST /api/v1/auth/login
{
  "email": "teacher@school.com",
  "password": "password"
}

# Response
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "token_type": "bearer",
  "expires_in": 3600
}

# Refresh token
POST /api/v1/auth/refresh
Headers: Authorization: Bearer <refresh_token>
```

### Core Endpoints (by role)

**Admin Endpoints** (`/api/v1/admin/`):
- `POST /schools` — Create school
- `GET /schools/{school_id}` — Get school details
- `DELETE /schools/{school_id}` — Suspend school
- `GET /dashboard` — Platform metrics

**School Admin Endpoints** (`/api/v1/school-admin/`):
- `POST /users` — Create user (teacher, student, parent)
- `POST /users/bulk-import` — CSV bulk import
- `POST /classes` — Create class
- `POST /classes/{class_id}/teachers/{teacher_id}` — Assign teacher

**Teacher Endpoints** (`/api/v1/teacher/`):
- `POST /documents/upload` — Upload material
- `GET /documents` — List documents
- `POST /quizzes` — Create quiz
- `GET /classes/{class_id}/progress` — Class progress

**Student Endpoints** (`/api/v1/student/`):
- `POST /chat` — Chat with AI tutor
- `GET /mastery` — Get mastery score
- `POST /quizzes/{quiz_id}/submit` — Submit quiz

**Parent Endpoints** (`/api/v1/parent/`):
- `GET /child/{student_id}/progress` — View child's progress

Full API docs available at `/docs` (Swagger UI) when running locally.

---

## ✅ Testing

Run all tests:

```bash
cd backend
pytest -v
```

### Test Coverage

- **Phase 1 Tests**:
  - `test_phase1_health.py` — Health endpoint (all services "ok")
  - `test_phase1_llm_router.py` — LLM routing (English→Gemini, Gujarati→NVIDIA, fallback)

- **Phase 2+ Tests**:
  - `test_phase2_auth.py` — JWT, login, permissions
  - `test_phase2_rbac.py` — Role-based access control
  - `test_phase2_tenant_isolation.py` — Multi-tenancy
  - `test_phase2_ingestion_url.py` — URL content ingestion
  - `test_phase2_ingestion_youtube.py` — YouTube transcript ingestion
  - `test_phase2_rag.py` — Vector search (RAG)
  - `test_phase2_audit.py` — Audit logging
  - `test_phase2_timetable.py` — Class scheduling

### Running Specific Tests

```bash
# Run Phase 1 only
pytest tests/test_phase1_*.py -v

# Run LLM router tests
pytest tests/test_phase1_llm_router.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

---

## 🚀 Deployment

### Backend (Render)

1. Create a free web service on [Render](https://render.com)
2. Connect GitHub repo
3. Set environment variables (from `.env`)
4. Deploy:
   ```bash
   # Render will auto-detect FastAPI and run:
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

**Note**: Render free tier sleeps after 15 minutes of inactivity. Document this tradeoff clearly for users.

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Add new column"

# Apply migrations
alembic upgrade head
```

### Environment Variables (Production)

All variables must be set on the hosting platform. Never commit `.env`:

```bash
# Check that .env is in .gitignore
grep "^\.env$" .gitignore
```

---

## 📚 Documentation

- **[PROJECT_PROMPT.md](PROJECT_PROMPT.md)** — Master specification (READ FIRST)
- **[IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)** — 6-phase roadmap
- **[CONTRIBUTING.md](docs/CONTRIBUTING.md)** — How to contribute
- **[CODE_OF_CONDUCT.md](docs/CODE_OF_CONDUCT.md)** — Community guidelines
- **[PURPOSE.md](docs/PURPOSE.md)** — Mission & vision

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

### Quick Start for Contributors

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Install dev dependencies: `pip install -r requirements-dev.txt`
4. Run tests: `pytest -v`
5. Format code: `black app/ && ruff check app/ --fix`
6. Commit with clear messages
7. Push and open a pull request

### Code Style

- **Python**: Black (100-char line), Ruff linter
- **Imports**: `isort` (configured in `pyproject.toml`)
- **Type hints**: MyPy strict mode
- **Tests**: Pytest with asyncio support

---

## 📄 License

This project is open source under the [LICENSE](LICENSE) file.

---

## 💬 Community

- **Issues**: [GitHub Issues](https://github.com/piyushh62/ashashala/issues)
- **Discussions**: [GitHub Discussions](https://github.com/piyushh62/ashashala/discussions)
- **Code of Conduct**: [CODE_OF_CONDUCT.md](docs/CODE_OF_CONDUCT.md)

---

## 🎯 Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Foundation & Service Verification | ✅ In Progress |
| 2 | Auth, RBAC, Tenancy, RAG Ingestion, Audit | 📋 Planned |
| 3 | Tutor Agent + Dynamic Prompting + Voice | 📋 Planned |
| 4 | Multi-Agent System (LangGraph) | 📋 Planned |
| 5 | React Frontend (All 5 Roles) | 📋 Planned |
| 6 | Safety, Seed Data, Deploy, Polish | 📋 Planned |

See [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for detailed phase breakdown.

---

## ❓ FAQ

### Why zero paid APIs?

We believe education should be free and accessible. All services used have free tiers that scale to real workloads:
- Gemini API: Free tier covers 1,000+ daily students per school
- Neon: Free tier covers small schools; shared-compute cost ~$0.01/student/month at scale
- Qdrant Cloud: Free tier covers 1M vectors (thousands of documents)

### How does tenant isolation work?

SQLAlchemy event listeners automatically add `WHERE school_id = <user's school_id>` to every query. This is transparent to the application code.

### What if I want to self-host?

Excellent! All dependencies are open source. You'll need:
- PostgreSQL (any version 14+)
- Redis or in-memory queue
- S3-compatible storage (Minio works)
- Optionally: self-hosted Qdrant instance

### Can I use different LLMs?

Absolutely. Add them to `config/model_registry.yaml` and wire in a new client in `app/services/`. The LLM router will automatically route to them.

---

**Built with ❤️ for schools. Let's make AI tutoring accessible to everyone.**
