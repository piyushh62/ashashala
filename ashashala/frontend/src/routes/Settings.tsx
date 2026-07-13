import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { authApi, parentApi } from "../api/endpoints";
import { useAuth } from "../stores/auth";
import { PageTitle } from "../components/layout/AppLayout";
import { Avatar, Badge, Button, Card, CardHeader, Input, Select, Skeleton } from "../components/ui";
import { FormField } from "../components/ui/FormField";
import { ThemeToggle } from "../components/ui/ThemeToggle";
import { useTheme } from "../stores/theme";
import { useLocale } from "../stores/locale";
import { SUPPORTED_LOCALES, type Locale } from "../i18n";
import { useToast } from "../components/ui/Toast";
import type { NotificationPreferenceOut } from "../types/api";

const ROLE_LABEL_KEY: Record<string, string> = {
  super_admin: "roleTitle.superAdmin",
  school_admin: "roleTitle.schoolAdmin",
  teacher: "roleTitle.teacher",
  student: "roleTitle.student",
  parent: "roleTitle.parent",
};

const LOCALE_LABEL: Record<Locale, string> = {
  en: "English",
  hi: "हिन्दी",
  gu: "ગુજરાતી",
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
  const { t } = useTranslation();
  const user = useAuth((s) => s.user)!;
  const toast = useToast();
  const themeMode = useTheme((s) => s.mode);
  const locale = useLocale((s) => s.locale);
  const setLocale = useLocale((s) => s.setLocale);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PasswordForm>({ resolver: zodResolver(passwordSchema) });

  const changePassword = useMutation({
    mutationFn: (values: PasswordForm) => authApi.passwordReset(user.email, values.newPassword),
    onSuccess: () => {
      toast.push(t("settings.passwordUpdated"), "success");
      reset();
    },
    onError: () => toast.push(t("settings.passwordUpdateFailed"), "error"),
  });

  return (
    <div>
      <PageTitle subtitle={t("settings.subtitle")}>{t("settings.title")}</PageTitle>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title={t("settings.profileTitle")} subtitle={t("settings.profileSubtitle")} />
          <div className="p-5 space-y-5">
            <div className="flex items-center gap-4">
              <Avatar name={user.name} size={56} />
              <div className="min-w-0">
                <div className="font-semibold text-slate-800 truncate">{user.name}</div>
                <div className="text-sm text-slate-500 truncate">{user.email}</div>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge tone="brand">{ROLE_LABEL_KEY[user.role] ? t(ROLE_LABEL_KEY[user.role]) : user.role}</Badge>
              {user.grade != null && <Badge tone="slate">{t("settings.grade", { grade: user.grade })}</Badge>}
            </div>
            {user.interests && (
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1">{t("settings.interests")}</div>
                <p className="text-sm text-slate-600">{user.interests}</p>
              </div>
            )}
            <p className="text-xs text-slate-400">{t("settings.profileLocked")}</p>
          </div>
        </Card>

        <Card>
          <CardHeader title={t("settings.passwordTitle")} subtitle={t("settings.passwordSubtitle")} />
          <form
            className="p-5 space-y-4"
            onSubmit={handleSubmit((values) => changePassword.mutateAsync(values))}
          >
            <FormField label={t("settings.newPassword")} error={errors.newPassword?.message}>
              <Input type="password" invalid={!!errors.newPassword} {...register("newPassword")} />
            </FormField>
            <FormField label={t("settings.confirmPassword")} error={errors.confirmPassword?.message}>
              <Input type="password" invalid={!!errors.confirmPassword} {...register("confirmPassword")} />
            </FormField>
            <Button type="submit" disabled={isSubmitting || changePassword.isPending}>
              {changePassword.isPending ? t("settings.updating") : t("settings.updatePassword")}
            </Button>
          </form>
        </Card>

        <Card>
          <CardHeader title={t("settings.appearanceTitle")} subtitle={t("settings.appearanceSubtitle")} />
          <div className="p-5 flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-slate-700 dark:text-slate-200">{t("settings.theme")}</div>
              <div className="text-xs text-slate-400 mt-0.5">
                {themeMode === "dark" ? t("settings.currentlyDark") : t("settings.currentlyLight")}
              </div>
            </div>
            <ThemeToggle className="border border-slate-200 dark:border-slate-700" />
          </div>
        </Card>

        <Card>
          <CardHeader title={t("settings.languageTitle")} subtitle={t("settings.languageSubtitle")} />
          <div className="p-5">
            <Select value={locale} onChange={(e) => setLocale(e.target.value as Locale)}>
              {SUPPORTED_LOCALES.map((l) => (
                <option key={l} value={l}>
                  {LOCALE_LABEL[l]}
                </option>
              ))}
            </Select>
          </div>
        </Card>

        {user.role === "parent" && <NotificationPreferencesCard />}
      </div>
    </div>
  );
}

function NotificationPreferencesCard() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["parent", "notification-preferences"], queryFn: parentApi.notificationPreferences });

  const PREF_LABELS: { key: keyof NotificationPreferenceOut; label: string; hint: string }[] = [
    { key: "in_app_enabled", label: t("settings.notifInApp"), hint: t("settings.notifInAppHint") },
    { key: "sms_enabled", label: t("settings.notifSms"), hint: t("settings.notifSmsHint") },
    { key: "whatsapp_enabled", label: t("settings.notifWhatsapp"), hint: t("settings.notifWhatsappHint") },
    { key: "email_enabled", label: t("settings.notifEmail"), hint: t("settings.notifEmailHint") },
  ];

  const update = useMutation({
    mutationFn: (body: Partial<NotificationPreferenceOut>) => parentApi.updateNotificationPreferences(body),
    onSuccess: (data) => qc.setQueryData(["parent", "notification-preferences"], data),
    onError: () => toast.push(t("settings.notifPrefUpdateFailed"), "error"),
  });

  return (
    <Card>
      <CardHeader title={t("settings.notifPrefTitle")} subtitle={t("settings.notifPrefSubtitle")} />
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
