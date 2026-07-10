import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { authApi, parentApi } from "../api/endpoints";
import { useAuth } from "../stores/auth";
import { PageTitle } from "../components/layout/AppLayout";
import { Avatar, Badge, Button, Card, CardHeader, Input, Skeleton } from "../components/ui";
import { FormField } from "../components/ui/FormField";
import { ThemeToggle } from "../components/ui/ThemeToggle";
import { useTheme } from "../stores/theme";
import { useToast } from "../components/ui/Toast";
import type { NotificationPreferenceOut } from "../types/api";

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

        {user.role === "parent" && <NotificationPreferencesCard />}
      </div>
    </div>
  );
}

const PREF_LABELS: { key: keyof NotificationPreferenceOut; label: string; hint: string }[] = [
  { key: "in_app_enabled", label: "In-app", hint: "Notifications inside AshaShala." },
  { key: "sms_enabled", label: "SMS", hint: "Text messages for important updates." },
  { key: "whatsapp_enabled", label: "WhatsApp", hint: "WhatsApp messages, where available." },
  { key: "email_enabled", label: "Email", hint: "Email summaries and alerts." },
];

function NotificationPreferencesCard() {
  const toast = useToast();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["parent", "notification-preferences"], queryFn: parentApi.notificationPreferences });

  const update = useMutation({
    mutationFn: (body: Partial<NotificationPreferenceOut>) => parentApi.updateNotificationPreferences(body),
    onSuccess: (data) => qc.setQueryData(["parent", "notification-preferences"], data),
    onError: () => toast.push("Couldn't update notification preferences.", "error"),
  });

  return (
    <Card>
      <CardHeader title="Notification preferences" subtitle="Choose how you'd like to hear from AshaShala." />
      <div className="p-5 space-y-4">
        {q.isLoading ? (
          <Skeleton className="h-24" />
        ) : (
          PREF_LABELS.map(({ key, label, hint }) => (
            <div key={key} className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-slate-700 dark:text-slate-200">{label}</div>
                <div className="text-xs text-slate-400 mt-0.5">{hint}</div>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={!!q.data?.[key]}
                onClick={() => update.mutate({ [key]: !q.data?.[key] })}
                disabled={update.isPending}
                className={`relative w-11 h-6 rounded-full transition ${
                  q.data?.[key] ? "bg-brand-600" : "bg-slate-200 dark:bg-slate-700"
                } disabled:opacity-50`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                    q.data?.[key] ? "translate-x-5" : ""
                  }`}
                />
              </button>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
