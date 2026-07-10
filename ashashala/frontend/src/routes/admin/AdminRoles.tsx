import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
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

export default function AdminRoles() {
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
      toast.push("Role template created.", "success");
      reset();
      setCreatePerms([]);
      invalidate();
    },
    onError: () => toast.push("Couldn't create role template (name may be taken).", "error"),
  });

  const openEdit = (t: RoleTemplateOut) => {
    setEditing(t);
    setSelectedPerms(t.permissions);
  };

  const update = useMutation({
    mutationFn: () => adminApi.updateRoleTemplate(editing!.id, { permissions: selectedPerms }),
    onSuccess: () => {
      toast.push("Role template updated.", "success");
      setEditing(null);
      invalidate();
    },
    onError: () => toast.push("Couldn't update role template.", "error"),
  });

  const del = useMutation({
    mutationFn: (id: string) => adminApi.deleteRoleTemplate(id),
    onSuccess: () => {
      toast.push("Role template deleted.", "success");
      invalidate();
    },
    onError: () => toast.push("Couldn't delete this template (it may be built-in or in use).", "error"),
  });

  const togglePerm = (list: string[], setList: (v: string[]) => void, perm: string) => {
    setList(list.includes(perm) ? list.filter((p) => p !== perm) : [...list, perm]);
  };

  const perms = permissions.data ?? [];

  return (
    <div>
      <PageTitle subtitle="Define the role templates every school's roles are cloned from.">Role Templates</PageTitle>

      <Card className="mb-6">
        <CardHeader title="New role template" />
        <form className="p-5 space-y-4" onSubmit={handleSubmit((v) => create.mutateAsync(v))}>
          <div className="grid md:grid-cols-2 gap-3">
            <FormField label="Name" error={errors.name?.message}>
              <Input invalid={!!errors.name} {...register("name")} />
            </FormField>
            <FormField label="Description" optional>
              <Input {...register("description")} />
            </FormField>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Permissions</div>
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
            {isSubmitting ? "Creating…" : "Create template"}
          </Button>
        </form>
      </Card>

      <Card>
        <CardHeader title="All role templates" />
        <div className="p-2">
          {templates.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !templates.data?.length ? (
            <EmptyState title="No role templates yet" />
          ) : (
            <div className="divide-y divide-slate-50 dark:divide-slate-800">
              {templates.data.map((t) => (
                <div key={t.id} className="p-4 flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-700 dark:text-slate-200">{t.name}</span>
                      {t.is_system && <Badge tone="brand">system</Badge>}
                    </div>
                    {t.description && <p className="text-sm text-slate-400 mt-0.5">{t.description}</p>}
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {t.permissions.map((p) => (
                        <Badge key={p}>{p}</Badge>
                      ))}
                    </div>
                  </div>
                  {!t.is_system && (
                    <div className="flex gap-2 shrink-0">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(t)}>
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          confirm.ask({
                            title: "Delete this role template?",
                            description: `${t.name} will be removed. Schools already using it are unaffected.`,
                            confirmLabel: "Delete",
                            onConfirm: () => del.mutateAsync(t.id),
                          })
                        }
                      >
                        Delete
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      <Modal open={!!editing} onOpenChange={(open) => !open && setEditing(null)} title="Edit permissions" size="md">
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
              {update.isPending ? "Saving…" : "Save changes"}
            </Button>
          </div>
        )}
      </Modal>
      {confirm.dialog}
    </div>
  );
}
