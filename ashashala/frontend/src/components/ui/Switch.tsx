import * as SwitchPrimitive from "@radix-ui/react-switch";
import { cn } from "../../lib/cn";

/**
 * Accessible on/off toggle built on Radix Switch. Use for plain boolean state
 * that doesn't need a confirmation step (e.g. notification preferences).
 * For destructive/consequential toggles (suspend a school, deactivate a user),
 * keep using a Button + confirm dialog instead.
 */
export function Switch({
  checked,
  onCheckedChange,
  disabled,
  label,
  className,
}: {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
  className?: string;
}) {
  return (
    <SwitchPrimitive.Root
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      aria-label={label}
      className={cn(
        "relative w-11 h-6 rounded-full transition data-[state=checked]:bg-brand-600 data-[state=unchecked]:bg-slate-200 dark:data-[state=unchecked]:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-300 dark:focus-visible:ring-brand-500/40",
        className,
      )}
    >
      <SwitchPrimitive.Thumb className="block w-5 h-5 rounded-full bg-white shadow translate-x-0.5 transition-transform data-[state=checked]:translate-x-5" />
    </SwitchPrimitive.Root>
  );
}
