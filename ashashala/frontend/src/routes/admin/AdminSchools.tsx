import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import type { ColumnDef } from "@tanstack/react-table";
import { api } from "../../api/client";
import { adminApi } from "../../api/endpoints";
import type { School } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, Input, Label, Skeleton } from "../../components/ui";
import { DataTable } from "../../components/ui/DataTable";
import { useToast } from "../../components/ui/Toast";
import { Modal, useConfirm } from "../../components/ui/Modal";

export default function AdminSchools() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [detailsFor, setDetailsFor] = useState<School | null>(null);
  const [adminFor, setAdminFor] = useState<School | null>(null);
  const [adminName, setAdminName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [tempCredential, setTempCredential] = useState<{ email: string; password: string } | null>(null);

  const details = useQuery({
    queryKey: ["admin", "school-dashboard", detailsFor?.id],
    queryFn: () => adminApi.schoolDashboard(detailsFor!.id),
    enabled: !!detailsFor,
  });

  const schools = useQuery({ queryKey: ["admin", "schools"], queryFn: () => api.get<School[]>("/api/v1/admin/schools") });

  const create = useMutation({
    mutationFn: () => adminApi.createSchool({ name, address: address || undefined }),
    onSuccess: () => {
      toast.push(t("admin.schools.schoolCreated"), "success");
      setName("");
      setAddress("");
      qc.invalidateQueries({ queryKey: ["admin", "schools"] });
    },
    onError: () => toast.push(t("admin.schools.createSchoolFailed"), "error"),
  });

  const toggle = useMutation({
    mutationFn: (s: School) => adminApi.updateSchool(s.id, { is_active: !s.is_active }),
    onSuccess: (_data, s) => {
      toast.push(s.is_active ? t("admin.schools.schoolSuspended") : t("admin.schools.schoolReactivated"), "success");
      qc.invalidateQueries({ queryKey: ["admin", "schools"] });
    },
    onError: () => toast.push(t("admin.schools.updateStatusFailed"), "error"),
  });

  const del = useMutation({
    mutationFn: (id: string) => adminApi.deleteSchool(id),
    onSuccess: () => {
      toast.push(t("admin.schools.schoolDeleted"), "success");
      qc.invalidateQueries({ queryKey: ["admin", "schools"] });
    },
    onError: () => toast.push(t("admin.schools.deleteSchoolFailed"), "error"),
  });

  const createAdmin = useMutation({
    mutationFn: () => adminApi.createSchoolAdmin(adminFor!.id, { name: adminName, email: adminEmail }),
    onSuccess: (res) => {
      setAdminFor(null);
      setTempCredential({ email: adminEmail, password: res.temp_password });
      setAdminName("");
      setAdminEmail("");
    },
    onError: () => toast.push(t("admin.schools.createSchoolAdminFailed"), "error"),
  });

  const askSuspend = (s: School) =>
    confirm.ask({
      title: s.is_active ? t("admin.schools.suspendTitle") : t("admin.schools.reactivateTitle"),
      description: s.is_active
        ? t("admin.schools.suspendDescription", { name: s.name })
        : t("admin.schools.reactivateDescription", { name: s.name }),
      tone: s.is_active ? "danger" : "primary",
      confirmLabel: s.is_active ? t("admin.schools.suspend") : t("admin.schools.reactivate"),
      onConfirm: () => toggle.mutateAsync(s),
    });

  const askDelete = (s: School) =>
    confirm.ask({
      title: t("admin.schools.deleteTitle"),
      description: t("admin.schools.deleteDescription", { name: s.name }),
      tone: "danger",
      confirmLabel: t("admin.schools.delete"),
      onConfirm: () => del.mutateAsync(s.id),
    });

  const columns = useMemo<ColumnDef<School, unknown>[]>(
    () => [
      {
        id: "name",
        accessorFn: (s) => `${s.name} ${s.address ?? ""}`,
        header: t("admin.schools.colName"),
        cell: ({ row }) => (
          <div>
            <div className="font-medium text-slate-700 dark:text-slate-200">{row.original.name}</div>
            <div className="text-xs text-slate-400">{row.original.address}</div>
          </div>
        ),
      },
      {
        id: "status",
        accessorFn: (s) => (s.is_active ? "active" : "suspended"),
        header: t("admin.schools.colStatus"),
        cell: ({ row }) => (
          <Badge tone={row.original.is_active ? "green" : "red"}>
            {row.original.is_active ? t("admin.schools.active") : t("admin.schools.suspended")}
          </Badge>
        ),
      },
      {
        id: "actions",
        header: t("admin.schools.colActions"),
        enableSorting: false,
        enableGlobalFilter: false,
        cell: ({ row }) => {
          const s = row.original;
          return (
            <div className="flex flex-wrap gap-2">
              <Button variant="ghost" size="sm" onClick={() => setDetailsFor(s)}>
                {t("admin.schools.viewDetails")}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setAdminFor(s)}>
                {t("admin.schools.addAdmin")}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => askSuspend(s)}>
                {s.is_active ? t("admin.schools.suspend") : t("admin.schools.reactivate")}
              </Button>
              <Button variant="danger" size="sm" onClick={() => askDelete(s)}>
                {t("admin.schools.delete")}
              </Button>
            </div>
          );
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [t],
  );

  return (
    <div>
      <PageTitle subtitle={t("admin.schools.subtitle")}>{t("admin.schools.title")}</PageTitle>

      <Card className="mb-6">
        <CardHeader title={t("admin.schools.onboardASchool")} />
        <form
          className="p-5 flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div className="flex-1 min-w-[180px]">
            <Label>{t("admin.schools.name")}</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="flex-1 min-w-[180px]">
            <Label>{t("admin.schools.address")}</Label>
            <Input value={address} onChange={(e) => setAddress(e.target.value)} />
          </div>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? t("admin.schools.creating") : t("admin.schools.create")}
          </Button>
        </form>
      </Card>

      <Card>
        <CardHeader title={t("admin.schools.allSchools")} />
        <div className="p-2">
          <DataTable
            data={schools.data ?? []}
            columns={columns}
            isLoading={schools.isLoading}
            emptyTitle={t("admin.schools.noSchoolsYet")}
            emptyHint={t("admin.schools.noSchoolsYetHint")}
            searchPlaceholder={t("common.searchPlaceholder")}
          />
        </div>
      </Card>

      <Modal
        open={!!detailsFor}
        onOpenChange={(open) => !open && setDetailsFor(null)}
        title={detailsFor?.name ?? t("admin.schools.defaultSchoolTitle")}
        description={t("admin.schools.detailsDescription")}
        size="sm"
      >
        {details.isLoading ? (
          <Skeleton className="h-32" />
        ) : (
          <div className="grid grid-cols-2 gap-3">
            <Stat label={t("admin.schools.statTeachers")} value={details.data?.teachers ?? 0} />
            <Stat label={t("admin.schools.statStudents")} value={details.data?.students ?? 0} />
            <Stat label={t("admin.schools.statClasses")} value={details.data?.classes ?? 0} />
            <Stat label={t("admin.schools.statAvgMastery")} value={details.data?.avg_mastery ?? 0} />
          </div>
        )}
      </Modal>

      <Modal
        open={!!adminFor}
        onOpenChange={(open) => !open && setAdminFor(null)}
        title={t("admin.schools.createSchoolAdmin")}
        description={adminFor ? t("admin.schools.createSchoolAdminDescription", { name: adminFor.name }) : undefined}
        size="sm"
      >
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            createAdmin.mutate();
          }}
        >
          <div>
            <Label>{t("admin.schools.name")}</Label>
            <Input value={adminName} onChange={(e) => setAdminName(e.target.value)} required />
          </div>
          <div>
            <Label>{t("admin.schools.email")}</Label>
            <Input type="email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)} required />
          </div>
          <Button type="submit" className="w-full" disabled={createAdmin.isPending}>
            {createAdmin.isPending ? t("admin.schools.creating") : t("admin.schools.createAdmin")}
          </Button>
        </form>
      </Modal>

      <Modal
        open={!!tempCredential}
        onOpenChange={(open) => !open && setTempCredential(null)}
        title={t("admin.schools.tempPasswordTitle")}
        description={t("admin.schools.tempPasswordDesc")}
        size="sm"
      >
        {tempCredential && (
          <div className="space-y-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t("admin.schools.email")}</div>
              <div className="text-sm font-medium text-slate-700">{tempCredential.email}</div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t("admin.schools.tempPasswordLabel")}</div>
              <div className="flex items-center gap-2 mt-1">
                <code className="flex-1 px-3 py-2 rounded-lg bg-slate-50 border border-slate-200 text-sm font-mono text-slate-700">
                  {tempCredential.password}
                </code>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => navigator.clipboard.writeText(tempCredential.password)}
                >
                  {t("admin.schools.copy")}
                </Button>
              </div>
            </div>
            <Button type="button" className="w-full" onClick={() => setTempCredential(null)}>
              {t("admin.schools.done")}
            </Button>
          </div>
        )}
      </Modal>

      {confirm.dialog}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center rounded-xl bg-slate-50 py-4">
      <div className="text-xl font-bold text-slate-800 tabular-nums">{value}</div>
      <div className="text-[11px] text-slate-400 uppercase tracking-wide mt-0.5">{label}</div>
    </div>
  );
}
