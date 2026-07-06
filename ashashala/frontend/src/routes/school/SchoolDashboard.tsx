import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { schoolApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Card, CardHeader, Skeleton, StatTile } from "../../components/ui";

const tooltipStyle = {
  borderRadius: 12,
  border: "1px solid #e2e8f0",
  boxShadow: "0 4px 16px -4px rgba(15,23,42,0.12)",
  fontSize: 12,
};

export default function SchoolDashboard() {
  const q = useQuery({ queryKey: ["school", "dashboard"], queryFn: schoolApi.dashboard });
  const usage = useQuery({ queryKey: ["school", "llm-usage"], queryFn: () => schoolApi.llmUsage(7) });

  if (q.isLoading)
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
    );

  const d = q.data ?? {};
  const tiles = [
    { label: "Teachers", value: d.teachers ?? 0, icon: "🧑‍🏫", tone: "brand" as const },
    { label: "Students", value: d.students ?? 0, icon: "🎓", tone: "green" as const },
    { label: "Classes", value: d.classes ?? 0, icon: "🗂️", tone: "slate" as const },
    { label: "Avg mastery", value: `${d.avg_mastery ?? 0}`, icon: "📈", tone: "amber" as const },
  ];

  return (
    <div>
      <PageTitle subtitle="Your school at a glance.">School Dashboard</PageTitle>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {tiles.map((t) => (
          <StatTile key={t.label} {...t} />
        ))}
      </div>

      <Card className="mb-6">
        <CardHeader
          title="LLM usage"
          subtitle="Tokens spent against the free-tier quota (7 days)."
          icon="⚡"
          action={
            usage.data?.over_quota ? (
              <Badge tone="red">⚠ Over daily quota</Badge>
            ) : (
              <Badge tone="green">✓ Within quota</Badge>
            )
          }
        />
        <div className="p-5">
          {usage.isLoading ? (
            <Skeleton className="h-40" />
          ) : (
            <>
              <div className="grid grid-cols-3 gap-4 mb-5">
                <MiniStat label="Tokens today" value={(usage.data?.today_tokens ?? 0).toLocaleString()} />
                <MiniStat label="Calls today" value={usage.data?.today_calls ?? 0} />
                <MiniStat label="Error rate" value={`${Math.round((usage.data?.today_error_rate ?? 0) * 100)}%`} />
              </div>
              {!usage.data?.by_day.length ? (
                <p className="text-sm text-slate-400 text-center py-6">No LLM usage recorded yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={usage.data.by_day} margin={{ left: -12 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="day" tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "#94a3b8" }} />
                    <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "#94a3b8" }} />
                    <Tooltip cursor={{ fill: "#f1f5f9" }} contentStyle={tooltipStyle} />
                    <Bar dataKey="tokens" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={44} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </>
          )}
        </div>
      </Card>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="text-center rounded-xl bg-slate-50 py-3">
      <div className="text-xl font-bold text-slate-800 tabular-nums">{value}</div>
      <div className="text-[11px] text-slate-400 uppercase tracking-wide mt-0.5">{label}</div>
    </div>
  );
}
