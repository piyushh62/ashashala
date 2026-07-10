"""Dynamic RBAC resolution + auto-provisioning.

There is no production data yet (5-10 pilot users), so instead of a one-off
backfill script this lazily provisions on first use:

- `ensure_catalog_seeded` creates the permission catalog + 5 system role
  templates the first time anything needs them (belt-and-braces alongside the
  Alembic migration's `op.bulk_insert` — tests build schema via
  `Base.metadata.create_all`, which never runs the migration, so this is the
  only seeding path that fires there).
- `ensure_school_roles` clones a school's 4 concrete `Role` rows from the
  system templates (+ default `RoleCreationRight`s) the first time any of its
  users needs one — covers schools created before this migration too.
- `ensure_user_role_assignment` gives a user their `user_roles` row the first
  time their permissions are resolved (called from `build_token_claims` on
  every login/refresh, see app/deps.py).

None of the RBAC tables are `TenantScoped` (`Role.school_id` is a plain
column, not the mixin) — the automatic tenant filter in
`app/db/tenant_filter.py` never touches them, so no `tenant_bypass()` is
needed here.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    DEFAULT_CREATION_RIGHTS,
    SCHOOL_TEMPLATE_NAMES,
    SYSTEM_TEMPLATES,
    TEMPLATE_NAME_BY_USER_ROLE,
)
from app.models.agent_action import AgentAction
from app.models.rbac import (
    Permission,
    Role,
    RoleCreationRight,
    RolePermission,
    RoleTemplate,
    TemplatePermission,
    UserRoleAssignment,
)
from app.models.user import User, UserRole


async def ensure_catalog_seeded(db: AsyncSession) -> None:
    """Idempotently create any missing system `RoleTemplate`s + `Permission`s."""
    existing_template_names = set(
        (await db.execute(select(RoleTemplate.name))).scalars().all()
    )
    missing = {
        name: spec for name, spec in SYSTEM_TEMPLATES.items() if name not in existing_template_names
    }
    if not missing:
        return

    perm_rows = (await db.execute(select(Permission))).scalars().all()
    perm_by_str = {f"{p.resource}:{p.action}": p for p in perm_rows}
    needed = {perm for spec in missing.values() for perm in spec["permissions"]}
    for perm_str in needed - perm_by_str.keys():
        resource, action = perm_str.split(":", 1)
        perm = Permission(resource=resource, action=action)
        db.add(perm)
        perm_by_str[perm_str] = perm
    await db.flush()

    for name, spec in missing.items():
        template = RoleTemplate(name=name, is_system=True, description=spec["description"])
        db.add(template)
        await db.flush()
        for perm_str in spec["permissions"]:
            db.add(TemplatePermission(template_id=template.id, permission_id=perm_by_str[perm_str].id))
    await db.flush()


async def ensure_school_roles(db: AsyncSession, school_id: str) -> dict[str, Role]:
    """Ensure the 4 school-scoped `Role` rows (+ default creation rights)
    exist for `school_id`, cloned from the system templates. Returns
    template name -> Role. Safe to call repeatedly (no-op after first call)."""
    await ensure_catalog_seeded(db)

    templates = {
        t.name: t for t in (await db.execute(
            select(RoleTemplate).where(RoleTemplate.name.in_(SCHOOL_TEMPLATE_NAMES))
        )).scalars().all()
    }
    existing = (await db.execute(
        select(Role).where(
            Role.school_id == school_id,
            Role.template_id.in_([t.id for t in templates.values()]),
        )
    )).scalars().all()
    existing_by_template_id = {r.template_id: r for r in existing}

    by_template_name: dict[str, Role] = {}
    newly_created: list[tuple[str, Role, RoleTemplate]] = []
    for name in SCHOOL_TEMPLATE_NAMES:
        template = templates[name]
        role = existing_by_template_id.get(template.id)
        if role is None:
            role = Role(school_id=school_id, name=name, template_id=template.id, is_custom=False)
            db.add(role)
            newly_created.append((name, role, template))
        by_template_name[name] = role
    await db.flush()

    for name, role, template in newly_created:
        permission_ids = (await db.execute(
            select(TemplatePermission.permission_id).where(TemplatePermission.template_id == template.id)
        )).scalars().all()
        for permission_id in permission_ids:
            db.add(RolePermission(role_id=role.id, permission_id=permission_id))

        for creatable_name in DEFAULT_CREATION_RIGHTS.get(name, set()):
            creatable_template = templates.get(creatable_name)
            if creatable_template is not None:
                db.add(RoleCreationRight(
                    creator_role_id=role.id, creatable_template_id=creatable_template.id,
                ))
    await db.flush()
    return by_template_name


async def ensure_platform_role(db: AsyncSession) -> Role:
    """Ensure the singleton platform-level (`school_id=None`) Super Admin role."""
    await ensure_catalog_seeded(db)
    template = (await db.execute(
        select(RoleTemplate).where(RoleTemplate.name == "Super Admin")
    )).scalar_one()
    role = (await db.execute(
        select(Role).where(Role.school_id.is_(None), Role.template_id == template.id)
    )).scalar_one_or_none()
    if role is None:
        role = Role(school_id=None, name="Super Admin", template_id=template.id, is_custom=False)
        db.add(role)
        await db.flush()
        permission_ids = (await db.execute(
            select(TemplatePermission.permission_id).where(TemplatePermission.template_id == template.id)
        )).scalars().all()
        for permission_id in permission_ids:
            db.add(RolePermission(role_id=role.id, permission_id=permission_id))
        await db.flush()
    return role


async def ensure_user_role_assignment(db: AsyncSession, user: User) -> None:
    """No-op if `user` already has a `user_roles` row; otherwise assigns the
    Role matching their `UserRole` (creating school roles lazily if needed)."""
    existing = (await db.execute(
        select(UserRoleAssignment).where(UserRoleAssignment.user_id == user.id)
    )).scalars().first()
    if existing is not None:
        return

    if user.role == UserRole.super_admin:
        role = await ensure_platform_role(db)
        school_id = None
    else:
        if user.school_id is None:
            return
        roles_by_template = await ensure_school_roles(db, user.school_id)
        role = roles_by_template[TEMPLATE_NAME_BY_USER_ROLE[user.role]]
        school_id = user.school_id

    db.add(UserRoleAssignment(user_id=user.id, role_id=role.id, school_id=school_id))
    await db.flush()


async def resolve_permissions(db: AsyncSession, user: User) -> set[str]:
    """The full set of `"resource:action"` strings `user` holds, across every
    role assigned to them. Auto-provisions the assignment on first call."""
    await ensure_user_role_assignment(db, user)

    role_ids = (await db.execute(
        select(UserRoleAssignment.role_id).where(UserRoleAssignment.user_id == user.id)
    )).scalars().all()
    if not role_ids:
        return set()

    permission_ids = (await db.execute(
        select(RolePermission.permission_id).where(RolePermission.role_id.in_(role_ids))
    )).scalars().all()
    if not permission_ids:
        return set()

    perms = (await db.execute(
        select(Permission).where(Permission.id.in_(permission_ids))
    )).scalars().all()
    return {f"{p.resource}:{p.action}" for p in perms}


async def get_user_role_row(db: AsyncSession, user: User) -> Role | None:
    """The concrete `Role` row backing `user`'s primary `UserRole` (their
    school's cloned role, or the platform role for super_admin)."""
    await ensure_user_role_assignment(db, user)
    assignment = (await db.execute(
        select(UserRoleAssignment).where(UserRoleAssignment.user_id == user.id)
    )).scalars().first()
    if assignment is None:
        return None
    return await db.get(Role, assignment.role_id)


