import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, Input } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { Modal } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";

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

function permissionDeniedMessage(action: string) {
  return `Your school hasn't granted you permission to create ${action} yet — ask your school admin to enable it under Roles.`;
}

export default function TeacherStudents() {
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
      else toast.push("Student created.", "success");
      studentForm.reset();
    },
    onError: (err: any) => {
      if (err?.status === 403) toast.push(permissionDeniedMessage("students"), "error");
      else toast.push("Couldn't create student (email may be taken).", "error");
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
      else toast.push("Parent created and linked.", "success");
      parentForm.reset();
    },
    onError: (err: any) => {
      if (err?.status === 403) toast.push(permissionDeniedMessage("parents"), "error");
      else toast.push("Couldn't create parent (email or student ID may be invalid).", "error");
    },
  });

  return (
    <div>
      <PageTitle subtitle="Create students and parents directly, if your school admin has enabled it.">
        Students
      </PageTitle>

      <Card className="mb-6">
        <CardHeader title="Add a student" />
        <form
          className="p-5 grid md:grid-cols-4 gap-3 items-start"
          onSubmit={studentForm.handleSubmit((v) => createStudent.mutateAsync(v))}
        >
          <FormField label="Name" error={studentForm.formState.errors.name?.message}>
            <Input invalid={!!studentForm.formState.errors.name} {...studentForm.register("name")} />
          </FormField>
          <FormField label="Email" error={studentForm.formState.errors.email?.message}>
            <Input type="email" invalid={!!studentForm.formState.errors.email} {...studentForm.register("email")} />
          </FormField>
          <FormField label="Grade" error={studentForm.formState.errors.grade?.message} optional>
            <Input type="number" {...studentForm.register("grade")} />
          </FormField>
          <Button type="submit" disabled={createStudent.isPending} className="mt-6">
            {createStudent.isPending ? "Adding…" : "Add student"}
          </Button>
        </form>
      </Card>

      <Card>
        <CardHeader title="Add a parent" subtitle="Links the parent to an existing student by ID." />
        <form
          className="p-5 grid md:grid-cols-4 gap-3 items-start"
          onSubmit={parentForm.handleSubmit((v) => createParent.mutateAsync(v))}
        >
          <FormField label="Name" error={parentForm.formState.errors.name?.message}>
            <Input invalid={!!parentForm.formState.errors.name} {...parentForm.register("name")} />
          </FormField>
          <FormField label="Email" error={parentForm.formState.errors.email?.message}>
            <Input type="email" invalid={!!parentForm.formState.errors.email} {...parentForm.register("email")} />
          </FormField>
          <FormField label="Student ID" error={parentForm.formState.errors.student_id?.message}>
            <Input invalid={!!parentForm.formState.errors.student_id} {...parentForm.register("student_id")} />
          </FormField>
          <Button type="submit" disabled={createParent.isPending} className="mt-6">
            {createParent.isPending ? "Adding…" : "Add parent"}
          </Button>
        </form>
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
                <Button type="button" variant="ghost" size="sm" onClick={() => navigator.clipboard.writeText(tempCredential.password)}>
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
    </div>
  );
}
