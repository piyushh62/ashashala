"""Baseline: the 22 tables that predate Alembic

This repo's first Alembic revision was 20260710_0001, which only ever added
NEW tables (dynamic RBAC + agent_actions) and explicitly documented that the
22 tables already in use at that point (users, schools, class_sections,
subjects, teacher_assignments, enrollments, parent_student_links,
audit_logs, documents, chunks, ocr_cache, flagged_answers, chat_sessions,
messages, quizzes, quiz_attempts, progress_records, llm_usage,
refresh_tokens, notifications, timetables, exam_timetables) had no baseline
migration of their own — they only ever existed because
Base.metadata.create_all() created them in scripts/seed.py.

That gap meant `alembic upgrade head` could never bootstrap a genuinely
empty database: every later revision's op.add_column()/op.create_index()
calls assume these tables already exist. This revision closes that gap by
creating them here, as the true root of the migration chain.

Columns that were added to these tables by LATER migrations (0002, 0006,
0007) are deliberately excluded here so those migrations' op.add_column()
calls don't collide with a column that already exists:
  - users: phone_number, tokens_valid_after (0002, 0007)
  - documents: page_count (0007)
  - notifications: channel, dispatch_status, dispatched_at, dispatch_error (0002)
  - timetables: topic (0002)
  - enrollments: end_date (0002)
  - teacher_assignments: end_date (0002)

For the Render database, which already has this exact schema (built via
create_all(), then caught up via scripts/render_catchup.sql), this revision
should never actually run — `alembic stamp head` (or stamping this specific
revision) is used instead so Alembic treats it as already applied. It exists
so any FUTURE fresh/empty database (a new dev environment, a new Render
instance, CI) can bootstrap the full schema from scratch via a plain
`alembic upgrade head`.

Revision ID: 20260709_0000
Revises:
Create Date: 2026-07-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260709_0000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum('super_admin', 'school_admin', 'teacher', 'student', 'parent', name='user_role'), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=True),
        sa.Column("interests", sa.String(512), nullable=True),
        sa.Column("grade", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_school_id", "users", ["school_id"])

    op.create_table(
        "schools",
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("features_json", sa.JSON(), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("academic_year_start", sa.Date(), nullable=True),
        sa.Column("academic_year_end", sa.Date(), nullable=True),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "class_sections",
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("grade_level", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_class_sections_school_id", "class_sections", ["school_id"])

    op.create_table(
        "subjects",
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_subjects_school_id", "subjects", ["school_id"])
    op.create_table(
        "teacher_assignments",
        sa.Column("teacher_id", sa.String(36), nullable=False),
        sa.Column("class_id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_teacher_assignments_teacher_id", "teacher_assignments", ["teacher_id"])
    op.create_index("ix_teacher_assignments_class_id", "teacher_assignments", ["class_id"])
    op.create_index("ix_teacher_assignments_subject_id", "teacher_assignments", ["subject_id"])
    op.create_index("ix_teacher_assignments_school_id", "teacher_assignments", ["school_id"])

    op.create_table(
        "enrollments",
        sa.Column("student_id", sa.String(36), nullable=False),
        sa.Column("class_id", sa.String(36), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_enrollments_class_id", "enrollments", ["class_id"])
    op.create_index("ix_enrollments_student_id", "enrollments", ["student_id"])
    op.create_index("ix_enrollments_school_id", "enrollments", ["school_id"])

    op.create_table(
        "parent_student_links",
        sa.Column("parent_id", sa.String(36), nullable=False),
        sa.Column("student_id", sa.String(36), nullable=False),
        sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_parent_student_links_school_id", "parent_student_links", ["school_id"])
    op.create_index("ix_parent_student_links_student_id", "parent_student_links", ["student_id"])
    op.create_index("ix_parent_student_links_parent_id", "parent_student_links", ["parent_id"])

    op.create_table(
        "audit_logs",
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.String(36), nullable=True),
        sa.Column("actor_role", sa.String(32), nullable=True),
        sa.Column("school_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=True),
        sa.Column("target_id", sa.String(320), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("payload_hash", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_school_id", "audit_logs", ["school_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_ts", "audit_logs", ["ts"])

    op.create_table(
        "documents",
        sa.Column("class_id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=True),
        sa.Column("uploaded_by_teacher_id", sa.String(36), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("storage_url", sa.String(1024), nullable=True),
        sa.Column("source_type", sa.Enum('pdf', 'docx', 'txt', 'url', 'youtube', 'image', name='source_type'), nullable=False),
        sa.Column("source_ref", sa.String(1024), nullable=True),
        sa.Column("status", sa.Enum('pending', 'indexed', 'failed', name='doc_status'), nullable=False),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_documents_school_id", "documents", ["school_id"])
    op.create_index("ix_documents_subject_id", "documents", ["subject_id"])
    op.create_index("ix_documents_class_id", "documents", ["class_id"])
    op.create_index("ix_documents_uploaded_by_teacher_id", "documents", ["uploaded_by_teacher_id"])

    op.create_table(
        "chunks",
        sa.Column("doc_id", sa.String(36), nullable=False),
        sa.Column("class_id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=True),
        sa.Column("page_or_ts", sa.String(64), nullable=True),
        sa.Column("lang", sa.String(8), nullable=False),
        sa.Column("qdrant_point_id", sa.String(36), nullable=False),
        sa.Column("vector_name", sa.String(32), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_chunks_doc_id", "chunks", ["doc_id"])
    op.create_index("ix_chunks_school_id", "chunks", ["school_id"])
    op.create_index("ix_chunks_subject_id", "chunks", ["subject_id"])
    op.create_index("ix_chunks_qdrant_point_id", "chunks", ["qdrant_point_id"])
    op.create_index("ix_chunks_class_id", "chunks", ["class_id"])

    op.create_table(
        "ocr_cache",
        sa.Column("doc_id", sa.String(36), primary_key=True),
        sa.Column("page", sa.Integer(), primary_key=True),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "flagged_answers",
        sa.Column("quiz_attempt_id", sa.String(36), nullable=False),
        sa.Column("quiz_id", sa.String(36), nullable=False),
        sa.Column("student_id", sa.String(36), nullable=False),
        sa.Column("class_id", sa.String(36), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("student_answer", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=True),
        sa.Column("ai_score", sa.Float(), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("flag_reason", sa.String(255), nullable=False),
        sa.Column("status", sa.Enum('open', 'resolved', name='flag_status'), nullable=False),
        sa.Column("override_score", sa.Float(), nullable=True),
        sa.Column("override_feedback", sa.Text(), nullable=True),
        sa.Column("resolved_by_teacher_id", sa.String(36), nullable=True),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_flagged_answers_quiz_attempt_id", "flagged_answers", ["quiz_attempt_id"])
    op.create_index("ix_flagged_answers_class_id", "flagged_answers", ["class_id"])
    op.create_index("ix_flagged_answers_quiz_id", "flagged_answers", ["quiz_id"])
    op.create_index("ix_flagged_answers_student_id", "flagged_answers", ["student_id"])
    op.create_index("ix_flagged_answers_school_id", "flagged_answers", ["school_id"])

    op.create_table(
        "chat_sessions",
        sa.Column("student_id", sa.String(36), nullable=False),
        sa.Column("class_id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=True),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_chat_sessions_student_id", "chat_sessions", ["student_id"])
    op.create_index("ix_chat_sessions_class_id", "chat_sessions", ["class_id"])
    op.create_index("ix_chat_sessions_school_id", "chat_sessions", ["school_id"])

    op.create_table(
        "messages",
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("role", sa.Enum('user', 'assistant', name='message_role'), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=True),
        sa.Column("model_role_used", sa.String(64), nullable=True),
        sa.Column("provider_used", sa.String(32), nullable=True),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])
    op.create_index("ix_messages_school_id", "messages", ["school_id"])

    op.create_table(
        "quizzes",
        sa.Column("class_id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=True),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("questions_json", sa.JSON(), nullable=False),
        sa.Column("created_by_teacher_id", sa.String(36), nullable=True),
        sa.Column("status", sa.Enum('draft', 'approved', name='quiz_status'), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_quizzes_class_id", "quizzes", ["class_id"])
    op.create_index("ix_quizzes_school_id", "quizzes", ["school_id"])

    op.create_table(
        "quiz_attempts",
        sa.Column("quiz_id", sa.String(36), nullable=False),
        sa.Column("student_id", sa.String(36), nullable=False),
        sa.Column("answers_json", sa.JSON(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("feedback_json", sa.JSON(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_quiz_attempts_quiz_id", "quiz_attempts", ["quiz_id"])
    op.create_index("ix_quiz_attempts_student_id", "quiz_attempts", ["student_id"])
    op.create_index("ix_quiz_attempts_school_id", "quiz_attempts", ["school_id"])

    op.create_table(
        "progress_records",
        sa.Column("student_id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=True),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("mastery_score", sa.Integer(), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_progress_records_school_id", "progress_records", ["school_id"])
    op.create_index("ix_progress_records_subject_id", "progress_records", ["subject_id"])
    op.create_index("ix_progress_records_student_id", "progress_records", ["student_id"])
    op.create_index("ix_progress_records_topic", "progress_records", ["topic"])

    op.create_table(
        "llm_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model_role", sa.String(64), nullable=False),
        sa.Column("model_id", sa.String(128), nullable=True),
        sa.Column("task", sa.String(64), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_llm_usage_ts", "llm_usage", ["ts"])
    op.create_index("ix_llm_usage_school_id", "llm_usage", ["school_id"])
    op.create_index("ix_llm_usage_task", "llm_usage", ["task"])
    op.create_index("ix_llm_usage_user_id", "llm_usage", ["user_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.String(36), sa.ForeignKey("refresh_tokens.id"), nullable=True),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    op.create_table(
        "notifications",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link", sa.String(255), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_notifications_school_id", "notifications", ["school_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    op.create_table(
        "timetables",
        sa.Column("teacher_id", sa.String(36), nullable=False),
        sa.Column("class_id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("period_number", sa.Integer(), nullable=False),
        sa.Column("room", sa.String(64), nullable=True),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_timetables_class_id", "timetables", ["class_id"])
    op.create_index("ix_timetables_teacher_id", "timetables", ["teacher_id"])
    op.create_index("ix_timetables_school_id", "timetables", ["school_id"])
    op.create_index("ix_timetables_subject_id", "timetables", ["subject_id"])

    op.create_table(
        "exam_timetables",
        sa.Column("class_id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("exam_name", sa.String(255), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("syllabus_ref", sa.String(512), nullable=True),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("school_id", sa.String(36), nullable=False),
    )
    op.create_index("ix_exam_timetables_subject_id", "exam_timetables", ["subject_id"])
    op.create_index("ix_exam_timetables_school_id", "exam_timetables", ["school_id"])
    op.create_index("ix_exam_timetables_class_id", "exam_timetables", ["class_id"])




def downgrade() -> None:
    op.drop_table("exam_timetables")
    op.drop_table("timetables")
    op.drop_table("notifications")
    op.drop_table("refresh_tokens")
    op.drop_table("llm_usage")
    op.drop_table("progress_records")
    op.drop_table("quiz_attempts")
    op.drop_table("quizzes")
    op.drop_table("messages")
    op.drop_table("chat_sessions")
    op.drop_table("flagged_answers")
    op.drop_table("ocr_cache")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("audit_logs")
    op.drop_table("parent_student_links")
    op.drop_table("enrollments")
    op.drop_table("teacher_assignments")
    op.drop_table("subjects")
    op.drop_table("class_sections")
    op.drop_table("schools")
    op.drop_table("users")
    sa.Enum(name="quiz_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="message_role").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="flag_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="doc_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="source_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
