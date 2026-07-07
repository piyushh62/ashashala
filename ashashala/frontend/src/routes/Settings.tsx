import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { authApi } from "../api/endpoints";
import { useAuth } from "../stores/auth";
import { PageTitle } from "../components/layout/AppLayout";
import { Avatar, Badge, Button, Card, CardHeader, Input } from "../components/ui";
import { FormField } from "../components/ui/FormField";
import { ThemeToggle } from "../components/ui/ThemeToggle";
import { useTheme } from "../stores/theme";
import { useToast } from "../components/ui/Toast";

const ROLE_LABEL: Record<string, string> = {
  super_admin: "Super Admin",
  school_admin: "School Admin",
  teacher: "Teacher",
  student: "Student",
  parent: "Parent",
};

const passwordSchema = z
  .object({
    newPassword: z.string().min(8, "Must be at least 8 characters"),
    confirmPassword: z.string().min(1, "Please confirm your new password"),
  })
  .refine((v) => v.newPassword === v.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

type PasswordForm = z.infer<typeof passwordSchema>;

export default function Settings() {
  const user = useAuth((s) => s.user)!;
  const toast = useToast();
  const themeMode = useTheme((s) => s.mode);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PasswordForm>({ resolver: zodResolver(passwordSchema) });

  const changePassword = useMutation({
    mutationFn: (values: PasswordForm) => authApi.passwordReset(user.email, values.newPassword),
    onSuccess: () => {
      toast.push("Password updated.", "success");
      reset();
    },
    onError: () => toast.push("Couldn't update password. Try again.", "error"),
  });

  return (
    <div>
      <PageTitle subtitle="Manage your profile and account security.">Settings</PageTitle>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Profile" subtitle="Your account details." />
          <div className="p-5 space-y-5">
            <div className="flex items-center gap-4">
              <Avatar name={user.name} size={56} />
              <div className="min-w-0">
                <div className="font-semibold text-slate-800 truncate">{user.name}</div>
                <div className="text-sm text-slate-500 truncate">{user.email}</div>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge tone="brand">{ROLE_LABEL[user.role] || user.role}</Badge>
              {user.grade != null && <Badge tone="slate">Grade {user.grade}</Badge>}
            </div>
            {user.interests && (
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1">Interests</div>
                <p className="text-sm text-slate-600">{user.interests}</p>
              </div>
            )}
            <p className="text-xs text-slate-400">
              Profile details are managed by your school administrator and can't be edited here.
            </p>
          </div>
        </Card>

        <Card>
          <CardHeader title="Change password" subtitle="Update the password used to sign in." />
          <form
            className="p-5 space-y-4"
            onSubmit={handleSubmit((values) => changePassword.mutateAsync(values))}
          >
            <FormField label="New password" error={errors.newPassword?.message}>
              <Input type="password" invalid={!!errors.newPassword} {...register("newPassword")} />
            </FormField>
            <FormField label="Confirm new password" error={errors.confirmPassword?.message}>
              <Input type="password" invalid={!!errors.confirmPassword} {...register("confirmPassword")} />
            </FormField>
            <Button type="submit" disabled={isSubmitting || changePassword.isPending}>
              {changePassword.isPending ? "Updating…" : "Update password"}
            </Button>
          </form>
        </Card>

        <Card>
          <CardHeader title="Appearance" subtitle="Choose how AshaShala looks on this device." />
          <div className="p-5 flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-slate-700 dark:text-slate-200">Theme</div>
              <div className="text-xs text-slate-400 mt-0.5">
                Currently {themeMode === "dark" ? "dark" : "light"} mode
              </div>
            </div>
            <ThemeToggle className="border border-slate-200 dark:border-slate-700" />
          </div>
        </Card>
      </div>
    </div>
  );
}
