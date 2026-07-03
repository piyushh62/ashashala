import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { schoolApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Card, CardHeader, EmptyState, Input, Skeleton, Table } from "../../components/ui";

export default function SchoolAudit() {
  const [action, setAction] = useState("");
  const q = useQuery({
    queryKey: ["school", "audit", action],
    queryFn: () => schoolApi.audit(action || undefined),
  });

  return (
    <div>
      <PageTitle subtitle="Every state-changing action and sensitive read.">Audit Log</PageTitle>
      <Card>
        <CardHeader
          title="Recent activity"
          action={
            <Input
              placeholder="Filter by action e.g. USER_CREATE"
              value={action}
              onChange={(e) => setAction(e.target.value.toUpperCase())}
              className="w-64"
            />
          }
        />
        <div className="p-2">
          {q.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !q.data?.length ? (
            <EmptyState title="No audit entries" />
          ) : (
            <Table head={["Time", "Action", "Actor", "Target", "Status"]}>
              {q.data.map((r) => (
                <tr key={r.id} className="border-b border-slate-50">
                  <td className="px-4 py-2 text-slate-400 text-xs">{new Date(r.ts).toLocaleString()}</td>
                  <td className="px-4 py-2">
                    <Badge>{r.action}</Badge>
                  </td>
                  <td className="px-4 py-2 text-slate-500 text-xs">{r.actor_role}</td>
                  <td className="px-4 py-2 text-slate-500 text-xs">
                    {r.target_type}:{r.target_id?.slice(0, 8)}
                  </td>
                  <td className="px-4 py-2">
                    <Badge tone={r.status === "success" ? "green" : "red"}>{r.status}</Badge>
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </div>
      </Card>
    </div>
  );
}
