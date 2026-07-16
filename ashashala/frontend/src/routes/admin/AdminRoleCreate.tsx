import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { adminApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, Input } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { useToast } from "../../components/ui/Toast";
import { PermissionChecklist } from "../../components/PermissionChecklist";

const createSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
});
type CreateForm = z.infer<typeof createSchema>;

const VALIDATION_MESSAGE_KEYS: Record<string, string> = {
  "Name is required": "common.nameRequired",
};

export default function AdminRoleCreate() {
  const { t } = useTranslation();
  const errMsg = (raw?: string) => (raw ? t(VALIDATION_MESSAGE_KEYS[raw] ?? raw) : undefined);
  const toast = useToast();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [createPerms, setCreatePerms] = useState<string[]>([]);

  const permissions = useQuery({ queryKey: ["admin", "permissions"], queryFn: () => adminApi.listPermissions() });

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateForm>({ resolver: zodResolver(createSchema), defaultValues: { name: "", description: "" } });

  const create = useMutation({
    mutationFn: (values: CreateForm) =>
      adminApi.createRoleTemplate({ name: values.name, description: values.description || undefined, permissions: createPerms }),
    onSuccess: () => {
      toast.push(t("admin.roles.roleTemplateCreated"), "success");
      qc.invalidateQueries({ queryKey: ["admin", "role-templates"] });
      navigate("/admin/roles");
    },
    onError: () => toast.push(t("admin.roles.createTemplateFailed"), "error"),
  });

  const togglePerm = (perm: string) =>
    setCreatePerms((list) => (list.includes(perm) ? list.filter((p) => p !== perm) : [...list, perm]));

  const perms = permissions.data ?? [];

  return (
    <div>
      <PageTitle subtitle={t("admin.roles.subtitle")}>{t("admin.roles.newRoleTemplate")}</PageTitle>

      <Card>
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
            <PermissionChecklist
              permissions={perms}
              loading={permissions.isLoading}
              selected={createPerms}
              onToggle={togglePerm}
              idPrefix="create"
            />
          </div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? t("admin.roles.creating") : t("admin.roles.createTemplate")}
          </Button>
        </form>
      </Card>
    </div>
  );
}
