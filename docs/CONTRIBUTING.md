# Contributing to AshaShala

> **AshaShala** — A multi-tenant, role-based, agentic AI tutoring platform for real schools. Built 100% open source. Zero paid APIs. Zero paid hosting.

---

## 🎯 Our Mission

Democratize AI-powered education for every school on the planet — regardless of budget, language, or infrastructure. We believe every student deserves a patient, encouraging tutor that speaks their language and cites its sources.

---

## 🌍 Community Goals

- **10,000+ GitHub Stars** — Building a global community of contributors
- **100+ Contributors** — From students, teachers, engineers, researchers worldwide
- **50+ Schools in Production** — Real deployments serving real students
- **10+ Languages Supported** — Starting with Gujarati, Hindi, expanding globally

---

## 🚀 Quick Start for Contributors

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (for local services)
- Free accounts: [Neon](https://neon.tech), [Qdrant Cloud](https://cloud.qdrant.io), [Cloudflare R2](https://dash.cloudflare.com), [Google AI Studio](https://aistudio.google.com), [NVIDIA NGC](https://build.nvidia.com)

### 1. Fork & Clone
```bash
git clone https://github.com/YOUR_USERNAME/ashashala.git
cd ashashala
```

### 2. Backend Setup
```bash
cd backend
cp .env.example .env
# Fill in your API keys (see DEVELOPMENT.md)
uvicorn app.main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

### 4. Run Tests
```bash
# Backend
cd backend && pytest -v

# Frontend
cd frontend && npm test
```

---

## 🤝 How to Contribute

### Types of Contributions Welcome

| Type | Examples | Difficulty |
|------|----------|------------|
| 🐛 **Bug Fixes** | Fix citation parsing, OCR edge cases, auth bugs | Easy–Medium |
| ✨ **Features** | New LLM providers, language support, quiz types | Medium–Hard |
| 📚 **Documentation** | Tutorials, API docs, translation guides | Easy |
| 🧪 **Tests** | Unit, integration, e2e, load testing | Medium |
| 🌐 **Localization** | Add Gujarati, Hindi, Tamil, Marathi, etc. | Medium |
| 🎨 **UI/UX** | Dashboard improvements, accessibility | Medium |
| 🏗️ **Infrastructure** | CI/CD, monitoring, deployment scripts | Hard |

### Contribution Workflow

1. **Pick an Issue** — Browse [Good First Issues](https://github.com/ashashala/ashashala/labels/good%20first%20issue) or [Help Wanted](https://github.com/ashashala/ashashala/labels/help%20wanted)
2. **Comment** — Say "I'll take this!" to avoid duplicate work
3. **Branch** — `git checkout -b feat/your-feature-name` or `fix/bug-description`
4. **Code** — Follow our [Code Style](#code-style) and [Commit Convention](#commit-convention)
5. **Test** — Run the full test suite locally
6. **PR** — Open a Pull Request with description + screenshots (if UI)
7. **Review** — Address feedback, get approval from 2 maintainers
8. **Merge** — Squash & merge, celebrate! 🎉

---

## 📝 Code Style

### Python (Backend)
```bash
# Format
ruff format .
ruff check . --fix

# Type check
mypy app/
```

- **Black/Ruff** formatting (line length 100)
- **Type hints required** — No `Any` in public APIs
- **Pydantic v2** for all schemas
- **SQLAlchemy 2.x** typed models
- **Async/await** everywhere (FastAPI native)

### TypeScript (Frontend)
```bash
# Format
npm run format

# Lint
npm run lint

# Type check
npm run typecheck
```

- **ESLint + Prettier** (configured)
- **Strict TypeScript** — `noImplicitAny: true`
- **Functional components** + hooks only
- **Zustand** for state, **TanStack Query** for server state

### Commit Convention (Conventional Commits)
```
feat: add Gujarati voice input support
fix: resolve citation parsing for YouTube timestamps
docs: update DEVELOPMENT.md with Windows instructions
test: add integration test for cross-tenant isolation
refactor: extract OCR service into separate module
chore: update dependencies
```

**Scope prefixes:** `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `perf:`, `security:`

---

## 🧪 Testing Standards

| Layer | Tool | Coverage Target |
|-------|------|-----------------|
| Unit | `pytest` / `vitest` | 80%+ |
| Integration | `pytest` + Testcontainers | Critical paths |
| E2E | `playwright` | Core user flows |
| Contract | `schemathesis` | API schemas |

**Run before PR:**
```bash
# Backend
cd backend && pytest --cov=app --cov-report=term-missing

# Frontend
cd frontend && npm run test:coverage
```

---

## 🌐 Localization (i18n)

We prioritize **Indic languages** first:
- **Gujarati (gu)** — Primary
- **Hindi (hi)** — Primary
- **Marathi (mr)**, **Tamil (ta)**, **Telugu (te)**, **Bengali (bn)**, **Kannada (kn)**, **Malayalam (ml)**, **Punjabi (pa)**, **Urdu (ur)**

### Adding a Language
1. Add locale to `frontend/src/i18n/locales/`
2. Update `config/model_registry.yaml` with NVIDIA model IDs
3. Add language code to `INDIC_LANGUAGES` set in `llm_router.py`
4. Test with native speakers

---

## 🏷️ Issue & PR Labels

| Label | Meaning |
|-------|---------|
| `good first issue` | Beginner-friendly, mentored |
| `help wanted` | Community contribution needed |
| `language: gujarati` | Language-specific work |
| `area: backend` / `area: frontend` | Code area |
| `priority: high` | Blocking release |
| `security` | Vulnerability fix |
| `breaking-change` | Requires migration |

---

## 👥 Community & Support

- **Discord:** [discord.gg/ashashala](https://discord.gg/ashashala) — Real-time chat, help, showcases
- **GitHub Discussions:** [github.com/ashashala/ashashala/discussions](https://github.com/ashashala/ashashala/discussions) — RFCs, Q&A, announcements
- **Weekly Community Call:** Thursdays 14:00 UTC — [Calendar](https://cal.com/ashashala/community)
- **Twitter/X:** [@ashashala_ai](https://twitter.com/ashashala_ai) — Updates, highlights

---

## 📜 License

**Apache 2.0** — Free for commercial use, modification, distribution. See [LICENSE](../LICENSE).

> By contributing, you agree your contributions are licensed under Apache 2.0.

---

## 🙏 Recognition

All contributors listed in [AUTHORS.md](../AUTHORS.md) and release notes.
Top contributors invited to **Core Maintainer** team (write access, governance vote).

---

## 📞 Questions?

- **Technical:** Open a [Discussion](https://github.com/ashashala/ashashala/discussions/categories/q-a)
- **Security:** Email `security@ashashala.org` (see [SECURITY.md](SECURITY.md))
- **Partnerships:** Email `partnerships@ashashala.org`

---

**Welcome to the community!** 🌟 Your first PR is waiting — check out [Good First Issues](https://github.com/ashashala/ashashala/labels/good%20first%20issue).