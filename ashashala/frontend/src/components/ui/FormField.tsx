import type { ReactNode } from "react";
import { Label } from "./index";

/**
 * FormField — label + control + inline error, the standard wrapper for every
 * react-hook-form field. Pairs with `register("name")` and
 * `formState.errors.name?.message`.
 */
export function FormField({
  label,
  error,
  hint,
  children,
  optional = false,
}: {
  label: string;
  error?: string;
  hint?: string;
  children: ReactNode;
  optional?: boolean;
}) {
  return (
    <div>
      <Label>
        {label}
        {optional && <span className="ml-1 normal-case font-normal text-slate-400">(optional)</span>}
      </Label>
      {children}
      {error ? (
        <p className="text-xs text-rose-600 mt-1.5 flex items-center gap-1">
          <span aria-hidden>⚠</span> {error}
        </p>
      ) : (
        hint && <p className="text-xs text-slate-400 mt-1.5">{hint}</p>
      )}
    </div>
  );
}
