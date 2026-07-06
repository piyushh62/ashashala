import { useQuery } from "@tanstack/react-query";
import { adminApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Card, CardHeader, EmptyState, ProgressBar, Skeleton, StatTile } from "../../components/ui";

export default function AdminDashboard() {
  const q = useQuery({ queryKey: ["admin", "dashboard"], queryFn: adminApi.dashboard });

  if (q.isLoading)
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
    );

  const d = q.data;
  const perSchool = Object.entries(d?.tokens_today_by_school ?? {});
  const maxTokens = Math.max(1, ...perSchool.map(([, v]) => v));
  const totalToday = perSchool.reduce((a, [, v]) => a + v, 0);

  return (
    <div>
      <PageTitle subtitle="Platform-wide metrics from the last 24 hours.">Platform Dashboard</PageTitle>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatTile label="Active schools" value={d?.active_schools ?? 0} icon="🏫" tone="brand" />
        <StatTile label="Total users" value={d?.total_users ?? 0} icon="👥" tone="green" />
        <StatTile
          label="LLM error rate"
          value={`${Math.round((d?.error_rate ?? 0) * 100)}%`}
          icon="⚠️"
          tone={(d?.error_rate ?? 0) > 0.1 ? "rose" : "amber"}
        />
        <StatTile label="Tokens today" value={totalToday.toLocaleString()} icon="⚡" tone="slate" />
      </div>

      <Card>
        <CardHeader title="Token usage today" subtitle="Per school" icon="📊" />
        <div className="p-5 space-y-4">
          {perSchool.length === 0 ? (
            <EmptyState title="No usage recorded yet" icon="📈" />
          ) : (
            perSchool.map(([school, tokens]) => (
              <div key={school}>
                <div className="flex justify-between text-sm mb-1.5">
                  <span className="text-slate-600 truncate font-medium">{school}</span>
                  <Badge tone="brand">{tokens.toLocaleString()}</Badge>
                </div>
                <ProgressBar value={(tokens / maxTokens) * 100} />
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
