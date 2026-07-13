import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { agentActionsApi } from "../api/endpoints";
import type { AgentActionOut } from "../types/api";
import { Badge, Button, Card, CardHeader, EmptyState, Skeleton } from "./ui";
import { useToast } from "./ui/Toast";

const PAGE_SIZE = 20;

const STATUS_TONE: Record<AgentActionOut["status"], string> = {
  pending: "amber",
  approved: "green",
  rejected: "red",
  auto_applied: "blue",
};

export function AgentActionQueue() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const [offset, setOffset] = useState(0);
  const q = useQuery({
    queryKey: ["agent-actions", "pending", offset],
    queryFn: () => agentActionsApi.list("pending", PAGE_SIZE, offset),
  });
  // scheduling_agent proposals aren't handled by the generic approve/reject
  // route — they're resolved via the dedicated Timetable page's "AI Suggest"
  // option-selection flow, so surfacing them here would be a dead-end button.
  const rows = (q.data?.items ?? []).filter((a) => a.agent_name !== "scheduling_agent");
  const total = q.data?.total ?? 0;
  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = offset + rows.length;

  const invalidate = () => qc.invalidateQueries({ queryKey: ["agent-actions"] });

  return (
    <div>
      {q.isLoading ? (
        <Skeleton className="h-24" />
      ) : !rows.length ? (
        <EmptyState title={t("agentQueue.queueEmpty")} hint={t("agentQueue.queueEmptyHint")} icon="🤖" />
      ) : (
        <div className="space-y-4">
          {rows.map((a) => (
            <AgentActionCard key={a.id} action={a} onResolved={invalidate} toast={toast} />
          ))}
          {total > 0 && (
            <div className="flex items-center justify-between px-1 py-2 text-sm text-slate-500">
              <span>
                {t("common.rangeOfTotal", { start: rangeStart, end: rangeEnd, total })}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  disabled={offset === 0}
                >
                  {t("common.previous")}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  disabled={rangeEnd >= total}
                >
                  {t("common.next")}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AgentActionCard({
  action,
  onResolved,
  toast,
}: {
  action: AgentActionOut;
  onResolved: () => void;
  toast: ReturnType<typeof useToast>;
}) {
  const { t } = useTranslation();
  const approve = useMutation({
    mutationFn: () => agentActionsApi.approve(action.id),
    onSuccess: () => {
      toast.push(t("agentQueue.actionApproved"), "success");
      onResolved();
    },
    onError: () => toast.push(t("agentQueue.actionApproveFailed"), "error"),
  });
  const reject = useMutation({
    mutationFn: () => agentActionsApi.reject(action.id),
    onSuccess: () => {
      toast.push(t("agentQueue.actionRejected"), "success");
      onResolved();
    },
    onError: () => toast.push(t("agentQueue.actionRejectFailed"), "error"),
  });
  const busy = approve.isPending || reject.isPending;

  return (
    <Card>
      <CardHeader
        title={`${action.agent_name} · ${action.action_type}`}
        subtitle={action.confidence != null ? t("agentQueue.confidence", { percent: Math.round(action.confidence * 100) }) : undefined}
        action={<Badge tone={STATUS_TONE[action.status]}>{action.status}</Badge>}
      />
      <div className="p-5 space-y-3">
        <pre className="text-xs bg-slate-50 dark:bg-slate-800 rounded-lg p-3 overflow-x-auto text-slate-600 dark:text-slate-300">
          {JSON.stringify(action.payload_json, null, 2)}
        </pre>
        {action.status === "pending" && (
          <div className="flex gap-2 justify-end">
            <Button variant="danger" size="sm" onClick={() => reject.mutate()} disabled={busy}>
              {t("agentQueue.reject")}
            </Button>
            <Button size="sm" onClick={() => approve.mutate()} disabled={busy}>
              {t("agentQueue.approve")}
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}
