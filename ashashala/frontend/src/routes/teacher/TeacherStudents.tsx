import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { z } from "zod";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, Input } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { useToast } from "../../components/ui/Toast";
import { TempCredentialModal } from "../../components/TempCredentialModal";

const studentSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  grade: z.string().optional(),
});
type StudentForm = z.infer<typeof studentSchema>;

const parentSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  student_id: z.string().min(1, "Student ID is required"),
});
type ParentForm = z.infer<typeof parentSchema>;

const VALIDATION_MESSAGE_KEYS: Record<string, string> = {
  "Name is required": "common.nameRequired",
  "Email is required": "common.emailRequired",
  "Enter a valid email address": "common.invalidEmail",
  "Student ID is required": "teacher.students.studentIdRequired",
};

export default function TeacherStudents() {
  const { t } = useTranslation();
  const errMsg = (raw?: string) => (raw ? t(VALIDATION_MESSAGE_KEYS[raw] ?? raw) : undefined);
  const permissionDeniedMessage = (action: string) => t("teacher.students.permissionDenied", { action });
  const toast = useToast();
  const [tempCredential, setTempCredential] = useState<{ email: string; password: string } | null>(null);

  const studentForm = useForm<StudentForm>({
    resolver: zodResolver(studentSchema),
    defaultValues: { name: "", email: "", grade: "" },
  });
  const createStudent = useMutation({
    mutationFn: (values: StudentForm) =>
      teacherApi.createStudent({ name: values.name, email: values.email, grade: values.grade ? Number(values.grade) : undefined }),
    onSuccess: (res, values) => {
      if (res.temp_password) setTempCredential({ email: values.email, password: res.temp_password });
      else toast.push(t("teacher.students.studentCreated"), "success");
      studentForm.reset();
    },
    onError: (err: any) => {
      if (err?.status === 403) toast.push(permissionDeniedMessage(t("teacher.students.permissionDeniedStudents")), "error");
      else toast.push(t("teacher.students.createStudentFailed"), "error");
    },
  });

  const parentForm = useForm<ParentForm>({
    resolver: zodResolver(parentSchema),
    defaultValues: { name: "", email: "", student_id: "" },
  });
  const createParent = useMutation({
    mutationFn: (values: ParentForm) => teacherApi.createParent(values),
    onSuccess: (res, values) => {
      if (res.temp_password) setTempCredential({ email: values.email, password: res.temp_password });
      else toast.push(t("teacher.students.parentCreated"), "success");
      parentForm.reset();
    },
    onError: (err: any) => {
      if (err?.status === 403) toast.push(permissionDeniedMessage(t("teacher.students.permissionDeniedParents")), "error");
      else toast.push(t("teacher.students.createParentFailed"), "error");
    },
  });

  return (
    <div>
      <PageTitle subtitle={t("teacher.students.subtitle")}>
        {t("teacher.students.title")}
      </PageTitle>

      <Card className="mb-6">
        <CardHeader title={t("teacher.students.addStudent")} />
        <form
          className="p-5 grid md:grid-cols-4 gap-3 items-start"
          onSubmit={studentForm.handleSubmit((v) => createStudent.mutateAsync(v))}
        >
          <FormField label={t("teacher.students.name")} error={errMsg(studentForm.formState.errors.name?.message)}>
            <Input invalid={!!studentForm.formState.errors.name} {...studentForm.register("name")} />
          </FormField>
          <FormField label={t("teacher.students.email")} error={errMsg(studentForm.formState.errors.email?.message)}>
            <Input type="email" invalid={!!studentForm.formState.errors.email} {...studentForm.register("email")} />
          </FormField>
          <FormField label={t("teacher.students.grade")} error={errMsg(studentForm.formState.errors.grade?.message)} optional>
            <Input type="number" {...studentForm.register("grade")} />
          </FormField>
          <Button type="submit" disabled={createStudent.isPending} className="mt-6">
            {createStudent.isPending ? t("teacher.students.adding") : t("teacher.students.addStudentBtn")}
          </Button>
        </form>
      </Card>

      <Card>
        <CardHeader title={t("teacher.students.addParent")} subtitle={t("teacher.students.addParentSubtitle")} />
        <form
          className="p-5 grid md:grid-cols-4 gap-3 items-start"
          onSubmit={parentForm.handleSubmit((v) => createParent.mutateAsync(v))}
        >
          <FormField label={t("teacher.students.name")} error={errMsg(parentForm.formState.errors.name?.message)}>
            <Input invalid={!!parentForm.formState.errors.name} {...parentForm.register("name")} />
          </FormField>
          <FormField label={t("teacher.students.email")} error={errMsg(parentForm.formState.errors.email?.message)}>
            <Input type="email" invalid={!!parentForm.formState.errors.email} {...parentForm.register("email")} />
          </FormField>
          <FormField label={t("teacher.students.studentId")} error={errMsg(parentForm.formState.errors.student_id?.message)}>
            <Input invalid={!!parentForm.formState.errors.student_id} {...parentForm.register("student_id")} />
          </FormField>
          <Button type="submit" disabled={createParent.isPending} className="mt-6">
            {createParent.isPending ? t("teacher.students.adding") : t("teacher.students.addParentBtn")}
          </Button>
        </form>
      </Card>

      <TempCredentialModal credential={tempCredential} onClose={() => setTempCredential(null)} />
    </div>
  );
}
