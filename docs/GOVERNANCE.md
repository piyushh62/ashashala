# Governance

## Project Name: AshaShala

AshaShala is governed as a community-led open source project. This document explains how decisions are made, who maintains the repository, and how contributors can participate in governance.

---

## Governance Model

We follow a **benevolent dictator for now (BDFN)** model transitioning to a **community governance model** as the project matures.

### Current Phase: BDFN (Bootstrap)
- **Project Founder(s)** act as benevolent dictators for initial architecture and direction
- All major decisions documented publicly via RFCs
- Active recruitment of maintainers from early contributors

### Target Phase: Community Governance (Post v1.0)
- **Steering Committee** of 5-9 maintainers elected by contributors
- **Working Groups** for key areas (Core, Agents, RAG, i18n, Community, Infra)
- **RFC Process** for all major changes
- **Term Limits** for steering committee members (2 years, renewable once)

---

## Roles and Responsibilities

### Core Maintainers
- Approve PRs, merge releases, manage issues
- Set technical direction within community consensus
- Protect repository branch rules and CI/CD
- **Current**: Project founders + active contributors with 10+ merged PRs

### Contributors
- Anyone who submits issues, code, docs, translations, or tests
- Eligible for maintainer nomination after sustained contribution

### Community Stewards
- Active contributors trusted to review and triage issues
- Welcome new contributors, manage discussions
- Organize community calls, hackathons, translation sprints

### Working Group Leads
- **Core Platform** — FastAPI, Postgres, Auth, Tenancy
- **Agent Orchestration** — LangGraph, Prompting, Model Router
- **RAG & Ingestion** — Qdrant, Embeddings, Chunking, Citations
- **Internationalization (i18n)** — Translations, RTL, Voice
- **Community & Docs** — Onboarding, Tutorials, Events
- **Infrastructure** — CI/CD, Deploy, Monitoring, Security

---

## Decision Making Process

### 1. Small Changes (Bug fixes, docs, minor features)
- Standard PR review by any maintainer
- 1 approval required
- Merge after CI passes

### 2. Medium Changes (New features, API changes, refactors)
- Open GitHub Issue for discussion first
- Design doc or RFC encouraged for architectural changes
- 2 maintainer approvals required
- 48-hour review window for community input

### 3. Major Changes (Architecture, governance, breaking changes, new dependencies)
- **Required**: RFC (Request for Comments) in `docs/rfcs/`
- RFC template: Problem, Proposal, Alternatives, Migration Plan, Security/Privacy Impact
- 7-day comment period minimum
- Steering committee decision (or maintainer consensus pre-steering-committee)
- Documented in `docs/DECISIONS.md`

### 4. Emergency Fixes (Security, data loss, critical regression)
- Fast-track PR with 1 maintainer approval
- Post-incident review within 7 days
- Document in `docs/INCIDENTS.md`

---

## Contribution Review Workflow

```
1. Issue Created → Triage (label: good first issue, help wanted, area:*)
2. Contributor Claims Issue → Branch: feat/fix/docs/chore/<issue-number>-<slug>
3. PR Opened → CI Runs (lint, typecheck, test, build)
4. Review → Maintainer/Steward reviews (code quality, tests, docs, breaking changes)
5. Approval → 1-2 approvals based on change size
6. Merge → Squash merge, delete branch
6. Release → Automated on tag push (semantic versioning)
```

### Review Standards
- **Code Quality**: Type hints, docstrings, error handling, logging
- **Tests**: Unit tests for new logic, integration tests for API changes
- **Docs**: Update relevant docs, add examples for new features
- **Security**: No secrets, input validation, auth checks
- **Performance**: No N+1 queries, reasonable latency budgets
- **Accessibility**: i18n keys for all user-facing strings, ARIA for UI

---

## Release Process

### Versioning
- **Semantic Versioning**: `vMAJOR.MINOR.PATCH`
- **Pre-releases**: `vX.Y.Z-alpha.N`, `vX.Y.Z-beta.N`, `vX.Y.Z-rc.N`

### Release Cadence
- **Patch**: As needed (bug fixes, security)
- **Minor**: Monthly (features, improvements)
- **Major**: Yearly or for breaking changes

### Release Checklist
1. Update `CHANGELOG.md` with highlights
2. Create release branch `release/vX.Y`
3. Run full test suite + integration tests
4. Tag release `vX.Y.Z`
5. GitHub Release with notes
6. Deploy to staging → production
7. Announce in Discord, GitHub Discussions, Twitter

---

## Code of Conduct

This project follows the **Contributor Covenant Code of Conduct v2.1**.

- **Enforcement**: Code of Conduct Committee (3 maintainers, rotating)
- **Reporting**: `conduct@ashashala.org` (private, encrypted)
- **Transparency**: Annual transparency report (anonymized)

See `CODE_OF_CONDUCT.md` for full text.

---

## Escalation Path

1. **PR Review Disagreement** → Request second maintainer opinion
2. **Technical Dispute** → Open RFC, 7-day discussion, steering committee decides
3. **Conduct Violation** → Code of Conduct Committee investigates, recommends action
4. **Governance Dispute** → Steering committee vote (simple majority, quorum 3)
5. **Project Direction** → Community vote (all contributors with 5+ merged PRs)

---

## Community Channels

| Channel | Purpose | Link |
|---------|---------|------|
| GitHub Issues | Bugs, features, tasks | `github.com/ashashala/ashashala/issues` |
| GitHub Discussions | RFCs, Q&A, announcements | `github.com/ashashala/ashashala/discussions` |
| Discord | Real-time chat, help, social | `discord.gg/ashashala` |
| Community Call | Monthly sync, demos, planning | `cal.com/ashashala/community` |
| Twitter/X | Announcements, highlights | `@ashashala_ai` |
| Blog | Deep dives, tutorials, case studies | `blog.ashashala.org` |

---

## Transparency Commitments

- All maintainer meetings: notes published in `docs/meeting-notes/`
- Financial transparency: Annual report (sponsorships, infrastructure costs)
- Security incidents: Public post-mortem within 30 days (no sensitive data)
- Roadmap updates: Quarterly public review

---

## Amending This Document

Changes to governance require:
1. RFC with 14-day comment period
2. Steering committee approval (or maintainer consensus pre-committee)
3. Announcement in all community channels

---

*This governance model is inspired by Kubernetes, Rust, and Node.js governance. It will evolve as the community grows.*
