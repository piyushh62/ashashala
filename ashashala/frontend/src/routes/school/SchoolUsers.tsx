import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { schoolApi } from "../../api/endpoints";
import type { Role, UserRow } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Input, Select, Skeleton, Table } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { Modal, useConfirm } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";

const ROLES: Role[] = ["teacher", "student", "parent"];

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

export default function SchoolUsers() {
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
        toast.push("User created.", "success");
      }
      reset();
      invalidateUsers();
    },
    onError: () => toast.push("Couldn't create user (email may be taken).", "error"),
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
      toast.push("User updated.", "success");
      setEditingUser(null);
      invalidateUsers();
    },
    onError: () => toast.push("Couldn't update user.", "error"),
  });

  const mToggleActive = useMutation({
    mutationFn: (u: UserRow) => schoolApi.updateUser(u.id, { is_active: !u.is_active }),
    onSuccess: (_res, u) => {
      toast.push(u.is_active ? "User deactivated." : "User reactivated.", "success");
      invalidateUsers();
    },
    onError: () => toast.push("Couldn't update status.", "error"),
  });

  const mReset = useMutation({
    mutationFn: (u: UserRow) => schoolApi.resetUserPassword(u.id),
    onSuccess: (res, u) => setTempCredential({ email: u.email, password: res.temp_password }),
    onError: () => toast.push("Couldn't reset password.", "error"),
  });

  const mBulk = useMutation({
    mutationFn: (form: FormData) => schoolApi.bulkImportUsers(form),
    onSuccess: (res) => {
      setBulkResult(res.created);
      invalidateUsers();
      if (fileInput.current) fileInput.current.value = "";
    },
    onError: () => toast.push("CSV import failed.", "error"),
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
          ? `Absence recorded — ${res.substitute_suggestions} substitute suggestion(s) queued for approval.`
          : "Absence recorded — no classes scheduled that day.",
        "success",
      );
      setAbsentTarget(null);
      setAbsenceReason("");
    },
    onError: () => toast.push("Couldn't record the absence.", "error"),
  });

  const onBulkFileChosen = (file: File | null) => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    mBulk.mutate(form);
  };

  return (
    <div>
      <PageTitle subtitle="Invite teachers, students and parents.">Users</PageTitle>

      <Card className="mb-6">
        <CardHeader title="Add a user" />
        <form
          className="p-5 grid md:grid-cols-5 gap-3 items-start"
          onSubmit={handleSubmit((values) => create.mutateAsync(values))}
        >
          <FormField label="Name" error={errors.name?.message}>
            <Input invalid={!!errors.name} {...register("name")} />
          </FormField>
          <FormField label="Email" error={errors.email?.message}>
            <Input type="email" invalid={!!errors.email} {...register("email")} />
          </FormField>
          <FormField label="Role">
            <Select {...register("role")}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Grade" error={errors.grade?.message} optional={selectedRole !== "student"}>
            <Input type="number" invalid={!!errors.grade} disabled={selectedRole !== "student"} {...register("grade")} />
          </FormField>
          <Button type="submit" disabled={isSubmitting} className="mt-6">
            {isSubmitting ? "Adding…" : "Add"}
          </Button>
        </form>
      </Card>

      <Card className="mb-6">
        <CardHeader
          title="Bulk import students"
          subtitle="Upload a CSV with columns: name, email, grade. Passwords are auto-generated per row."
        />
        <div className="p-5 flex items-center gap-3">
          <input
            ref={fileInput}
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => onBulkFileChosen(e.target.files?.[0] ?? null)}
            disabled={mBulk.isPending}
          />
          {mBulk.isPending && <span className="text-sm text-slate-400">Importing…</span>}
        </div>
      </Card>

      <Modal
        open={!!tempCredential}
        onOpenChange={(open) => !open && setTempCredential(null)}
        title="Temporary password"
        description="Share this password securely — it won't be shown again."
        size="sm"
      >
        {tempCredential && (
          <div className="space-y-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Email</div>
              <div className="text-sm font-medium text-slate-700">{tempCredential.email}</div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Temporary password</div>
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
                  Copy
                </Button>
              </div>
            </div>
            <Button type="button" className="w-full" onClick={() => setTempCredential(null)}>
              Done
            </Button>
          </div>
        )}
      </Modal>

      <Modal
        open={!!bulkResult}
        onOpenChange={(open) => !open && setBulkResult(null)}
        title="Import complete"
        description={bulkResult ? `${bulkResult.length} user(s) created.` : undefined}
        size="md"
      >
        {bulkResult && (
          <div className="space-y-3">
            {bulkResult.length === 0 ? (
              <EmptyState title="No rows imported" hint="Check that your CSV has name, email and grade columns and no duplicate emails." />
            ) : (
              <div className="max-h-72 overflow-y-auto">
                <Table head={["Email", "Temp password"]}>
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
              Done
            </Button>
          </div>
        )}
      </Modal>

      <Modal
        open={!!editingUser}
        onOpenChange={(open) => !open && setEditingUser(null)}
        title="Edit user"
        size="sm"
      >
        {editingUser && (
          <form className="space-y-3" onSubmit={handleEditSubmit((values) => mUpdate.mutateAsync(values))}>
            <FormField label="Name" error={editErrors.name?.message}>
              <Input invalid={!!editErrors.name} {...registerEdit("name")} />
            </FormField>
            {editingUser.role === "student" && (
              <FormField label="Grade" error={editErrors.grade?.message}>
                <Input type="number" invalid={!!editErrors.grade} {...registerEdit("grade")} />
              </FormField>
            )}
            <Button type="submit" className="w-full" disabled={isEditSubmitting}>
              {isEditSubmitting ? "Saving…" : "Save changes"}
            </Button>
          </form>
        )}
      </Modal>

      <Modal
        open={!!absentTarget}
        onOpenChange={(open) => !open && setAbsentTarget(null)}
        title="Mark teacher absent"
        description={absentTarget ? `${absentTarget.name}'s classes for that day will get substitute suggestions.` : undefined}
        size="sm"
      >
        {absentTarget && (
          <div className="space-y-3">
            <FormField label="Absence date">
              <Input type="date" value={absenceDate} onChange={(e) => setAbsenceDate(e.target.value)} />
            </FormField>
            <FormField label="Reason" optional>
              <Input value={absenceReason} onChange={(e) => setAbsenceReason(e.target.value)} placeholder="e.g. Sick leave" />
            </FormField>
            <Button
              type="button"
              className="w-full"
              onClick={() => mMarkAbsent.mutate()}
              disabled={!absenceDate || mMarkAbsent.isPending}
            >
              {mMarkAbsent.isPending ? "Recording…" : "Record absence"}
            </Button>
          </div>
        )}
      </Modal>

      <Card>
        <CardHeader
          title="All users"
          action={
            <select
              className="text-sm border border-slate-300 rounded-lg px-2 py-1"
              value={filter}
              onChange={(e) => changeFilter(e.target.value as Role | "")}
            >
              <option value="">All roles</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          }
        />
        <div className="p-2">
          {users.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !userRows.length ? (
            <EmptyState title="No users found" />
          ) : (
            <Table head={["Name", "Email", "Role", "Status", ""]}>
              {userRows.map((u) => (
                <tr key={u.id} className="border-b border-slate-50">
                  <td className="px-4 py-2 font-medium text-slate-700">{u.name}</td>
                  <td className="px-4 py-2 text-slate-500">{u.email}</td>
                  <td className="px-4 py-2">
                    <Badge>{u.role}</Badge>
                  </td>
                  <td className="px-4 py-2">
                    <Badge tone={u.is_active ? "green" : "red"}>{u.is_active ? "active" : "inactive"}</Badge>
                  </td>
                  <td className="px-4 py-2 text-right whitespace-nowrap">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(u)}>
                      Edit
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
                        Mark absent
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => confirm.ask({
                        title: "Reset this user's password?",
                        description: `${u.name}'s current password will stop working immediately.`,
                        confirmLabel: "Reset password",
                        onConfirm: () => mReset.mutateAsync(u),
                      })}
                    >
                      Reset password
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => confirm.ask({
                        title: u.is_active ? "Deactivate this user?" : "Reactivate this user?",
                        description: u.is_active
                          ? `${u.name} will no longer be able to log in.`
                          : `${u.name} will be able to log in again.`,
                        tone: u.is_active ? "danger" : "primary",
                        confirmLabel: u.is_active ? "Deactivate" : "Reactivate",
                        onConfirm: () => mToggleActive.mutateAsync(u),
                      })}
                    >
                      {u.is_active ? "Deactivate" : "Reactivate"}
                    </Button>
                  </td>
                </tr>
              ))}
            </Table>
          )}
          {total > 0 && (
            <div className="flex items-center justify-between px-3 py-3 text-sm text-slate-500">
              <span>
                {rangeStart}–{rangeEnd} of {total}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  disabled={offset === 0}
                >
                  Previous
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  disabled={rangeEnd >= total}
                >
                  Next
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
