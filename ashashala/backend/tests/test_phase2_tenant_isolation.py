"""Tenant isolation — a query scoped to school B cannot see school A's rows.

The event listener filters SELECTs on TenantScoped models by the active
school_id, so a cross-tenant lookup yields no row → routes turn that into 404.
"""

import pytest
from sqlalchemy import select

from app.db.tenant_filter import tenant_context
from app.models.document import Document, DocStatus, SourceType
from tests.conftest import make_school


async def _make_doc(db, school_id: str) -> Document:
    from app.db.tenant_filter import tenant_bypass

    with tenant_bypass():
        doc = Document(school_id=school_id, class_id="c1", uploaded_by_teacher_id="t1",
                       filename="a.pdf", source_type=SourceType.pdf, status=DocStatus.indexed)
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
    return doc


@pytest.mark.asyncio
async def test_cross_tenant_document_is_invisible(db):
    school_a = await make_school(db, name="A")
    school_b = await make_school(db, name="B")
    doc = await _make_doc(db, school_a.id)

    # School A context sees its document.
    with tenant_context(school_a.id):
        db.expire_all()
        found = (await db.execute(select(Document).where(Document.id == doc.id))).scalar_one_or_none()
    assert found is not None

    # School B context sees nothing (would become a 404 in a route).
    with tenant_context(school_b.id):
        db.expire_all()
        hidden = (await db.execute(select(Document).where(Document.id == doc.id))).scalar_one_or_none()
    assert hidden is None


@pytest.mark.asyncio
async def test_super_admin_context_sees_all(db):
    school_a = await make_school(db, name="A")
    doc = await _make_doc(db, school_a.id)
    # No tenant context (super admin) => no filtering.
    with tenant_context(None):
        db.expire_all()
        found = (await db.execute(select(Document).where(Document.id == doc.id))).scalar_one_or_none()
    assert found is not None