async def can_create_role(db: AsyncSession, creator: User, target_role: UserRole) -> bool:
    """Whether `creator`'s role has been granted the right to create users
    with `target_role`, per that school's `RoleCreationRight` rows."""
    creator_role = await get_user_role_row(db, creator)
    if creator_role is None:
        return False

    target_template = (await db.execute(
        select(RoleTemplate).where(RoleTemplate.name == TEMPLATE_NAME_BY_USER_ROLE[target_role])
    )).scalar_one_or_none()
    if target_template is None:
        return False

    right = (await db.execute(
        select(RoleCreationRight).where(
            RoleCreationRight.creator_role_id == creator_role.id,
            RoleCreationRight.creatable_template_id == target_template.id,
        )
    )).scalar_one_or_none()
    return right is not None


async def propose_agent_action(
    db: AsyncSession,
    *,
    school_id: str,
    agent_name: str,
    action_type: str,
    payload: dict,
    confidence: float | None = None,
) -> AgentAction:
    """Queue a proactive agent proposal for human approval. No producer wires
    into this yet (agents land in Phase 3+) — this is the entry point they'll
    call, mirroring how `FlaggedAnswer` rows are created in quiz_submit."""
    action = AgentAction(
        school_id=school_id, agent_name=agent_name, action_type=action_type,
        payload_json=payload, confidence=confidence,
    )
    db.add(action)
    await db.flush()
    return action
