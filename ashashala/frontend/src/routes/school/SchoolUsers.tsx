import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { z } from "zod";
import { schoolApi } from "../../api/endpoints";
import type { Role, UserRow } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Input, Select, Skeleton, Table } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { Modal, useConfirm } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";

const ROLES: Role[] = ["teacher", "student", "parent"];
const ROLE_TITLE_KEY: Record<Role, string> = {
  super_admin: "roleTitle.superAdmin",
  school_admin: "roleTitle.schoolAdmin",
  teacher: "roleTitle.teacher",
  student: "roleTitle.student",
  parent: "roleTitle.parent",
};

const createUserSchema = z
  .object({
    name: z.string().min(1, "Name is required"),
    email: z.string().min(1, "Email is required").email("Enter a valid email address"),
    role: z.enum(["teacher", "student", "parent"]),
    grade: z.string().optional(),
  })
  .refine((v) => v.role !== "student" || (v.grade && v.grade.trim().length > 0), {
    message: "Grade is required for students",
    path: ["grade"],
  });

type CreateUserForm = z.infer<typeof createUserSchema>;

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
  const fileInput = useRef<HTMLInputElement>(null);
  const [filter, setFilter] = useState<Role | "">("");
  const [tempCredential, setTempCredential] = useState<{ email: string; password: string } | null>(null);
  const [editingUser, setEditingUser] = useState<UserRow | null>(null);
  const [bulkResult, setBulkResult] = useState<{ id: string; email: string; temp_password: string }[] | null>(null);
  const [absentTarget, setAbsentTarget] = useState<UserRow | null>(null);
  const [absenceDate, setAbsenceDate] = useState(() => new Date().toISOString().slice(0, 10));
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
  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = offset + userRows.length;

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateUserForm>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { name: "", email: "", role: "student", grade: "" },
  });
  const selectedRole = watch("role");

  const create = useMutation({
    mutationFn: (values: CreateUserForm) =>
      schoolApi.createUser({
        name: values.name,
        email: values.email,
        role: values.role,
        grade: values.grade ? Number(values.grade) : undefined,
      }),
    onSuccess: (res, values) => {
      if (res.temp_password) {
        setTempCredential({ email: values.email, password: res.temp_password });
      } else {
        toast.push(t("school.users.userCreated"), "success");
      }
      reset();
      invalidateUsers();
    },
    onError: () => toast.push(t("school.users.createUserFailed"), "error"),
  });

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

  const mBulk = useMutation({
    mutationFn: (form: FormData) => schoolApi.bulkImportUsers(form),
    onSuccess: (res) => {
      setBulkResult(res.created);
      invalidateUsers();
      if (fileInput.current) fileInput.current.value = "";
    },
    onError: () => toast.push(t("school.users.csvImportFailed"), "error"),
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

  const onBulkFileChosen = (file: File | null) => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    mBulk.mutate(form);
  };

  return (
    <div>
      <PageTitle subtitle={t("school.users.subtitle")}>{t("school.users.title")}</PageTitle>

      <Card className="mb-6">
        <CardHeader title={t("school.users.addUser")} />
        <form
          className="p-5 grid md:grid-cols-5 gap-3 items-start"
          onSubmit={handleSubmit((values) => create.mutateAsync(values))}
        >
          <FormField label={t("school.users.name")} error={errMsg(errors.name?.message)}>
            <Input invalid={!!errors.name} {...register("name")} />
          </FormField>
          <FormField label={t("school.users.email")} error={errMsg(errors.email?.message)}>
            <Input type="email" invalid={!!errors.email} {...register("email")} />
          </FormField>
          <FormField label={t("school.users.role")}>
            <Select {...register("role")}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {t(ROLE_TITLE_KEY[r])}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label={t("school.users.grade")} error={errMsg(errors.grade?.message)} optional={selectedRole !== "student"}>
            <Input type="number" invalid={!!errors.grade} disabled={selectedRole !== "student"} {...register("grade")} />
          </FormField>
          <Button type="submit" disabled={isSubmitting} className="mt-6">
            {isSubmitting ? t("school.users.adding") : t("school.users.add")}
          </Button>
        </form>
      </Card>

      <Card className="mb-6">
        <CardHeader
          title={t("school.users.bulkImportTitle")}
          subtitle={t("school.users.bulkImportSubtitle")}
        />
        <div className="p-5 flex items-center gap-3">
          <input
            ref={fileInput}
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => onBulkFileChosen(e.target.files?.[0] ?? null)}
            disabled={mBulk.isPending}
          />
          {mBulk.isPending && <span className="text-sm text-slate-400">{t("school.users.importing")}</span>}
        </div>
      </Card>

      <Modal
        open={!!tempCredential}
        onOpenChange={(open) => !open && setTempCredential(null)}
        title={t("school.users.tempPasswordTitle")}
        description={t("school.users.tempPasswordDesc")}
        size="sm"
      >
        {tempCredential && (
          <div className="space-y-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t("school.users.email")}</div>
              <div className="text-sm font-medium text-slate-700">{tempCredential.email}</div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{t("school.users.tempPasswordLabel")}</div>
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
                  {t("school.users.copy")}
                </Button>
              </div>
            </div>
            <Button type="button" className="w-full" onClick={() => setTempCredential(null)}>
              {t("school.users.done")}
            </Button>
          </div>
        )}
      </Modal>

      <Modal
        open={!!bulkResult}
        onOpenChange={(open) => !open && setBulkResult(null)}
        title={t("school.users.importCompleteTitle")}
        description={bulkResult ? t("school.users.importCompleteDesc", { count: bulkResult.length }) : undefined}
        size="md"
      >
        {bulkResult && (
          <div className="space-y-3">
            {bulkResult.length === 0 ? (
              <EmptyState title={t("school.users.noRowsImported")} hint={t("school.users.noRowsImportedHint")} />
            ) : (
              <div className="max-h-72 overflow-y-auto">
                <Table head={[t("school.users.email"), t("school.users.colTempPassword")]}>
                  {bulkResult.map((r) => (
                    <tr key={r.id} className="border-b border-slate-50">
                      <td className="px-4 py-2 text-slate-700">{r.email}</td>
                      <td className="px-4 py-2 font-mono text-xs text-slate-600">{r.temp_password}</td>
                    </tr>
                  ))}
                </Table>
              </div>
            )}
            <Button type="button" className="w-full" onClick={() => setBulkResult(null)}>
              {t("school.users.done")}
            </Button>
          </div>
        )}
      </Modal>

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
            <select
              className="text-sm border border-slate-300 rounded-lg px-2 py-1"
              value={filter}
              onChange={(e) => changeFilter(e.target.value as Role | "")}
            >
              <option value="">{t("school.users.allRolesOption")}</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {t(ROLE_TITLE_KEY[r])}
                </option>
              ))}
            </select>
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
                          setAbsenceDate(new Date().toISOString().slice(0, 10));
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
          {total > 0 && (
            <div className="flex items-center justify-between px-3 py-3 text-sm text-slate-500">
              <span>
                {t("common.rangeOfTotal", { start: rangeStart, end: rangeEnd, total })}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  disabled={offset === 0}
                >
                  {t("common.previous")}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  disabled={rangeEnd >= total}
                >
                  {t("common.next")}
                </Button>
              </div>
            </div>
          )}
        </div>
      </Card>
      {confirm.dialog}
    </div>
  );
}
