# AshaShala — Operations Runbook

"If X breaks, do Y." Diagnosis starts at `GET /api/v1/health` — it reports each
dependency (`db`, `vector_db`, `r2`, `gemini`, `nvidia_llm`, `nvidia_ocr`) as
`ok` / `error`, so the failing subsystem is usually obvious in one request.

```bash
curl -s https://<backend-host>/api/v1/health | jq
```

---

## 1. Neon Postgres connectivity

**Symptoms:** `health.db = error`; requests 500/503 with `error_code: DATABASE_ERROR`;
logs show `OperationalError` / connection timeouts.

**Likely causes → fixes:**
- **Scale-to-zero cold start.** Neon free tier suspends the compute when idle; the
  first query after idle can take a few seconds and occasionally times out. Retry
  once; the second request wakes it. This is expected, not an incident.
- **CU-hours exhausted (100/month free).** Check the Neon dashboard usage. Fix:
  wait for the monthly reset, or upgrade the project.
- **Wrong `DATABASE_URL`.** Must be the pooled connection string with
  `?sslmode=require`. Verify the secret in Render/Northflank.
- **Too many connections.** We use `NullPool` + Neon's PgBouncer pooler, so this is
  rare; if it appears, confirm the pooled (not direct) host is in `DATABASE_URL`.

**Escalation:** Neon status page; if data is intact, no action beyond waking compute.

---

## 2. Qdrant Cloud 503 / unavailable

**Symptoms:** `health.vector_db = error`; chat returns answers with **no citations**
or "I don't see that in your materials"; ingestion marks documents `failed`.

**Fixes:**
- **Transient 503.** Qdrant free clusters occasionally restart. Retrieval failures
  are caught — the tutor degrades to "not in materials" rather than crashing. Wait
  and retry; re-run ingestion for any `failed` documents.
- **1 GB / ~1M-vector cap hit.** Check cluster storage. Fix: delete stale documents
  (`DELETE /teacher/materials/{id}` also removes their Qdrant points) or upgrade.
- **Wrong `QDRANT_URL`/`QDRANT_API_KEY`.** Verify secrets.

**Note:** Postgres `chunks` rows mirror every Qdrant point, so vectors can be
rebuilt by re-ingesting the source `Document`s — nothing is unrecoverable.

---

## 3. Gemini quota exhausted (429)

**Symptoms:** `health.gemini = error` or intermittent slow chats; `llm_usage` rows
with `status=error`; School Admin **LLM usage** card shows **"Over daily quota"**.

**Fixes:**
- **Automatic fallback already engaged.** The router falls through Gemini→NVIDIA on
  429, so English chat still works via NVIDIA. Expect higher latency.
- **Throttle the source.** `slowapi` caps chat at `CHAT_RATE_LIMIT` (default 30/min)
  and quiz at `QUIZ_RATE_LIMIT`. Lower these env vars if a single school is burning
  quota.
- **Reset window.** Gemini free-tier quotas reset daily — usually resolves on its own.
- Confirm `GEMINI_API_KEY` is valid (revoked keys look like quota errors).

---

## 4. Render cold start (15 s+)

**Symptoms:** first request after ~15 min idle hangs 30–50 s, then succeeds; SSE
chat appears to "stall" at the very start.

**This is the documented free-tier tradeoff, not a bug.**

**Mitigations:**
- **Keep-alive ping.** Hit `/api/v1/health` every ~10 min (UptimeRobot free, or a
  cron) to keep the instance warm during school hours.
- **Switch host.** Deploy `deploy/northflank.json` (always-on) if cold starts hurt
  the demo.
- Set the frontend to show a "waking up…" state on the first request after idle.

---

## 5. R2 upload failure

**Symptoms:** `health.r2 = error`; teacher file upload returns 502
`EXTERNAL_SERVICE_ERROR`; `Document.storage_url` is null.

**Fixes:**
- **Credentials/bucket.** Verify `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`,
  `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL`. The endpoint URL is
  derived from the account id — a wrong id looks like a network failure.
- **10 GB free cap.** Check R2 usage; delete old materials or upgrade.
- **URL/YouTube materials don't need R2** (no original file) — if only file uploads
  fail, it's isolated to R2 and those materials still ingest.

---

## Backup & Restore

### Postgres (Neon) — Point-in-Time Recovery
- Neon free tier retains a **PITR window** (~24 h to 7 days depending on plan).
  Restore via **Neon dashboard → Branches → Restore** to a timestamp, or create a
  branch from a past point and repoint `DATABASE_URL`.
- **Logical backup (portable):**
  ```bash
  pg_dump "$DATABASE_URL" -Fc -f ashashala-$(date +%F).dump   # timestamp your own filename
  pg_restore --clean --if-exists -d "$TARGET_DATABASE_URL" ashashala-YYYY-MM-DD.dump
  ```

### Qdrant — snapshot export/restore (test this once before launch)
```bash
# Create a snapshot of a school collection
curl -X POST "$QDRANT_URL/collections/school_<id>/snapshots" -H "api-key: $QDRANT_API_KEY"
# List / download
curl "$QDRANT_URL/collections/school_<id>/snapshots" -H "api-key: $QDRANT_API_KEY"
# Restore by uploading the snapshot file to the target cluster's recover endpoint.
```
Because `chunks` rows in Postgres mirror every point, the **authoritative recovery
path** is re-ingesting the source `Document`s — Qdrant is a rebuildable index, not
a system of record.

### R2 — originals
Uploaded files live in R2 under `school_{id}/class_{id}/…`. R2 has zero egress, so
periodically sync a copy with `rclone`/`aws s3 sync` if you need an off-site backup.

---

## Restore drill checklist (do once before touching real student data)
- [ ] Take a `pg_dump`, drop a scratch DB, `pg_restore`, confirm row counts match.
- [ ] Create a Qdrant snapshot, restore it to a scratch collection, confirm point count.
- [ ] Confirm a citation still opens its R2 file after a simulated restore.
