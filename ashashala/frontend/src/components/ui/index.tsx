import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
} from "react";

/* ---------------------------------- Card --------------------------------- */

export function Card({
  children,
  className = "",
  hover = false,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return (
    <div
      className={`bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/70 dark:border-slate-800 shadow-card ${
        hover ? "transition hover:shadow-soft hover:border-brand-200 dark:hover:border-brand-800" : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
  icon,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-slate-100 dark:border-slate-800">
      <div className="flex items-center gap-3 min-w-0">
        {icon && (
          <div className="w-9 h-9 rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/10 dark:text-brand-400 grid place-items-center text-lg shrink-0">
            {icon}
          </div>
        )}
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-800 dark:text-slate-100 truncate">{title}</h3>
          {subtitle && <p className="text-sm text-slate-500 dark:text-slate-400 truncate">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

/* -------------------------------- Button --------------------------------- */

interface BtnProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "danger" | "subtle";
  size?: "sm" | "md";
}
export function Button({ variant = "primary", size = "md", className = "", ...rest }: BtnProps) {
  const styles: Record<string, string> = {
    primary: "bg-brand-600 hover:bg-brand-700 text-white shadow-sm hover:shadow-pop",
    ghost: "bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300",
    subtle: "bg-brand-50 hover:bg-brand-100 text-brand-700 dark:bg-brand-500/10 dark:hover:bg-brand-500/20 dark:text-brand-300",
    danger: "bg-rose-600 hover:bg-rose-700 text-white shadow-sm",
  };
  const sizes: Record<string, string> = {
    sm: "px-3 py-1.5 text-xs rounded-lg",
    md: "px-4 py-2 text-sm rounded-xl",
  };
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 font-medium transition active:scale-[.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100 ${styles[variant]} ${sizes[size]} ${className}`}
      {...rest}
    />
  );
}

/* --------------------------------- Inputs -------------------------------- */

const fieldCls =
  "w-full px-3.5 py-2.5 rounded-xl border border-slate-300 bg-white text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400 transition dark:bg-slate-900 dark:border-slate-700 dark:text-slate-100 dark:focus:ring-brand-500/20 dark:focus:border-brand-500";
const fieldInvalidCls =
  "border-rose-300 focus:ring-rose-100 focus:border-rose-400 dark:border-rose-700 dark:focus:ring-rose-500/20";

interface FieldExtraProps {
  invalid?: boolean;
}

export function Input({
  className = "",
  invalid = false,
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & FieldExtraProps) {
  return <input className={`${fieldCls} ${invalid ? fieldInvalidCls : ""} ${className}`} {...rest} />;
}

export function Textarea({
  className = "",
  invalid = false,
  ...rest
}: import("react").TextareaHTMLAttributes<HTMLTextAreaElement> & FieldExtraProps) {
  return <textarea className={`${fieldCls} ${invalid ? fieldInvalidCls : ""} ${className}`} {...rest} />;
}

export function Select({
  className = "",
  invalid = false,
  children,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement> & FieldExtraProps) {
  return (
    <select className={`${fieldCls} cursor-pointer ${invalid ? fieldInvalidCls : ""} ${className}`} {...rest}>
      {children}
    </select>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-1.5">{children}</label>;
}

/* ------------------------------ Feedback --------------------------------- */

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm">
      <span className="inline-block w-4 h-4 border-2 border-slate-200 dark:border-slate-700 border-t-brand-600 rounded-full animate-spin" />
      {label}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`relative overflow-hidden bg-slate-100 dark:bg-slate-800 rounded-xl ${className}`}
      aria-hidden
    >
      <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/60 dark:via-slate-700/40 to-transparent animate-[shimmer_1.5s_infinite]" />
    </div>
  );
}

export function EmptyState({ title, hint, icon = "✨" }: { title: string; hint?: string; icon?: ReactNode }) {
  return (
    <div className="text-center py-14 px-6">
      <div className="mx-auto w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 grid place-items-center text-2xl mb-3">{icon}</div>
      <p className="font-semibold text-slate-600 dark:text-slate-300">{title}</p>
      {hint && <p className="text-sm mt-1 text-slate-400">{hint}</p>}
    </div>
  );
}

/* --------------------------------- Table --------------------------------- */

export function Table({ head, children }: { head: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-400 border-b border-slate-100 dark:border-slate-800">
            {head.map((h) => (
              <th key={h} className="px-4 py-2.5 font-semibold text-xs uppercase tracking-wide">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50 dark:divide-slate-800 dark:text-slate-200">{children}</tbody>
      </table>
    </div>
  );
}

/* --------------------------------- Badge --------------------------------- */

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: string }) {
  const tones: Record<string, string> = {
    slate: "bg-slate-100 text-slate-600 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700",
    brand: "bg-brand-50 text-brand-700 ring-brand-200 dark:bg-brand-500/10 dark:text-brand-300 dark:ring-brand-500/30",
    green: "bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-500/30",
    amber: "bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-500/30",
    red: "bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-500/10 dark:text-rose-300 dark:ring-rose-500/30",
    blue: "bg-sky-50 text-sky-700 ring-sky-200 dark:bg-sky-500/10 dark:text-sky-300 dark:ring-sky-500/30",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ring-1 ring-inset ${tones[tone] || tones.slate}`}
    >
      {children}
    </span>
  );
}

/* ------------------------------- StatTile -------------------------------- */

export function StatTile({
  label,
  value,
  icon,
  hint,
  tone = "brand",
}: {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  hint?: ReactNode;
  tone?: "brand" | "green" | "amber" | "rose" | "slate";
}) {
  const iconTones: Record<string, string> = {
    brand: "bg-brand-50 text-brand-600 dark:bg-brand-500/10 dark:text-brand-400",
    green: "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400",
    amber: "bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400",
    rose: "bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400",
    slate: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
  };
  return (
    <Card className="p-5 animate-slide-up">
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</div>
          <div className="text-3xl font-bold text-slate-800 dark:text-slate-100 mt-1 tabular-nums truncate">{value}</div>
          {hint && <div className="text-xs text-slate-400 mt-1">{hint}</div>}
        </div>
        {icon && (
          <div className={`w-10 h-10 rounded-xl grid place-items-center text-xl shrink-0 ${iconTones[tone]}`}>
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}

/* ------------------------------ ProgressBar ------------------------------ */

export function ProgressBar({ value, tone = "brand" }: { value: number; tone?: "brand" | "green" | "amber" }) {
  const bars: Record<string, string> = {
    brand: "bg-brand-500",
    green: "bg-emerald-500",
    amber: "bg-amber-500",
  };
  const v = Math.max(0, Math.min(100, value));
  return (
    <div className="h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
      <div className={`h-full rounded-full transition-all duration-500 ${bars[tone]}`} style={{ width: `${v}%` }} />
    </div>
  );
}

/* -------------------------------- Avatar --------------------------------- */

export function Avatar({ name, size = 36 }: { name: string; size?: number }) {
  const initials = name
    .split(" ")
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <div
      className="rounded-full bg-gradient-to-br from-brand-500 to-violet-500 text-white grid place-items-center font-semibold shrink-0"
      style={{ width: size, height: size, fontSize: size * 0.4 }}
    >
      {initials || "?"}
    </div>
  );
}
