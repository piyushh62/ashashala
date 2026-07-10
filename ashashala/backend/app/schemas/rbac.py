"""RBAC schemas: permissions, role templates, per-school roles, creation rights."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PermissionOut(BaseModel):
    id: str
    resource: str
    action: str

    model_config = {"from_attributes": True}


class RoleTemplateOut(BaseModel):
    id: str
    name: str
    is_system: bool
    description: str | None
    permissions: list[str] = []


class RoleTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class RoleTemplateUpdate(BaseModel):
    description: str | None = None
    permissions: list[str] | None = None


class RoleOut(BaseModel):
    id: str
    name: str
    is_custom: bool
    template_id: str | None
    permissions: list[str] = []


class RoleCreate(BaseModel):
    name: str
    permissions: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = None
    permissions: list[str] | None = None


class CreationRightsOut(BaseModel):
    role_id: str
    creatable_template_names: list[str] = []


class CreationRightsUpdate(BaseModel):
    creatable_template_names: list[str]
