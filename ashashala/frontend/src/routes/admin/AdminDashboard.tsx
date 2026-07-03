import { useQuery } from "@tanstack/react-query";
import { adminApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Card, CardHeader, Skeleton } from "../../components/ui";

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="p-5">
      <div className="text-3xl font-bold text-brand-600">{value}</div>
      <div className="text-sm text-slate-500 mt-1">{label}</div>
    </Card>
  );
}

export default function AdminDashboard() {
  const q = useQuery({ queryKey: ["admin", "dashboard"], queryFn: adminApi.dashboard });

  if (q.isLoading) return <Skeleton className="h-40" />;
  const d = q.data;

  return (
    <div>
      <PageTitle subtitle="Platform-wide metrics (last 24h).">Platform Dashboard</PageTitle>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Metric label="Active schools" value={d?.active_schools ?? 0} />
        <Metric label="Total users" value={d?.total_users ?? 0} />
        <Metric label="LLM error rate" value={`${Math.round((d?.error_rate ?? 0) * 100)}%`} />
        <Metric
          label="Tokens today"
          value={Object.values(d?.tokens_today_by_school ?? {}).reduce((a, b) => a + b, 0)}
        />
      </div>

      <Card>
        <CardHeader title="Tokens used today, per school" />
        <div className="p-5 space-y-2">
          {Object.entries(d?.tokens_today_by_school ?? {}).length === 0 ? (
            <p className="text-sm text-slate-400">No usage recorded yet.</p>
          ) : (
            Object.entries(d?.tokens_today_by_school ?? {}).map(([school, tokens]) => (
              <div key={school} className="flex justify-between text-sm">
                <span className="text-slate-600 truncate">{school}</span>
                <span className="font-medium tabular-nums">{tokens}</span>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
