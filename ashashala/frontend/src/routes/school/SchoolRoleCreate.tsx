import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { schoolApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, Input } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { useToast } from "../../components/ui/Toast";
import { PermissionChecklist } from "../../components/PermissionChecklist";

const createSchema = z.object({ name: z.string().min(1) });
type CreateForm = z.infer<typeof createSchema>;

export default function SchoolRoleCreate() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [createPerms, setCreatePerms] = useState<string[]>([]);

  const permissions = useQuery({ queryKey: ["school", "permissions"], queryFn: () => schoolApi.listPermissions() });

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateForm>({ resolver: zodResolver(createSchema), defaultValues: { name: "" } });

  const create = useMutation({
    mutationFn: (values: CreateForm) => schoolApi.createRole({ name: values.name, permissions: createPerms }),
    onSuccess: () => {
      toast.push(t("school.roles.roleCreated"), "success");
      qc.invalidateQueries({ queryKey: ["school", "roles"] });
      navigate("/school/roles");
    },
    onError: () => toast.push(t("school.roles.createRoleFailed"), "error"),
  });

  const togglePerm = (perm: string) =>
    setCreatePerms((list) => (list.includes(perm) ? list.filter((p) => p !== perm) : [...list, perm]));

  const perms = permissions.data ?? [];

  return (
    <div>
      <PageTitle subtitle={t("school.roles.subtitle")}>{t("school.roles.newCustomRole")}</PageTitle>

      <Card>
        <CardHeader title={t("school.roles.newCustomRole")} />
        <form className="p-5 space-y-4" onSubmit={handleSubmit((v) => create.mutateAsync(v))}>
          <FormField label={t("school.roles.name")} error={errors.name ? t("common.nameRequired") : undefined}>
            <Input invalid={!!errors.name} {...register("name")} className="max-w-sm" />
          </FormField>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{t("school.roles.permissions")}</div>
            <PermissionChecklist
              permissions={perms}
              loading={permissions.isLoading}
              selected={createPerms}
              onToggle={togglePerm}
              idPrefix="create"
            />
          </div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? t("school.roles.creating") : t("school.roles.createRole")}
          </Button>
        </form>
      </Card>
    </div>
  );
}
