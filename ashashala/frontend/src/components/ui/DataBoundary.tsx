import type { ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { ApiError } from "../../api/client";
import { Button, EmptyState, Skeleton } from "./index";

export function ErrorBanner({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-500/10 px-5 py-4">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-9 h-9 rounded-xl bg-rose-100 dark:bg-rose-500/20 text-rose-600 dark:text-rose-400 grid place-items-center text-lg shrink-0">!</div>
        <div className="min-w-0">
          <p className="font-semibold text-rose-700 dark:text-rose-300 text-sm">Something went wrong</p>
          <p className="text-sm text-rose-600/80 dark:text-rose-400/80 truncate">{message}</p>
        </div>
      </div>
      {onRetry && (
        <Button variant="danger" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Please try again.";
}

/**
 * DataBoundary — the one place every page decides how to render a
 * useQuery result, so loading/error/empty are never silently conflated.
 * A failed request renders an ErrorBanner+Retry, never an empty state.
 */
export function DataBoundary<T>({
  query,
  loadingFallback,
  isEmpty,
  emptyTitle = "Nothing here yet",
  emptyHint,
  children,
}: {
  query: Pick<UseQueryResult<T>, "data" | "isLoading" | "isError" | "error" | "refetch">;
  loadingFallback?: ReactNode;
  isEmpty?: (data: T) => boolean;
  emptyTitle?: string;
  emptyHint?: string;
  children: (data: T) => ReactNode;
}) {
  if (query.isLoading) return <>{loadingFallback ?? <Skeleton className="h-40" />}</>;

  if (query.isError) {
    return <ErrorBanner message={messageFor(query.error)} onRetry={() => query.refetch()} />;
  }

  const data = query.data as T;
  if (isEmpty ? isEmpty(data) : false) {
    return <EmptyState title={emptyTitle} hint={emptyHint} />;
  }

  return <>{children(data)}</>;
}
