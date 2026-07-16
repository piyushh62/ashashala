import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { schoolApi } from "../../api/endpoints";
import type { Role } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, EmptyState, Input, Select, Table } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { Dropzone } from "../../components/ui/Dropzone";
import { Modal } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";
import { TempCredentialModal } from "../../components/TempCredentialModal";

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

const VALIDATION_MESSAGE_KEYS: Record<string, string> = {
  "Name is required": "common.nameRequired",
  "Email is required": "common.emailRequired",
  "Enter a valid email address": "common.invalidEmail",
  "Grade is required for students": "school.users.gradeRequiredForStudents",
};

export default function SchoolUserCreate() {
  const { t } = useTranslation();
  const errMsg = (raw?: string) => (raw ? t(VALIDATION_MESSAGE_KEYS[raw] ?? raw) : undefined);
  const toast = useToast();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [bulkFile, setBulkFile] = useState<File | null>(null);
  const [tempCredential, setTempCredential] = useState<{ email: string; password: string } | null>(null);
  const [bulkResult, setBulkResult] = useState<{ id: string; email: string; temp_password: string }[] | null>(null);

  const invalidateUsers = () => qc.invalidateQueries({ queryKey: ["school", "users"] });
  const goToList = () => navigate("/school/users");

  const {
    register,
    handleSubmit,
    watch,
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
      invalidateUsers();
      if (res.temp_password) {
        // Credential is shown once — navigate only after the modal is closed.
        setTempCredential({ email: values.email, password: res.temp_password });
      } else {
        toast.push(t("school.users.userCreated"), "success");
        goToList();
      }
    },
    onError: () => toast.push(t("school.users.createUserFailed"), "error"),
  });

  const mBulk = useMutation({
    mutationFn: (form: FormData) => schoolApi.bulkImportUsers(form),
    onSuccess: (res) => {
      setBulkResult(res.created);
      invalidateUsers();
      setBulkFile(null);
    },
    onError: () => toast.push(t("school.users.csvImportFailed"), "error"),
  });

  const onBulkFileChosen = (file: File | null) => {
    setBulkFile(file);
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    mBulk.mutate(form);
  };

  return (
    <div>
      <PageTitle subtitle={t("school.users.subtitle")}>{t("school.users.addUser")}</PageTitle>

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

      <Card>
        <CardHeader
          title={t("school.users.bulkImportTitle")}
          subtitle={t("school.users.bulkImportSubtitle")}
        />
        <div className="p-5 flex items-center gap-3">
          <Dropzone
            className="flex-1"
            file={bulkFile}
            onFile={onBulkFileChosen}
            accept={{ "text/csv": [".csv"] }}
            disabled={mBulk.isPending}
            browseLabel={t("school.users.bulkDropzoneLabel")}
            hint={t("school.users.bulkDropzoneHint")}
          />
          {mBulk.isPending && <span className="text-sm text-slate-400">{t("school.users.importing")}</span>}
        </div>
      </Card>

      <TempCredentialModal
        credential={tempCredential}
        onClose={() => {
          setTempCredential(null);
          goToList();
        }}
      />

      <Modal
        open={!!bulkResult}
        onOpenChange={(open) => {
          if (!open) {
            setBulkResult(null);
            goToList();
          }
        }}
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
            <Button
              type="button"
              className="w-full"
              onClick={() => {
                setBulkResult(null);
                goToList();
              }}
            >
              {t("school.users.done")}
            </Button>
          </div>
        )}
      </Modal>
    </div>
  );
}
