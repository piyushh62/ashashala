import type { ReactNode } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as Popover from "@radix-ui/react-popover";

/* ---------------------------------------------------------------------------
 * Dropdown — action menu (user menu, row actions, filters).
 * ------------------------------------------------------------------------- */

export function Dropdown({
  trigger,
  children,
  align = "end",
}: {
  trigger: ReactNode;
  children: ReactNode;
  align?: "start" | "center" | "end";
}) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>{trigger}</DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align={align}
          sideOffset={8}
          className="z-50 min-w-[200px] bg-white dark:bg-slate-900 rounded-xl border border-slate-200/70 dark:border-slate-800 shadow-soft p-1.5 data-[state=open]:animate-pop-in focus:outline-none"
        >
          {children}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

export function DropdownItem({
  children,
  onSelect,
  danger = false,
  disabled = false,
}: {
  children: ReactNode;
  onSelect?: () => void;
  danger?: boolean;
  disabled?: boolean;
}) {
  return (
    <DropdownMenu.Item
      onSelect={onSelect}
      disabled={disabled}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm cursor-pointer outline-none transition data-[highlighted]:bg-slate-50 dark:data-[highlighted]:bg-slate-800 ${
        danger ? "text-rose-600 dark:text-rose-400 data-[highlighted]:bg-rose-50 dark:data-[highlighted]:bg-rose-500/10" : "text-slate-700 dark:text-slate-200"
      } ${disabled ? "opacity-40 cursor-not-allowed" : ""}`}
    >
      {children}
    </DropdownMenu.Item>
  );
}

export function DropdownLabel({ children }: { children: ReactNode }) {
  return <div className="px-3 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">{children}</div>;
}

export function DropdownSeparator() {
  return <DropdownMenu.Separator className="h-px bg-slate-100 dark:bg-slate-800 my-1.5" />;
}

/* ---------------------------------------------------------------------------
 * PopoverPanel — for richer floating content (notification list, filters
 * with multiple controls) where a plain menu item list isn't enough.
 * ------------------------------------------------------------------------- */

export function PopoverPanel({
  trigger,
  children,
  align = "end",
  className = "",
}: {
  trigger: ReactNode;
  children: ReactNode;
  align?: "start" | "center" | "end";
  className?: string;
}) {
  return (
    <Popover.Root>
      <Popover.Trigger asChild>{trigger}</Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align={align}
          sideOffset={8}
          className={`z-50 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/70 dark:border-slate-800 shadow-soft data-[state=open]:animate-pop-in focus:outline-none ${className}`}
        >
          {children}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
