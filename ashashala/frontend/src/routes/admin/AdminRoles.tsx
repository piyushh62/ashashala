import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { z } from "zod";
import { adminApi } from "../../api/endpoints";
import type { RoleTemplateOut } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Input, Skeleton } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { Modal, useConfirm } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";

const createSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
});
type CreateForm = z.infer<typeof createSchema>;

const VALIDATION_MESSAGE_KEYS: Record<string, string> = {
  "Name is required": "common.nameRequired",
};

export default function AdminRoles() {
  const { t } = useTranslation();
  const errMsg = (raw?: string) => (raw ? t(VALIDATION_MESSAGE_KEYS[raw] ?? raw) : undefined);
  const toast = useToast();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [editing, setEditing] = useState<RoleTemplateOut | null>(null);
  const [selectedPerms, setSelectedPerms] = useState<string[]>([]);

  const permissions = useQuery({ queryKey: ["admin", "permissions"], queryFn: () => adminApi.listPermissions() });
  const templates = useQuery({ queryKey: ["admin", "role-templates"], queryFn: () => adminApi.listRoleTemplates() });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin", "role-templates"] });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateForm>({ resolver: zodResolver(createSchema), defaultValues: { name: "", description: "" } });
  const [createPerms, setCreatePerms] = useState<string[]>([]);

  const create = useMutation({
    mutationFn: (values: CreateForm) =>
      adminApi.createRoleTemplate({ name: values.name, description: values.description || undefined, permissions: createPerms }),
    onSuccess: () => {
      toast.push(t("admin.roles.roleTemplateCreated"), "success");
      reset();
      setCreatePerms([]);
      invalidate();
    },
    onError: () => toast.push(t("admin.roles.createTemplateFailed"), "error"),
  });

  const openEdit = (t: RoleTemplateOut) => {
    setEditing(t);
    setSelectedPerms(t.permissions);
  };

  const update = useMutation({
    mutationFn: () => adminApi.updateRoleTemplate(editing!.id, { permissions: selectedPerms }),
    onSuccess: () => {
      toast.push(t("admin.roles.roleTemplateUpdated"), "success");
      setEditing(null);
      invalidate();
    },
    onError: () => toast.push(t("admin.roles.updateTemplateFailed"), "error"),
  });

  const del = useMutation({
    mutationFn: (id: string) => adminApi.deleteRoleTemplate(id),
    onSuccess: () => {
      toast.push(t("admin.roles.roleTemplateDeleted"), "success");
      invalidate();
    },
    onError: () => toast.push(t("admin.roles.deleteTemplateFailed"), "error"),
  });

  const togglePerm = (list: string[], setList: (v: string[]) => void, perm: string) => {
    setList(list.includes(perm) ? list.filter((p) => p !== perm) : [...list, perm]);
  };

  const perms = permissions.data ?? [];

  return (
    <div>
      <PageTitle subtitle={t("admin.roles.subtitle")}>{t("admin.roles.title")}</PageTitle>

      <Card className="mb-6">
        <CardHeader title={t("admin.roles.newRoleTemplate")} />
        <form className="p-5 space-y-4" onSubmit={handleSubmit((v) => create.mutateAsync(v))}>
          <div className="grid md:grid-cols-2 gap-3">
            <FormField label={t("admin.roles.name")} error={errMsg(errors.name?.message)}>
              <Input invalid={!!errors.name} {...register("name")} />
            </FormField>
            <FormField label={t("admin.roles.description")} optional>
              <Input {...register("description")} />
            </FormField>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{t("admin.roles.permissions")}</div>
            {permissions.isLoading ? (
              <Skeleton className="h-16" />
            ) : (
              <div className="flex flex-wrap gap-2">
                {perms.map((p) => {
                  const key = `${p.resource}:${p.action}`;
                  const active = createPerms.includes(key);
                  return (
                    <button
                      type="button"
                      key={p.id}
                      onClick={() => togglePerm(createPerms, setCreatePerms, key)}
                      className={`px-2.5 py-1 rounded-full text-xs font-medium ring-1 ring-inset transition ${
                        active
                          ? "bg-brand-600 text-white ring-brand-600"
                          : "bg-slate-50 text-slate-600 ring-slate-200 hover:bg-slate-100 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700"
                      }`}
                    >
                      {key}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? t("admin.roles.creating") : t("admin.roles.createTemplate")}
          </Button>
        </form>
      </Card>

      <Card>
        <CardHeader title={t("admin.roles.allRoleTemplates")} />
        <div className="p-2">
          {templates.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !templates.data?.length ? (
            <EmptyState title={t("admin.roles.noRoleTemplatesYet")} />
          ) : (
            <div className="divide-y divide-slate-50 dark:divide-slate-800">
              {templates.data.map((tpl) => (
                <div key={tpl.id} className="p-4 flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-700 dark:text-slate-200">{tpl.name}</span>
                      {tpl.is_system && <Badge tone="brand">{t("admin.roles.system")}</Badge>}
                    </div>
                    {tpl.description && <p className="text-sm text-slate-400 mt-0.5">{tpl.description}</p>}
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {tpl.permissions.map((p) => (
                        <Badge key={p}>{p}</Badge>
                      ))}
                    </div>
                  </div>
                  {!tpl.is_system && (
                    <div className="flex gap-2 shrink-0">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(tpl)}>
                        {t("admin.roles.edit")}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          confirm.ask({
                            title: t("admin.roles.deleteTemplateTitle"),
                            description: t("admin.roles.deleteTemplateDescription", { name: tpl.name }),
                            confirmLabel: t("admin.roles.delete"),
                            onConfirm: () => del.mutateAsync(tpl.id),
                          })
                        }
                      >
                        {t("admin.roles.delete")}
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      <Modal open={!!editing} onOpenChange={(open) => !open && setEditing(null)} title={t("admin.roles.editPermissions")} size="md">
        {editing && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {perms.map((p) => {
                const key = `${p.resource}:${p.action}`;
                const active = selectedPerms.includes(key);
                return (
                  <button
                    type="button"
                    key={p.id}
                    onClick={() => togglePerm(selectedPerms, setSelectedPerms, key)}
                    className={`px-2.5 py-1 rounded-full text-xs font-medium ring-1 ring-inset transition ${
                      active
                        ? "bg-brand-600 text-white ring-brand-600"
                        : "bg-slate-50 text-slate-600 ring-slate-200 hover:bg-slate-100 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700"
                    }`}
                  >
                    {key}
                  </button>
                );
              })}
            </div>
            <Button className="w-full" onClick={() => update.mutate()} disabled={update.isPending}>
              {update.isPending ? t("admin.roles.saving") : t("admin.roles.saveChanges")}
            </Button>
          </div>
        )}
      </Modal>
      {confirm.dialog}
    </div>
  );
}
