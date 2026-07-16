import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { adminApi } from "../../api/endpoints";
import type { RoleTemplateOut } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Icon, Skeleton } from "../../components/ui";
import { Modal, useConfirm } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";
import { PermissionChecklist } from "../../components/PermissionChecklist";

export default function AdminRoles() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const navigate = useNavigate();
  const [editing, setEditing] = useState<RoleTemplateOut | null>(null);
  const [selectedPerms, setSelectedPerms] = useState<string[]>([]);

  const permissions = useQuery({ queryKey: ["admin", "permissions"], queryFn: () => adminApi.listPermissions() });
  const templates = useQuery({ queryKey: ["admin", "role-templates"], queryFn: () => adminApi.listRoleTemplates() });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["admin", "role-templates"] });

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

      <Card>
        <CardHeader
          title={t("admin.roles.allRoleTemplates")}
          action={
            <Button size="sm" onClick={() => navigate("/admin/roles/new")}>
              <Icon name="add" className="w-4 h-4" />
              {t("admin.roles.newRoleTemplate")}
            </Button>
          }
        />
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
            <PermissionChecklist
              permissions={perms}
              loading={permissions.isLoading}
              selected={selectedPerms}
              onToggle={(key) => togglePerm(selectedPerms, setSelectedPerms, key)}
              idPrefix="edit"
            />
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
