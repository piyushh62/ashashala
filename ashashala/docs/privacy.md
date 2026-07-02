# AshaShala — Privacy & Data Policy (one page)

AshaShala is a school-owned tutoring platform. Schools are the data controllers;
AshaShala (the software) is the processor. This page summarises retention,
deletion, and export.

## What we store
- **Accounts**: name, email, hashed password (bcrypt — never plaintext), role,
  school, and for students: grade + optional interests.
- **Learning data**: chat messages, quiz attempts, mastery scores.
- **Materials**: teacher-uploaded files (in Cloudflare R2) and their text chunks
  (in Postgres + Qdrant), scoped to a single class within a single school.
- **Operational**: audit logs (who did what, when) and LLM usage counters. Chat
  content in audit logs is stored only as a hash, never in the clear.

## Tenant isolation
Every record carries a `school_id` and is filtered automatically on every query.
Cross-school access returns **404** (we never confirm a resource exists to a
tenant that shouldn't see it). Parents see only children they are explicitly
linked to, with consent recorded at link time.

## Consent
Parent–student links capture `consent_given_at`. Schools are responsible for
obtaining guardian consent for students under the applicable age.

## Export (data portability)
A student can export their own data as JSON via
`GET /api/v1/student/data-export` (messages, quiz attempts, mastery).

## Deletion (right to erasure)
A super admin can erase a user via `DELETE /api/v1/admin/users/{id}/data`, which
removes the user's rows, their document vectors from Qdrant, and their original
files from R2. The action is recorded in the audit log with a reason.

## Retention
Learning and audit data are retained for the school's academic record needs and
deleted on request per the school's policy. Backups follow Neon's
point-in-time-recovery window (see `docs/runbook.md`).

## Contact
Privacy questions: the operating school's data protection contact, or the
platform maintainers at `security@ashashala.org`.
