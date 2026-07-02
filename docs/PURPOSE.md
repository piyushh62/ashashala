# Purpose

## Mission

**AshaShala** is a fully open-source, community-first agentic AI tutoring platform built for real schools — starting with Indian K-12 education. Our mission is to democratize high-quality, personalized AI tutoring by making it completely free, self-hostable, and community-governed.

We believe every student deserves a personal tutor. We believe schools should own their data. We believe AI in education should be transparent, auditable, and community-governed — not locked behind proprietary APIs or vendor lock-in.

## What We Are Building

A multi-tenant, role-based, agentic AI tutoring platform with:

- **Multi-tenant architecture** — Schools (tenants) own their data with full isolation via PostgreSQL row-level security and Qdrant collection-per-tenant
- **Role-based access** — Super Admin, School Admin, Teacher, Student, Parent roles with RBAC
- **Agentic AI tutoring** — LangGraph-orchestrated agents (Tutor, Quiz Master, Evaluator, Progress Tracker, Orchestrator) with dynamic prompting
- **Multilingual support** — English, Gujarati, Hindi, Marathi, Tamil, Telugu, Bengali, and more
- **Voice-first interfaces** — STT/TTS for low-literacy and accessibility contexts
- **RAG with citations** — Qdrant vector search with source citations for every answer
- **Zero paid dependencies** — Gemini API (free tier), NVIDIA NIM (free tier), Neon Postgres (free tier), Qdrant Cloud (free tier), Cloudflare R2 (free tier), Render/Vercel free tiers
- **Full audit trail** — Immutable audit logs for every AI interaction, grading decision, and data access

## Community Goals

| Goal | Target | Timeline |
|------|--------|----------|
| GitHub Stars | 10,000+ | 18 months |
| Contributors | 100+ | 18 months |
| Schools Deployed | 50+ | 24 months |
| Languages Supported | 10+ | 24 months |
| Lesson Packages | 100+ | 18 months |

## Our Promise to the Community

- **100% Open Source** — MIT licensed, forever. No "open core" model.
- **Community Governance** — Major decisions via RFC process with community input
- **Zero Vendor Lock-in** — Self-host on any cloud or on-prem; swap any component
- **Transparent Roadmap** — Public roadmap with community input on priorities
- **Inclusive Community** — Code of Conduct enforced, multilingual community channels
- **Sustainable** — Sponsorships and grants fund infrastructure, not profit

## Who This Is For

- **Schools** — Government and private schools seeking affordable AI tutoring
- **Teachers** — Reduce grading load, personalize practice, track mastery
- **Students** — Personalized tutor in their language, at their pace
- **Developers** — Build on a modern, well-architected AI education platform
- **Researchers** — Transparent, auditable AI tutoring for educational research
- **Translators** — Bring AI tutoring to every language community

## What We Are Not

- ❌ A SaaS product you rent
- ❌ A wrapper around GPT-4 with a markup
- ❌ A data-harvesting platform
- ❌ A closed-source "AI tutor" black box

---

*This document is a living document. Propose changes via GitHub Issues or Discussions.*
