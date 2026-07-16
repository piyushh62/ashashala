import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { schoolApi } from "../../api/endpoints";
import type { Role, UserRow } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Icon, Input, Pager, Select, Skeleton, Table } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { Modal, useConfirm } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";
import { TempCredentialModal } from "../../components/TempCredentialModal";
import { exportRowsToXlsx } from "../../lib/exportXlsx";
import { todayIso } from "../../lib/dates";

const ROLES: Role[] = ["teacher", "student", "parent"];
const ROLE_TITLE_KEY: Record<Role, string> = {
  super_admin: "roleTitle.superAdmin",
  school_admin: "roleTitle.schoolAdmin",
  teacher: "roleTitle.teacher",
  student: "roleTitle.student",
  parent: "roleTitle.parent",
};

const editUserSchema = z.object({
  name: z.string().min(1, "Name is required"),
  grade: z.string().optional(),
});
type EditUserForm = z.infer<typeof editUserSchema>;

const VALIDATION_MESSAGE_KEYS: Record<string, string> = {
  "Name is required": "common.nameRequired",
  "Email is required": "common.emailRequired",
  "Enter a valid email address": "common.invalidEmail",
  "Grade is required for students": "school.users.gradeRequiredForStudents",
};

export default function SchoolUsers() {
  const { t } = useTranslation();
  const errMsg = (raw?: string) => (raw ? t(VALIDATION_MESSAGE_KEYS[raw] ?? raw) : undefined);
  const toast = useToast();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const navigate = useNavigate();
  const [filter, setFilter] = useState<Role | "">("");
  const [tempCredential, setTempCredential] = useState<{ email: string; password: string } | null>(null);
  const [editingUser, setEditingUser] = useState<UserRow | null>(null);
  const [absentTarget, setAbsentTarget] = useState<UserRow | null>(null);
  const [absenceDate, setAbsenceDate] = useState(() => todayIso());
  const [absenceReason, setAbsenceReason] = useState("");

  const PAGE_SIZE = 20;
  const [offset, setOffset] = useState(0);
  const changeFilter = (r: Role | "") => {
    setFilter(r);
    setOffset(0);
  };

  const invalidateUsers = () => qc.invalidateQueries({ queryKey: ["school", "users"] });

  const users = useQuery({
    queryKey: ["school", "users", filter, offset],
    queryFn: () => schoolApi.listUsers(filter || undefined, PAGE_SIZE, offset),
  });
  const userRows = users.data?.items ?? [];
  const total = users.data?.total ?? 0;

  const exportUsers = () => {
    if (!userRows.length) return;
    exportRowsToXlsx(
      userRows.map((u) => ({
        name: u.name,
        email: u.email,
        role: t(ROLE_TITLE_KEY[u.role]),
        grade: u.grade ?? "",
        status: u.is_active ? t("school.users.active") : t("school.users.inactive"),
      })),
      {
        filename: `users-${filter || "all"}-${todayIso()}`,
        sheetName: t("school.users.title"),
        headers: {
          name: t("school.users.name"),
          email: t("school.users.email"),
          role: t("school.users.role"),
          grade: t("school.users.grade"),
          status: t("school.users.status"),
        },
      },
    );
  };

  const {
    register: registerEdit,
    handleSubmit: handleEditSubmit,
    reset: resetEdit,
    formState: { errors: editErrors, isSubmitting: isEditSubmitting },
  } = useForm<EditUserForm>({ resolver: zodResolver(editUserSchema) });

  const openEdit = (u: UserRow) => {
    setEditingUser(u);
    resetEdit({ name: u.name, grade: u.grade != null ? String(u.grade) : "" });
  };

  const mUpdate = useMutation({
    mutationFn: (values: EditUserForm) =>
      schoolApi.updateUser(editingUser!.id, {
        name: values.name,
        grade: values.grade ? Number(values.grade) : undefined,
      }),
    onSuccess: () => {
      toast.push(t("school.users.userUpdated"), "success");
      setEditingUser(null);
      invalidateUsers();
    },
    onError: () => toast.push(t("school.users.updateUserFailed"), "error"),
  });

  const mToggleActive = useMutation({
    mutationFn: (u: UserRow) => schoolApi.updateUser(u.id, { is_active: !u.is_active }),
    onSuccess: (_res, u) => {
      toast.push(u.is_active ? t("school.users.userDeactivated") : t("school.users.userReactivated"), "success");
      invalidateUsers();
    },
    onError: () => toast.push(t("school.users.updateStatusFailed"), "error"),
  });

  const mReset = useMutation({
    mutationFn: (u: UserRow) => schoolApi.resetUserPassword(u.id),
    onSuccess: (res, u) => setTempCredential({ email: u.email, password: res.temp_password }),
    onError: () => toast.push(t("school.users.passwordResetFailed"), "error"),
  });

  const mMarkAbsent = useMutation({
    mutationFn: () =>
      schoolApi.markTeacherAbsent({
        teacher_id: absentTarget!.id,
        absence_date: absenceDate,
        reason: absenceReason || undefined,
      }),
    onSuccess: (res) => {
      toast.push(
        res.substitute_suggestions
          ? t("school.users.absenceRecordedWithSubs", { count: res.substitute_suggestions })
          : t("school.users.absenceRecordedNoClasses"),
        "success",
      );
      setAbsentTarget(null);
      setAbsenceReason("");
    },
    onError: () => toast.push(t("school.users.absenceRecordFailed"), "error"),
  });

  return (
    <div>
      <PageTitle subtitle={t("school.users.subtitle")}>{t("school.users.title")}</PageTitle>

      <TempCredentialModal credential={tempCredential} onClose={() => setTempCredential(null)} />

      <Modal
        open={!!editingUser}
        onOpenChange={(open) => !open && setEditingUser(null)}
        title={t("school.users.editUserTitle")}
        size="sm"
      >
        {editingUser && (
          <form className="space-y-3" onSubmit={handleEditSubmit((values) => mUpdate.mutateAsync(values))}>
            <FormField label={t("school.users.name")} error={errMsg(editErrors.name?.message)}>
              <Input invalid={!!editErrors.name} {...registerEdit("name")} />
            </FormField>
            {editingUser.role === "student" && (
              <FormField label={t("school.users.grade")} error={errMsg(editErrors.grade?.message)}>
                <Input type="number" invalid={!!editErrors.grade} {...registerEdit("grade")} />
              </FormField>
            )}
            <Button type="submit" className="w-full" disabled={isEditSubmitting}>
              {isEditSubmitting ? t("common.saving") : t("common.saveChanges")}
            </Button>
          </form>
        )}
      </Modal>

      <Modal
        open={!!absentTarget}
        onOpenChange={(open) => !open && setAbsentTarget(null)}
        title={t("school.users.markAbsentTitle")}
        description={absentTarget ? t("school.users.markAbsentDesc", { name: absentTarget.name }) : undefined}
        size="sm"
      >
        {absentTarget && (
          <div className="space-y-3">
            <FormField label={t("school.users.absenceDate")}>
              <Input type="date" value={absenceDate} onChange={(e) => setAbsenceDate(e.target.value)} />
            </FormField>
            <FormField label={t("school.users.reason")} optional>
              <Input value={absenceReason} onChange={(e) => setAbsenceReason(e.target.value)} placeholder={t("school.users.reasonPlaceholder")} />
            </FormField>
            <Button
              type="button"
              className="w-full"
              onClick={() => mMarkAbsent.mutate()}
              disabled={!absenceDate || mMarkAbsent.isPending}
            >
              {mMarkAbsent.isPending ? t("school.users.recording") : t("school.users.recordAbsence")}
            </Button>
          </div>
        )}
      </Modal>

      <Card>
        <CardHeader
          title={t("school.users.allUsers")}
          action={
            <div className="flex items-center gap-2">
              <Select
                className="w-40"
                value={filter}
                onChange={(e) => changeFilter(e.target.value as Role | "")}
              >
                <option value="">{t("school.users.allRolesOption")}</option>
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {t(ROLE_TITLE_KEY[r])}
                  </option>
                ))}
              </Select>
              <Button variant="ghost" size="sm" onClick={exportUsers} disabled={!userRows.length}>
                <Icon name="download" className="w-4 h-4" />
                {t("school.users.exportExcel")}
              </Button>
              <Button size="sm" onClick={() => navigate("/school/users/new")}>
                <Icon name="add" className="w-4 h-4" />
                {t("school.users.addUser")}
              </Button>
            </div>
          }
        />
        <div className="p-2">
          {users.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !userRows.length ? (
            <EmptyState title={t("school.users.noUsersFound")} />
          ) : (
            <Table head={[t("school.users.name"), t("school.users.email"), t("school.users.role"), t("school.users.status"), ""]}>
              {userRows.map((u) => (
                <tr key={u.id} className="border-b border-slate-50">
                  <td className="px-4 py-2 font-medium text-slate-700">{u.name}</td>
                  <td className="px-4 py-2 text-slate-500">{u.email}</td>
                  <td className="px-4 py-2">
                    <Badge>{t(ROLE_TITLE_KEY[u.role])}</Badge>
                  </td>
                  <td className="px-4 py-2">
                    <Badge tone={u.is_active ? "green" : "red"}>{u.is_active ? t("school.users.active") : t("school.users.inactive")}</Badge>
                  </td>
                  <td className="px-4 py-2 text-right whitespace-nowrap">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(u)}>
                      {t("school.users.edit")}
                    </Button>
                    {u.role === "teacher" && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setAbsenceDate(todayIso());
                          setAbsenceReason("");
                          setAbsentTarget(u);
                        }}
                      >
                        {t("school.users.markAbsent")}
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => confirm.ask({
                        title: t("school.users.resetPasswordTitle"),
                        description: t("school.users.resetPasswordDesc", { name: u.name }),
                        confirmLabel: t("school.users.resetPassword"),
                        onConfirm: () => mReset.mutateAsync(u),
                      })}
                    >
                      {t("school.users.resetPassword")}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => confirm.ask({
                        title: u.is_active ? t("school.users.deactivateTitle") : t("school.users.reactivateTitle"),
                        description: u.is_active
                          ? t("school.users.deactivateDesc", { name: u.name })
                          : t("school.users.reactivateDesc", { name: u.name }),
                        tone: u.is_active ? "danger" : "primary",
                        confirmLabel: u.is_active ? t("school.users.deactivate") : t("school.users.reactivate"),
                        onConfirm: () => mToggleActive.mutateAsync(u),
                      })}
                    >
                      {u.is_active ? t("school.users.deactivate") : t("school.users.reactivate")}
                    </Button>
                  </td>
                </tr>
              ))}
            </Table>
          )}
          <Pager offset={offset} limit={PAGE_SIZE} total={total} count={userRows.length} onOffsetChange={setOffset} />
        </div>
      </Card>
      {confirm.dialog}
    </div>
  );
}
