import { useTranslation } from "react-i18next";
import { Button } from "./index";

/**
 * Pager — shared server-side (offset/limit) pagination control. Every list that
 * pages through a `Page<T>` endpoint uses this so the range label and prev/next
 * behavior stay identical across the app.
 */
export function Pager({
  offset,
  limit,
  total,
  count,
  onOffsetChange,
  className = "",
}: {
  /** current offset (rows skipped) */
  offset: number;
  /** page size */
  limit: number;
  /** total rows available on the server */
  total: number;
  /** rows returned in the current page */
  count: number;
  onOffsetChange: (next: number) => void;
  className?: string;
}) {
  const { t } = useTranslation();
  if (total <= 0) return null;

  const rangeStart = offset + 1;
  const rangeEnd = offset + count;

  return (
    <div
      className={`flex items-center justify-between px-3 py-3 text-sm text-slate-500 dark:text-slate-400 ${className}`}
    >
      <span>{t("common.rangeOfTotal", { start: rangeStart, end: rangeEnd, total })}</span>
      <div className="flex gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onOffsetChange(Math.max(0, offset - limit))}
          disabled={offset === 0}
        >
          {t("common.previous")}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onOffsetChange(offset + limit)}
          disabled={rangeEnd >= total}
        >
          {t("common.next")}
        </Button>
      </div>
    </div>
  );
}
