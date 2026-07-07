import type { ReactNode } from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";

export interface TabItem {
  value: string;
  label: string;
  icon?: ReactNode;
}

export function Tabs({
  items,
  value,
  onChange,
  children,
}: {
  items: TabItem[];
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  return (
    <TabsPrimitive.Root value={value} onValueChange={onChange}>
      <TabsPrimitive.List className="flex gap-1 p-1 bg-slate-100 rounded-xl w-fit mb-4">
        {items.map((t) => (
          <TabsPrimitive.Trigger
            key={t.value}
            value={t.value}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium text-slate-500 transition data-[state=active]:bg-white data-[state=active]:text-brand-700 data-[state=active]:shadow-card outline-none"
          >
            {t.icon}
            {t.label}
          </TabsPrimitive.Trigger>
        ))}
      </TabsPrimitive.List>
      {children}
    </TabsPrimitive.Root>
  );
}

export function TabPanel({ value, children }: { value: string; children: ReactNode }) {
  return (
    <TabsPrimitive.Content value={value} className="animate-fade-in outline-none">
      {children}
    </TabsPrimitive.Content>
  );
}
