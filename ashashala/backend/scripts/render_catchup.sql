-- One-time catch-up for the Render production DB, which has only ever been
-- built by Base.metadata.create_all() (via scripts/seed.py) and has never
-- had Alembic run against it. create_all() creates missing TABLES but never
-- ALTERs existing ones, so this DB is very likely missing every column that
-- was added to a model after its table first existed on Render, while
-- already having every table that migrations 0001/0003/0004/0005 also
-- `op.create_table` (created earlier by create_all instead).
--
-- This script brings the schema in line with what all of
-- alembic/versions/20260710_0001 .. 20260713_0007 expect, using
-- idempotent IF NOT EXISTS / DO-block guards so it's safe to run more than
-- once and safe to run regardless of exactly which columns are already
-- present.
--
-- Run this ONCE against Render's Postgres (psql shell, or `psql
-- "$EXTERNAL_DATABASE_URL" -f render_catchup.sql`), then run
-- `alembic stamp head` (see README note below) so Alembic's bookkeeping
-- matches reality. After that, the Dockerfile's `alembic upgrade head` will
-- be a safe no-op on this catch-up and will only apply genuinely new
-- migrations going forward.

-- ---- from 20260710_0002 (notifications channel/dispatch, users.phone_number,
--      timetables.topic, enrollments/teacher_assignments.end_date) ----
DO $$ BEGIN
    CREATE TYPE notification_channel AS ENUM ('in_app', 'sms', 'whatsapp', 'email');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE notification_dispatch_status AS ENUM ('pending', 'sent', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE notifications ADD COLUMN IF NOT EXISTS channel notification_channel NOT NULL DEFAULT 'in_app';
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS dispatch_status notification_dispatch_status NOT NULL DEFAULT 'sent';
CREATE INDEX IF NOT EXISTS ix_notifications_dispatch_status ON notifications (dispatch_status);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS dispatched_at TIMESTAMPTZ;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS dispatch_error VARCHAR(512);

ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);

ALTER TABLE timetables ADD COLUMN IF NOT EXISTS topic VARCHAR(255);

ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS end_date DATE;
ALTER TABLE teacher_assignments ADD COLUMN IF NOT EXISTS end_date DATE;

-- ---- from 20260713_0006 (user_roles.user_id FK to users.id) ----
DO $$
DECLARE orphan_count INT;
BEGIN
    SELECT COUNT(*) INTO orphan_count FROM user_roles ur LEFT JOIN users u ON u.id = ur.user_id WHERE u.id IS NULL;
    IF orphan_count > 0 THEN
        RAISE EXCEPTION 'Cannot add FK: % orphaned user_roles row(s) reference a non-existent user — clean them up before retrying', orphan_count;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_user_roles_user_id_users') THEN
        ALTER TABLE user_roles ADD CONSTRAINT fk_user_roles_user_id_users FOREIGN KEY (user_id) REFERENCES users(id);
    END IF;
END $$;

-- ---- from 20260713_0007 (users.tokens_valid_after, documents.page_count) ----
ALTER TABLE users ADD COLUMN IF NOT EXISTS tokens_valid_after TIMESTAMPTZ;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS page_count INTEGER;
