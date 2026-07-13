import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { z } from "zod";
import { schoolApi } from "../../api/endpoints";
import type { RoleOut } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Input, Skeleton } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { Modal, useConfirm } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";

const createSchema = z.object({ name: z.string().min(1) });
type CreateForm = z.infer<typeof createSchema>;

function Pills({
  options,
  selected,
  onToggle,
}: {
  options: string[];
  selected: string[];
  onToggle: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((o) => {
        const active = selected.includes(o);
        return (
          <button
            type="button"
            key={o}
            onClick={() => onToggle(o)}
            className={`px-2.5 py-1 rounded-full text-xs font-medium ring-1 ring-inset transition ${
              active
                ? "bg-brand-600 text-white ring-brand-600"
                : "bg-slate-50 text-slate-600 ring-slate-200 hover:bg-slate-100 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700"
            }`}
          >
            {o}
          </button>
        );
      })}
    </div>
  );
}

export default function SchoolRoles() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [editing, setEditing] = useState<RoleOut | null>(null);
  const [editPerms, setEditPerms] = useState<string[]>([]);
  const [rightsFor, setRightsFor] = useState<RoleOut | null>(null);
  const [rightsSelected, setRightsSelected] = useState<string[]>([]);
  const [createPerms, setCreatePerms] = useState<string[]>([]);

  const permissions = useQuery({ queryKey: ["school", "permissions"], queryFn: () => schoolApi.listPermissions() });
  const templates = useQuery({ queryKey: ["school", "role-templates"], queryFn: () => schoolApi.listRoleTemplates() });
  const roles = useQuery({ queryKey: ["school", "roles"], queryFn: () => schoolApi.listRoles() });

  const invalidateRoles = () => qc.invalidateQueries({ queryKey: ["school", "roles"] });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateForm>({ resolver: zodResolver(createSchema), defaultValues: { name: "" } });

  const create = useMutation({
    mutationFn: (values: CreateForm) => schoolApi.createRole({ name: values.name, permissions: createPerms }),
    onSuccess: () => {
      toast.push(t("school.roles.roleCreated"), "success");
      reset();
      setCreatePerms([]);
      invalidateRoles();
    },
    onError: () => toast.push(t("school.roles.createRoleFailed"), "error"),
  });

  const openEdit = (r: RoleOut) => {
    setEditing(r);
    setEditPerms(r.permissions);
  };
  const update = useMutation({
    mutationFn: () => schoolApi.updateRole(editing!.id, { permissions: editPerms }),
    onSuccess: () => {
      toast.push(t("school.roles.roleUpdated"), "success");
      setEditing(null);
      invalidateRoles();
    },
    onError: () => toast.push(t("school.roles.updateRoleFailed"), "error"),
  });

  const del = useMutation({
    mutationFn: (id: string) => schoolApi.deleteRole(id),
    onSuccess: () => {
      toast.push(t("school.roles.roleDeleted"), "success");
      invalidateRoles();
    },
    onError: () => toast.push(t("school.roles.deleteRoleFailed"), "error"),
  });

  const openRights = async (r: RoleOut) => {
    setRightsFor(r);
    const res = await schoolApi.getCreationRights(r.id);
    setRightsSelected(res.creatable_template_names);
  };
  const saveRights = useMutation({
    mutationFn: () => schoolApi.setCreationRights(rightsFor!.id, rightsSelected),
    onSuccess: () => {
      toast.push(t("school.roles.creationRightsUpdated"), "success");
      setRightsFor(null);
    },
    onError: () => toast.push(t("school.roles.creationRightsUpdateFailed"), "error"),
  });

  const toggle = (list: string[], setList: (v: string[]) => void, v: string) =>
    setList(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  const perms = (permissions.data ?? []).map((p) => `${p.resource}:${p.action}`);
  const templateNames = (templates.data ?? []).map((tpl) => tpl.name);

  return (
    <div>
      <PageTitle subtitle={t("school.roles.subtitle")}>{t("school.roles.title")}</PageTitle>

      <Card className="mb-6">
        <CardHeader title={t("school.roles.newCustomRole")} />
        <form className="p-5 space-y-4" onSubmit={handleSubmit((v) => create.mutateAsync(v))}>
          <FormField label={t("school.roles.name")} error={errors.name ? t("common.nameRequired") : undefined}>
            <Input invalid={!!errors.name} {...register("name")} className="max-w-sm" />
          </FormField>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{t("school.roles.permissions")}</div>
            {permissions.isLoading ? <Skeleton className="h-16" /> : <Pills options={perms} selected={createPerms} onToggle={(v) => toggle(createPerms, setCreatePerms, v)} />}
          </div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? t("school.roles.creating") : t("school.roles.createRole")}
          </Button>
        </form>
      </Card>

      <Card>
        <CardHeader title={t("school.roles.allRoles")} subtitle={t("school.roles.allRolesSubtitle")} />
        <div className="p-2">
          {roles.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !roles.data?.length ? (
            <EmptyState title={t("school.roles.noRoles")} />
          ) : (
            <div className="divide-y divide-slate-50 dark:divide-slate-800">
              {roles.data.map((r) => (
                <div key={r.id} className="p-4 flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-700 dark:text-slate-200">{r.name}</span>
                      {!r.is_custom && <Badge tone="brand">{t("school.roles.builtIn")}</Badge>}
                    </div>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {r.permissions.map((p) => (
                        <Badge key={p}>{p}</Badge>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <Button variant="ghost" size="sm" onClick={() => openRights(r)}>
                      {t("school.roles.creationRights")}
                    </Button>
                    {r.is_custom && (
                      <>
                        <Button variant="ghost" size="sm" onClick={() => openEdit(r)}>
                          {t("school.roles.edit")}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            confirm.ask({
                              title: t("school.roles.deleteRoleTitle"),
                              description: t("school.roles.deleteRoleDesc", { name: r.name }),
                              confirmLabel: t("school.roles.delete"),
                              onConfirm: () => del.mutateAsync(r.id),
                            })
                          }
                        >
                          {t("school.roles.delete")}
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      <Modal open={!!editing} onOpenChange={(open) => !open && setEditing(null)} title={t("school.roles.editPermissions")} size="md">
        {editing && (
          <div className="space-y-4">
            <Pills options={perms} selected={editPerms} onToggle={(v) => toggle(editPerms, setEditPerms, v)} />
            <Button className="w-full" onClick={() => update.mutate()} disabled={update.isPending}>
              {update.isPending ? t("school.roles.saving") : t("school.roles.saveChanges")}
            </Button>
          </div>
        )}
      </Modal>

      <Modal
        open={!!rightsFor}
        onOpenChange={(open) => !open && setRightsFor(null)}
        title={t("school.roles.creationRights")}
        description={rightsFor ? t("school.roles.creationRightsQuestion", { name: rightsFor.name }) : undefined}
        size="sm"
      >
        {rightsFor && (
          <div className="space-y-4">
            <Pills options={templateNames} selected={rightsSelected} onToggle={(v) => toggle(rightsSelected, setRightsSelected, v)} />
            <Button className="w-full" onClick={() => saveRights.mutate()} disabled={saveRights.isPending}>
              {saveRights.isPending ? t("school.roles.saving") : t("school.roles.save")}
            </Button>
          </div>
        )}
      </Modal>
      {confirm.dialog}
    </div>
  );
}
