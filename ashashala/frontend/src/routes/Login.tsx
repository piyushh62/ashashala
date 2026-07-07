import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "../stores/auth";
import { HOME_FOR } from "../components/layout/RoleGuard";
import { Button, Card, Input } from "../components/ui";
import { FormField } from "../components/ui/FormField";
import { useToast } from "../components/ui/Toast";

const loginSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const submit = async ({ email, password }: LoginForm) => {
    try {
      await login(email, password);
      const role = useAuth.getState().user!.role;
      navigate(HOME_FOR[role], { replace: true });
    } catch {
      toast.push("Invalid email or password.", "error");
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Brand hero */}
      <div className="hidden lg:flex flex-col justify-between p-12 bg-gradient-to-br from-brand-600 via-brand-700 to-violet-700 text-white relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-white/10 blur-2xl" />
        <div className="absolute bottom-0 -left-20 w-80 h-80 rounded-full bg-violet-400/20 blur-2xl" />
        <div className="flex items-center gap-3 relative">
          <div className="w-11 h-11 rounded-2xl bg-white/15 backdrop-blur grid place-items-center text-2xl font-bold">
            अ
          </div>
          <span className="text-xl font-bold">AshaShala</span>
        </div>
        <div className="relative">
          <h1 className="text-4xl font-bold leading-tight">
            A patient AI tutor
            <br />
            for every student.
          </h1>
          <p className="mt-4 text-white/80 max-w-md">
            Cited answers, example-first teaching, and native Gujarati &amp; Hindi — with the tools
            to run a whole school.
          </p>
          <div className="mt-8 flex flex-wrap gap-2">
            {["📚 Cited answers", "🗣️ Voice in Gujarati", "🧠 Adaptive quizzes", "🔒 Tenant-isolated"].map(
              (t) => (
                <span key={t} className="text-sm bg-white/10 rounded-full px-3 py-1 backdrop-blur">
                  {t}
                </span>
              ),
            )}
          </div>
        </div>
        <div className="relative text-white/60 text-sm">Free, open-source, self-hostable.</div>
      </div>

      {/* Form */}
      <div className="flex items-center justify-center p-6">
        <Card className="w-full max-w-sm p-8 animate-slide-up">
          <div className="lg:hidden flex items-center gap-2 justify-center mb-6">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-brand-500 to-violet-500 text-white grid place-items-center font-bold">
              अ
            </div>
            <span className="text-lg font-bold text-brand-700">AshaShala</span>
          </div>
          <h2 className="text-xl font-bold text-slate-800">Welcome back</h2>
          <p className="text-sm text-slate-500 mb-6">Sign in to continue.</p>

          <form onSubmit={handleSubmit(submit)} className="space-y-4">
            <FormField label="Email" error={errors.email?.message}>
              <Input
                type="email"
                autoComplete="username"
                placeholder="you@school.org"
                invalid={!!errors.email}
                {...register("email")}
              />
            </FormField>
            <FormField label="Password" error={errors.password?.message}>
              <Input
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                invalid={!!errors.password}
                {...register("password")}
              />
            </FormField>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Signing in…" : "Sign in →"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
