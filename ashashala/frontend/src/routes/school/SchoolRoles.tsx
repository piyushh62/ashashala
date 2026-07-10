import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { schoolApi } from "../../api/endpoints";
import type { RoleOut } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Input, Skeleton } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { Modal, useConfirm } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";

const createSchema = z.object({ name: z.string().min(1, "Name is required") });
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
      toast.push("Role created.", "success");
      reset();
      setCreatePerms([]);
      invalidateRoles();
    },
    onError: () => toast.push("Couldn't create role (name may be taken).", "error"),
  });

  const openEdit = (r: RoleOut) => {
    setEditing(r);
    setEditPerms(r.permissions);
  };
  const update = useMutation({
    mutationFn: () => schoolApi.updateRole(editing!.id, { permissions: editPerms }),
    onSuccess: () => {
      toast.push("Role updated.", "success");
      setEditing(null);
      invalidateRoles();
    },
    onError: () => toast.push("Couldn't update role.", "error"),
  });

  const del = useMutation({
    mutationFn: (id: string) => schoolApi.deleteRole(id),
    onSuccess: () => {
      toast.push("Role deleted.", "success");
      invalidateRoles();
    },
    onError: () => toast.push("Couldn't delete this role (it may be built-in or still assigned to users).", "error"),
  });

  const openRights = async (r: RoleOut) => {
    setRightsFor(r);
    const res = await schoolApi.getCreationRights(r.id);
    setRightsSelected(res.creatable_template_names);
  };
  const saveRights = useMutation({
    mutationFn: () => schoolApi.setCreationRights(rightsFor!.id, rightsSelected),
    onSuccess: () => {
      toast.push("Creation rights updated.", "success");
      setRightsFor(null);
    },
    onError: () => toast.push("Couldn't update creation rights.", "error"),
  });

  const toggle = (list: string[], setList: (v: string[]) => void, v: string) =>
    setList(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  const perms = (permissions.data ?? []).map((p) => `${p.resource}:${p.action}`);
  const templateNames = (templates.data ?? []).map((t) => t.name);

  return (
    <div>
      <PageTitle subtitle="Custom roles and who can create teachers, students, and parents.">Roles</PageTitle>

      <Card className="mb-6">
        <CardHeader title="New custom role" />
        <form className="p-5 space-y-4" onSubmit={handleSubmit((v) => create.mutateAsync(v))}>
          <FormField label="Name" error={errors.name?.message}>
            <Input invalid={!!errors.name} {...register("name")} className="max-w-sm" />
          </FormField>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Permissions</div>
            {permissions.isLoading ? <Skeleton className="h-16" /> : <Pills options={perms} selected={createPerms} onToggle={(v) => toggle(createPerms, setCreatePerms, v)} />}
          </div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating…" : "Create role"}
          </Button>
        </form>
      </Card>

      <Card>
        <CardHeader title="All roles" subtitle="Toggle which roles can create teachers, students, or parents." />
        <div className="p-2">
          {roles.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !roles.data?.length ? (
            <EmptyState title="No roles yet" />
          ) : (
            <div className="divide-y divide-slate-50 dark:divide-slate-800">
              {roles.data.map((r) => (
                <div key={r.id} className="p-4 flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-700 dark:text-slate-200">{r.name}</span>
                      {!r.is_custom && <Badge tone="brand">built-in</Badge>}
                    </div>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {r.permissions.map((p) => (
                        <Badge key={p}>{p}</Badge>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <Button variant="ghost" size="sm" onClick={() => openRights(r)}>
                      Creation rights
                    </Button>
                    {r.is_custom && (
                      <>
                        <Button variant="ghost" size="sm" onClick={() => openEdit(r)}>
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            confirm.ask({
                              title: "Delete this role?",
                              description: `${r.name} will be removed. This fails if any user still holds it.`,
                              confirmLabel: "Delete",
                              onConfirm: () => del.mutateAsync(r.id),
                            })
                          }
                        >
                          Delete
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

      <Modal open={!!editing} onOpenChange={(open) => !open && setEditing(null)} title="Edit permissions" size="md">
        {editing && (
          <div className="space-y-4">
            <Pills options={perms} selected={editPerms} onToggle={(v) => toggle(editPerms, setEditPerms, v)} />
            <Button className="w-full" onClick={() => update.mutate()} disabled={update.isPending}>
              {update.isPending ? "Saving…" : "Save changes"}
            </Button>
          </div>
        )}
      </Modal>

      <Modal
        open={!!rightsFor}
        onOpenChange={(open) => !open && setRightsFor(null)}
        title="Creation rights"
        description={rightsFor ? `Which user types can "${rightsFor.name}" create?` : undefined}
        size="sm"
      >
        {rightsFor && (
          <div className="space-y-4">
            <Pills options={templateNames} selected={rightsSelected} onToggle={(v) => toggle(rightsSelected, setRightsSelected, v)} />
            <Button className="w-full" onClick={() => saveRights.mutate()} disabled={saveRights.isPending}>
              {saveRights.isPending ? "Saving…" : "Save"}
            </Button>
          </div>
        )}
      </Modal>
      {confirm.dialog}
    </div>
  );
}
