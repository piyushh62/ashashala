import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { Button, EmptyState, Icon, Input, Skeleton } from "./index";

/**
 * DataTable — sortable, filterable, paginated table built on
 * @tanstack/react-table (headless) so every list in the app gets consistent
 * behavior instead of re-implementing sort/filter/pagination per page.
 */
export function DataTable<T>({
  data,
  columns,
  isLoading,
  emptyTitle = "Nothing here yet",
  emptyHint,
  searchPlaceholder = "Search…",
  pageSize = 10,
  toolbar,
}: {
  data: T[];
  columns: ColumnDef<T, any>[];
  isLoading?: boolean;
  emptyTitle?: string;
  emptyHint?: string;
  searchPlaceholder?: string;
  pageSize?: number;
  toolbar?: React.ReactNode;
}) {
  const { t } = useTranslation();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize } },
  });

  if (isLoading) return <Skeleton className="h-64 m-3" />;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 pt-3 pb-2">
        <Input
          value={globalFilter}
          onChange={(e) => table.setGlobalFilter(e.target.value)}
          placeholder={searchPlaceholder}
          className="max-w-xs"
        />
        {toolbar}
      </div>

      {data.length === 0 ? (
        <EmptyState title={emptyTitle} hint={emptyHint} />
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                {table.getHeaderGroups().map((hg) => (
                  <tr key={hg.id} className="text-left text-slate-400 border-b border-slate-100 dark:border-slate-800">
                    {hg.headers.map((h) => (
                      <th
                        key={h.id}
                        onClick={h.column.getToggleSortingHandler()}
                        className={`px-4 py-2.5 font-semibold text-xs uppercase tracking-wide select-none ${
                          h.column.getCanSort() ? "cursor-pointer hover:text-slate-600 dark:hover:text-slate-300" : ""
                        }`}
                      >
                        <span className="inline-flex items-center gap-1">
                          {flexRender(h.column.columnDef.header, h.getContext())}
                          {h.column.getIsSorted() === "asc" && <Icon name="sortAsc" className="w-3.5 h-3.5" />}
                          {h.column.getIsSorted() === "desc" && <Icon name="sortDesc" className="w-3.5 h-3.5" />}
                        </span>
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className="divide-y divide-slate-50 dark:divide-slate-800 dark:text-slate-200">
                {table.getRowModel().rows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length} className="px-4 py-10">
                      <EmptyState title={t("common.noResultsFound")} hint={t("common.searchPlaceholder")} icon={<Icon name="search" className="w-6 h-6" />} />
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <tr key={row.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition">
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-4 py-3">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {table.getPageCount() > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 dark:border-slate-800 text-sm text-slate-500">
              <span>
                {t("common.rangeOfTotal", {
                  start: table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1,
                  end:
                    table.getState().pagination.pageIndex * table.getState().pagination.pageSize +
                    table.getRowModel().rows.length,
                  total: table.getFilteredRowModel().rows.length,
                })}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => table.previousPage()}
                  disabled={!table.getCanPreviousPage()}
                >
                  {t("common.previous")}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>
                  {t("common.next")}
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
