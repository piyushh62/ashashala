import { useState } from "react";
import { DayPicker } from "react-day-picker";
import * as Popover from "@radix-ui/react-popover";
import { format, parseISO, isValid } from "date-fns";
import { Icon } from "./icons";
import { cn } from "../../lib/cn";

/**
 * DatePicker — a calendar popover that reads and writes ISO date strings
 * (yyyy-MM-dd), so it is a drop-in replacement for `<Input type="date">`
 * throughout the app (exam timetable, absence dates, admissions, ...).
 * Built on react-day-picker + the Radix popover already used elsewhere.
 */
export function DatePicker({
  value,
  onChange,
  placeholder = "Select a date",
  disabled = false,
  fromYear,
  toYear,
  className = "",
}: {
  value: string;
  onChange: (iso: string) => void;
  placeholder?: string;
  disabled?: boolean;
  fromYear?: number;
  toYear?: number;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const selected = value ? parseISO(value) : undefined;
  const label = selected && isValid(selected) ? format(selected, "d MMM yyyy") : "";

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          disabled={disabled}
          className={cn(
            "w-full flex items-center justify-between gap-2 px-3.5 py-2.5 rounded-xl border border-slate-300 bg-white text-sm text-left transition focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400 dark:bg-slate-900 dark:border-slate-700 dark:focus:ring-brand-500/20 dark:focus:border-brand-500 disabled:opacity-50 disabled:cursor-not-allowed",
            label ? "text-slate-800 dark:text-slate-100" : "text-slate-400",
            className,
          )}
        >
          <span className="truncate">{label || placeholder}</span>
          <Icon name="calendar" className="w-4 h-4 shrink-0 text-slate-400" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="start"
          sideOffset={8}
          className="z-50 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/70 dark:border-slate-800 shadow-soft p-2 data-[state=open]:animate-pop-in focus:outline-none"
        >
          <DayPicker
            mode="single"
            selected={selected}
            defaultMonth={selected}
            captionLayout={fromYear || toYear ? "dropdown-buttons" : undefined}
            fromYear={fromYear}
            toYear={toYear}
            onSelect={(day) => {
              if (day) {
                onChange(format(day, "yyyy-MM-dd"));
                setOpen(false);
              }
            }}
            classNames={{
              day_selected: "!bg-brand-600 !text-white",
              day_today: "font-bold text-brand-600",
            }}
          />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
