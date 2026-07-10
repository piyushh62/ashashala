"""Report routes: teacher can attach notes only while a report is a draft;
parents only ever see `sent` reports; the PDF export renders real PDF bytes;
cross-tenant/unlinked access is rejected."""

from datetime import UTC, date, datetime

import pytest

from app.db.tenant_filter import tenant_bypass
from app.models.report import Report, ReportStatus
from app.models.structure import ParentStudentLink
from app.models.user import UserRole
from tests.conftest import login, make_school, make_user


async def _seed_report(db, *, school, student, status=ReportStatus.draft):
    with tenant_bypass():
        report = Report(school_id=school.id, student_id=student.id, period_start=date(2026, 7, 1),
                        period_end=date(2026, 7, 8), narrative="Doing well.", status=status,
                        sent_at=datetime.now(UTC) if status == ReportStatus.sent else None)
        db.add(report)
        await db.commit()
        await db.refresh(report)
    return report


@pytest.mark.asyncio
async def test_teacher_patch_notes_only_while_draft(client, db):
    school = await make_school(db)
    teacher = await make_user(db, role=UserRole.teacher, school_id=school.id, email="pr1@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="prs1@x.test", grade=6)
    report = await _seed_report(db, school=school, student=student, status=ReportStatus.draft)
    headers = await login(client, "pr1@x.test")

    resp = await client.patch(f"/api/v1/teacher/reports/{report.id}", headers=headers,
                              json={"teacher_notes": "Doing great in class."})
    assert resp.status_code == 200, resp.text
    assert resp.json()["teacher_notes"] == "Doing great in class."

    sent_report = await _seed_report(db, school=school, student=student, status=ReportStatus.sent)
    resp2 = await client.patch(f"/api/v1/teacher/reports/{sent_report.id}", headers=headers,
                               json={"teacher_notes": "Too late."})
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_teacher_patch_report_cross_tenant_404(client, db):
    school_a = await make_school(db, name="A")
    school_b = await make_school(db, name="B")
    teacher = await make_user(db, role=UserRole.teacher, school_id=school_a.id, email="pr2@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school_b.id, email="prs2@x.test", grade=6)
    report = await _seed_report(db, school=school_b, student=student, status=ReportStatus.draft)
    headers = await login(client, "pr2@x.test")

    resp = await client.patch(f"/api/v1/teacher/reports/{report.id}", headers=headers,
                              json={"teacher_notes": "x"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_parent_only_sees_sent_reports(client, db):
    school = await make_school(db)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="pr3@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="prs3@x.test", grade=6)
    with tenant_bypass():
        db.add(ParentStudentLink(parent_id=parent.id, student_id=student.id, school_id=school.id))
        await db.commit()
    await _seed_report(db, school=school, student=student, status=ReportStatus.draft)
    sent = await _seed_report(db, school=school, student=student, status=ReportStatus.sent)
    headers = await login(client, "pr3@x.test")

    resp = await client.get(f"/api/v1/parent/children/{student.id}/reports", headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == sent.id


@pytest.mark.asyncio
async def test_parent_report_pdf_returns_pdf_bytes(client, db):
    school = await make_school(db)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="pr4@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="prs4@x.test", grade=6)
    with tenant_bypass():
        db.add(ParentStudentLink(parent_id=parent.id, student_id=student.id, school_id=school.id))
        await db.commit()
    sent = await _seed_report(db, school=school, student=student, status=ReportStatus.sent)
    headers = await login(client, "pr4@x.test")

    resp = await client.get(f"/api/v1/parent/children/{student.id}/reports/{sent.id}/pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_parent_report_pdf_unlinked_child_403(client, db):
    school = await make_school(db)
    parent = await make_user(db, role=UserRole.parent, school_id=school.id, email="pr5@x.test")
    student = await make_user(db, role=UserRole.student, school_id=school.id, email="prs5@x.test", grade=6)
    sent = await _seed_report(db, school=school, student=student, status=ReportStatus.sent)
    headers = await login(client, "pr5@x.test")

    resp = await client.get(f"/api/v1/parent/children/{student.id}/reports/{sent.id}/pdf", headers=headers)
    assert resp.status_code == 403
