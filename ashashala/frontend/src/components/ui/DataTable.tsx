import { useState } from "react";
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
import { Button, EmptyState, Input, Skeleton } from "./index";

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
                  <tr key={hg.id} className="text-left text-slate-400 border-b border-slate-100">
                    {hg.headers.map((h) => (
                      <th
                        key={h.id}
                        onClick={h.column.getToggleSortingHandler()}
                        className={`px-4 py-2.5 font-semibold text-xs uppercase tracking-wide select-none ${
                          h.column.getCanSort() ? "cursor-pointer hover:text-slate-600" : ""
                        }`}
                      >
                        <span className="inline-flex items-center gap-1">
                          {flexRender(h.column.columnDef.header, h.getContext())}
                          {{ asc: "▲", desc: "▼" }[h.column.getIsSorted() as string] ?? null}
                        </span>
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className="divide-y divide-slate-50">
                {table.getRowModel().rows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length} className="px-4 py-10">
                      <EmptyState title="No matches" hint="Try a different search term." icon="🔍" />
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <tr key={row.id} className="hover:bg-slate-50/60 transition">
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
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
              <span>
                Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()} ·{" "}
                {table.getFilteredRowModel().rows.length} rows
              </span>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => table.previousPage()}
                  disabled={!table.getCanPreviousPage()}
                >
                  Previous
                </Button>
                <Button variant="ghost" size="sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
