"""Idempotent demo seed — one command to a full, logged-in-able demo.

Creates: 1 super admin (from .env), 1 school, 1 school admin, 2 teachers,
6 students (mixed grade + mastery), 2 parents each linked to one student, a
class + subject with assignments/enrollments, varied ProgressRecords, and two
sample materials (a YouTube link + a TXT note). Best-effort ingestion of the
materials runs if the vector/embedding services are reachable; otherwise the
Document rows are still created so the UI has content to show.

Run:  cd backend && python scripts/seed.py    (safe to run repeatedly)
"""

from __future__ import annotations

import asyncio
import pathlib
import sys

# Make `app` importable when run as a bare script.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.models  # noqa: F401,E402 — populate Base.metadata
from app.auth.password import hash_password  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import async_session_factory, engine  # noqa: E402
from app.db.tenant_filter import tenant_bypass  # noqa: E402
from app.models.document import Document, DocStatus, SourceType  # noqa: E402
from app.models.learning import ProgressRecord  # noqa: E402
from app.models.school import School  # noqa: E402
from app.models.structure import (  # noqa: E402
    ClassSection,
    Enrollment,
    ParentStudentLink,
    Subject,
    TeacherAssignment,
)
from app.models.user import User, UserRole  # noqa: E402

# Fixed demo passwords (printed at the end). Super admin uses the .env values.
PW_ADMIN = "demo-admin-1234"
PW_TEACHER = "demo-teacher-1234"
PW_STUDENT = "demo-student-1234"
PW_PARENT = "demo-parent-1234"

SCHOOL_NAME = "Demo Public School"
YT_URL = "https://www.youtube.com/watch?v=kn-lFZTknkk"  # Khan Academy: fractions


async def _get_or_create(session: AsyncSession, model, defaults: dict, **filters):
    """Return (obj, created). Look up by `filters`; create with defaults+filters."""
    obj = (await session.execute(select(model).filter_by(**filters))).scalars().first()
    if obj is not None:
        return obj, False
    obj = model(**{**filters, **defaults})
    session.add(obj)
    await session.flush()
    return obj, True


async def _ensure_user(session, *, name, email, role, password, school_id=None, grade=None, interests=None):
    user, created = await _get_or_create(
        session, User, {
            "name": name, "password_hash": hash_password(password), "role": role,
            "school_id": school_id, "grade": grade, "interests": interests,
        }, email=email,
    )
    return user


