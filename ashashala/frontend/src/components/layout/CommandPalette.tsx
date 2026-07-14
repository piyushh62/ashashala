import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Command } from "cmdk";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Icon } from "../ui";
import type { NavItem } from "./AppLayout";

export interface SearchSource<T> {
  /** Group heading shown above the results, e.g. "Users". */
  label: string;
  queryKey: string[];
  queryFn: () => Promise<T[]>;
  /** Turn one result row into a labelled, navigable entry. */
  toItem: (row: T) => { id: string; label: string; sublabel?: string; to: string };
}

export function CommandPalette({
  nav,
  searchSource,
  open,
  onOpenChange,
}: {
  nav: NavItem[];
  searchSource?: SearchSource<any>;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const search = useQuery({
    queryKey: searchSource ? ["command-palette", ...searchSource.queryKey] : ["command-palette", "disabled"],
    queryFn: () => searchSource!.queryFn(),
    enabled: open && !!searchSource,
  });

  const go = (to: string) => {
    onOpenChange(false);
    navigate(to);
  };

  const entityItems = useMemo(() => {
    if (!searchSource || !search.data) return [];
    return search.data.map(searchSource.toItem);
  }, [searchSource, search.data]);

  return (
    <Command.Dialog
      open={open}
      onOpenChange={onOpenChange}
      label={t("common.globalSearch")}
      shouldFilter
      className="fixed z-50 left-1/2 top-24 -translate-x-1/2 w-[calc(100%-2rem)] max-w-lg bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/70 dark:border-slate-700 shadow-soft overflow-hidden data-[state=open]:animate-pop-in"
      overlayClassName="fixed inset-0 bg-slate-900/40 backdrop-blur-[2px] z-40 data-[state=open]:animate-fade-in"
    >
      <div className="flex items-center gap-2 px-4 border-b border-slate-100 dark:border-slate-700">
        <Icon name="search" className="w-4 h-4 text-slate-400" />
        <Command.Input
          value={query}
          onValueChange={setQuery}
          placeholder={t("common.searchPlaceholder")}
          className="flex-1 bg-transparent py-3 text-sm text-slate-800 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none"
        />
        <kbd className="hidden sm:block text-[10px] font-medium text-slate-400 border border-slate-200 dark:border-slate-700 rounded px-1.5 py-0.5">
          Esc
        </kbd>
      </div>
      <Command.List className="max-h-80 overflow-y-auto p-2">
        <Command.Empty className="py-8 text-center text-sm text-slate-400">{t("common.noResultsFound")}</Command.Empty>

        <Command.Group heading={t("common.navigate")} className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pt-2 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wide [&_[cmdk-group-heading]]:text-slate-400">
          {nav.map((n) => (
            <Command.Item
              key={n.to}
              value={`nav-${n.label}`}
              onSelect={() => go(n.to)}
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm cursor-pointer text-slate-700 dark:text-slate-200 data-[selected=true]:bg-slate-100 dark:data-[selected=true]:bg-slate-800"
            >
              <span className="w-5 grid place-items-center">
                <Icon name={n.icon} className="w-4 h-4" />
              </span>
              {n.label}
            </Command.Item>
          ))}
        </Command.Group>

        {searchSource && entityItems.length > 0 && (
          <Command.Group heading={searchSource.label} className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pt-3 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wide [&_[cmdk-group-heading]]:text-slate-400">
            {entityItems.map((item) => (
              <Command.Item
                key={item.id}
                value={`${searchSource.label}-${item.label}-${item.id}`}
                onSelect={() => go(item.to)}
                className="flex flex-col items-start px-3 py-2 rounded-lg text-sm cursor-pointer text-slate-700 dark:text-slate-200 data-[selected=true]:bg-slate-100 dark:data-[selected=true]:bg-slate-800"
              >
                <span>{item.label}</span>
                {item.sublabel && <span className="text-xs text-slate-400">{item.sublabel}</span>}
              </Command.Item>
            ))}
          </Command.Group>
        )}
      </Command.List>
    </Command.Dialog>
  );
}
