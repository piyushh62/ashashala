import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { notificationsApi } from "../../api/endpoints";
import type { Notification } from "../../types/api";
import { PopoverPanel } from "../ui/Dropdown";
import { Icon } from "../ui";

function timeAgo(iso: string, t: (key: string, opts?: Record<string, unknown>) => string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return t("common.justNow");
  if (mins < 60) return t("common.minutesAgo", { count: mins });
  const hours = Math.floor(mins / 60);
  if (hours < 24) return t("common.hoursAgo", { count: hours });
  const days = Math.floor(hours / 24);
  return t("common.daysAgo", { count: days });
}

export function NotificationBell() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationsApi.list(),
    refetchInterval: 30_000,
  });

  const markRead = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const markAllRead = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const items = data?.items ?? [];
  const unreadCount = data?.unread_count ?? 0;

  const handleClick = (n: Notification) => {
    if (!n.is_read) markRead.mutate(n.id);
    if (n.link) navigate(n.link);
  };

  return (
    <PopoverPanel
      align="end"
      className="w-80 max-h-[26rem] flex flex-col"
      trigger={
        <button
          aria-label={t("common.notifications")}
          className="relative w-9 h-9 grid place-items-center rounded-full text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800 transition"
        >
          <Icon name="bell" className="w-[18px] h-[18px]" />
          {unreadCount > 0 && (
            <span className="absolute top-1 right-1 min-w-[16px] h-4 px-1 rounded-full bg-rose-500 text-white text-[10px] font-semibold grid place-items-center">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </button>
      }
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-slate-700 shrink-0">
        <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-100">{t("common.notifications")}</h3>
        {unreadCount > 0 && (
          <button
            onClick={() => markAllRead.mutate()}
            className="text-xs font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400"
          >
            {t("common.markAllRead")}
          </button>
        )}
      </div>
      <div className="overflow-y-auto flex-1">
        {items.length === 0 ? (
          <div className="text-center py-10 px-4 text-sm text-slate-400 dark:text-slate-500">
            {t("common.allCaughtUp")}
          </div>
        ) : (
          items.map((n) => (
            <button
              key={n.id}
              onClick={() => handleClick(n)}
              className={`w-full text-left px-4 py-3 border-b border-slate-50 dark:border-slate-800 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800 transition ${
                !n.is_read ? "bg-brand-50/40 dark:bg-brand-900/10" : ""
              }`}
            >
              <div className="flex items-start gap-2">
                {!n.is_read && <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-brand-500 shrink-0" />}
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">{n.title}</div>
                  {n.body && (
                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">{n.body}</div>
                  )}
                  <div className="text-[11px] text-slate-400 dark:text-slate-500 mt-1">{timeAgo(n.created_at, t)}</div>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </PopoverPanel>
  );
}