async def seed() -> dict:
    # Dev convenience: create tables if they don't exist (idempotent; prod uses Alembic).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Ensure new columns exist on existing tables for production/render deploys
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS tokens_valid_after TIMESTAMP WITH TIME ZONE"))
        except Exception as e:
            print(f"Migration warning: {e}", file=sys.stderr)

    async with async_session_factory() as s:
        with tenant_bypass():
            # Super admin (from .env).
            await _ensure_user(
                s, name="Super Admin", email=settings.SUPER_ADMIN_EMAIL,
                role=UserRole.super_admin, password=settings.SUPER_ADMIN_PASSWORD,
            )

            school, _ = await _get_or_create(s, School, {"address": "Ahmedabad, Gujarat"}, name=SCHOOL_NAME)

            admin = await _ensure_user(s, name="Asha Admin", email="admin@demo.ashashala",
                                       role=UserRole.school_admin, password=PW_ADMIN, school_id=school.id)
            t1 = await _ensure_user(s, name="Meera Teacher", email="teacher1@demo.ashashala",
                                    role=UserRole.teacher, password=PW_TEACHER, school_id=school.id)
            t2 = await _ensure_user(s, name="Raj Teacher", email="teacher2@demo.ashashala",
                                    role=UserRole.teacher, password=PW_TEACHER, school_id=school.id)

            grades = [6, 6, 7, 7, 8, 8]
            interests = ["cricket", "space", "cooking", "football", "music", "drawing"]
            students = []
            for i in range(6):
                st = await _ensure_user(
                    s, name=f"Student {i + 1}", email=f"student{i + 1}@demo.ashashala",
                    role=UserRole.student, password=PW_STUDENT, school_id=school.id,
                    grade=grades[i], interests=interests[i],
                )
                students.append(st)

            p1 = await _ensure_user(s, name="Parent One", email="parent1@demo.ashashala",
                                    role=UserRole.parent, password=PW_PARENT, school_id=school.id)
            p2 = await _ensure_user(s, name="Parent Two", email="parent2@demo.ashashala",
                                    role=UserRole.parent, password=PW_PARENT, school_id=school.id)

            cls, _ = await _get_or_create(s, ClassSection, {"grade_level": 6}, school_id=school.id, name="Grade 6 - A")
            subj, _ = await _get_or_create(s, Subject, {}, school_id=school.id, name="Mathematics")

            await _get_or_create(s, TeacherAssignment, {}, school_id=school.id,
                                 teacher_id=t1.id, class_id=cls.id, subject_id=subj.id)
            for st in students:
                await _get_or_create(s, Enrollment, {}, school_id=school.id, student_id=st.id, class_id=cls.id)

            # Two parents each linked to a different student (consent recorded).
            from app.models.mixins import utcnow
            await _get_or_create(s, ParentStudentLink, {"consent_given_at": utcnow()},
                                 school_id=school.id, parent_id=p1.id, student_id=students[0].id)
            await _get_or_create(s, ParentStudentLink, {"consent_given_at": utcnow()},
                                 school_id=school.id, parent_id=p2.id, student_id=students[1].id)

            # Varied mastery so dashboards look real.
            masteries = [20, 35, 50, 65, 80, 95]
            for st, m in zip(students, masteries):
                await _get_or_create(s, ProgressRecord, {"mastery_score": m},
                                     school_id=school.id, student_id=st.id, subject_id=subj.id, topic="Fractions")

            # Sample materials.
            yt, _ = await _get_or_create(
                s, Document, {
                    "subject_id": subj.id, "uploaded_by_teacher_id": t1.id,
                    "filename": "Fractions (Khan Academy)", "source_type": SourceType.youtube,
                    "source_ref": YT_URL, "status": DocStatus.pending,
                }, school_id=school.id, class_id=cls.id, filename="Fractions (Khan Academy)",
            )
            txt, _ = await _get_or_create(
                s, Document, {
                    "subject_id": subj.id, "uploaded_by_teacher_id": t1.id,
                    "filename": "fractions_notes.txt", "source_type": SourceType.txt,
                    "source_ref": "fractions_notes.txt", "status": DocStatus.pending,
                }, school_id=school.id, class_id=cls.id, filename="fractions_notes.txt",
            )

            await s.commit()
            ctx = {"school": school.id, "class": cls.id, "subject": subj.id,
                   "yt_doc": yt.id, "txt_doc": txt.id}

    # Best-effort ingestion of the TXT note (skipped cleanly if services are down).
    try:
        from app.services.ingestion.pipeline import ingest_document
        sample = b"A fraction represents a part of a whole. 1/2 means one of two equal parts. " * 20
        await ingest_document(doc_id=ctx["txt_doc"], school_id=ctx["school"], class_id=ctx["class"],
                              subject_id=ctx["subject"], source_type=SourceType.txt, data=sample)
        print("  ✓ ingested sample TXT note")
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ skipped ingestion (services unavailable): {e}")

    return ctx


def _print_credentials() -> None:
    rows = [
        ("Super Admin", settings.SUPER_ADMIN_EMAIL, "(from .env)"),
        ("School Admin", "admin@demo.ashashala", PW_ADMIN),
        ("Teacher", "teacher1@demo.ashashala", PW_TEACHER),
        ("Teacher", "teacher2@demo.ashashala", PW_TEACHER),
        ("Student", "student1@demo.ashashala", PW_STUDENT),
        ("Student (…2-6)", "student2..6@demo.ashashala", PW_STUDENT),
        ("Parent", "parent1@demo.ashashala", PW_PARENT),
        ("Parent", "parent2@demo.ashashala", PW_PARENT),
    ]
    print("\n" + "=" * 64)
    print("  AshaShala demo credentials")
    print("=" * 64)
    print(f"  {'Role':<16}{'Email':<32}{'Password'}")
    print("  " + "-" * 60)
    for role, email, pw in rows:
        print(f"  {role:<16}{email:<32}{pw}")
    print("=" * 64 + "\n")


async def main() -> None:
    print("Seeding demo data…")
    await seed()
    print("Done.")
    _print_credentials()


if __name__ == "__main__":
    asyncio.run(main())
