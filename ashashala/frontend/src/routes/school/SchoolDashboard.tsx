import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useTranslation } from "react-i18next";
import { schoolApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Card, CardHeader, EmptyState, Icon, Skeleton, StatTile, Table } from "../../components/ui";
import { DataBoundary } from "../../components/ui/DataBoundary";

const tooltipStyle = {
  borderRadius: 12,
  border: "1px solid #e2e8f0",
  boxShadow: "0 4px 16px -4px rgba(15,23,42,0.12)",
  fontSize: 12,
};

export default function SchoolDashboard() {
  const { t } = useTranslation();
  const q = useQuery({ queryKey: ["school", "dashboard"], queryFn: schoolApi.dashboard });
  const usage = useQuery({ queryKey: ["school", "llm-usage"], queryFn: () => schoolApi.llmUsage(7) });
  const atRisk = useQuery({ queryKey: ["school", "at-risk"], queryFn: () => schoolApi.atRisk(10) });
  const mastery = useQuery({ queryKey: ["school", "mastery-by-class"], queryFn: schoolApi.masteryByClass });
  const activity = useQuery({ queryKey: ["school", "audit", "recent"], queryFn: () => schoolApi.audit() });

  if (q.isLoading)
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
    );

  const d = q.data;
  const tiles = [
    { label: t("school.dashboard.teachers"), value: d?.teachers ?? 0, icon: <Icon name="teacher" />, tone: "brand" as const },
    { label: t("school.dashboard.students"), value: d?.students ?? 0, icon: <Icon name="students" />, tone: "green" as const },
    { label: t("school.dashboard.classes"), value: d?.classes ?? 0, icon: <Icon name="structure" />, tone: "slate" as const },
    { label: t("school.dashboard.avgMastery"), value: `${d?.avg_mastery ?? 0}`, icon: <Icon name="trend" />, tone: "amber" as const },
  ];

  return (
    <div>
      <PageTitle subtitle={t("school.dashboard.subtitle")}>{t("school.dashboard.title")}</PageTitle>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {tiles.map((tile) => (
          <StatTile key={tile.label} {...tile} />
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mb-6">
        <Card>
          <CardHeader
            title={t("school.dashboard.atRiskStudents")}
            subtitle={t("school.dashboard.lowestAvgMastery")}
            icon={<Icon name="critical" />}
          />
          <div className="p-2">
            <DataBoundary
              query={atRisk}
              isEmpty={(rows) => rows.length === 0}
              emptyTitle={t("school.dashboard.noMasteryData")}
              loadingFallback={<Skeleton className="h-40 m-3" />}
            >
              {(rows) => (
                <Table head={[t("school.dashboard.colStudent"), t("school.dashboard.colAvgMastery")]}>
                  {rows.map((r) => (
                    <tr key={r.student_id} className="border-b border-slate-50">
                      <td className="px-4 py-2 font-medium text-slate-700">{r.student_name}</td>
                      <td className="px-4 py-2">
                        <Badge tone={r.avg_mastery < 40 ? "red" : r.avg_mastery < 70 ? "amber" : "green"}>
                          {r.avg_mastery}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </Table>
              )}
            </DataBoundary>
          </div>
        </Card>

        <Card>
          <CardHeader title={t("school.dashboard.masteryByClass")} icon={<Icon name="structure" />} />
          <div className="p-5">
            <DataBoundary
              query={mastery}
              isEmpty={(rows) => rows.length === 0}
              emptyTitle={t("school.dashboard.noMasteryData")}
              loadingFallback={<Skeleton className="h-40" />}
            >
              {(rows) => (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={rows} margin={{ left: -12 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="class_name" tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "#94a3b8" }} />
                    <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "#94a3b8" }} />
                    <Tooltip cursor={{ fill: "#f1f5f9" }} contentStyle={tooltipStyle} />
                    <Bar dataKey="avg_mastery" fill="#7c3aed" radius={[4, 4, 0, 0]} maxBarSize={44} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </DataBoundary>
          </div>
        </Card>
      </div>

      <Card className="mb-6">
        <CardHeader
          title={t("school.dashboard.llmUsage")}
          subtitle={t("school.dashboard.llmUsageSubtitle")}
          icon={<Icon name="activity" />}
          action={
            usage.data?.over_quota ? (
              <Badge tone="red">{t("school.dashboard.overQuota")}</Badge>
            ) : (
              <Badge tone="green">{t("school.dashboard.withinQuota")}</Badge>
            )
          }
        />
        <div className="p-5">
          {usage.isLoading ? (
            <Skeleton className="h-40" />
          ) : (
            <>
              <div className="grid grid-cols-3 gap-4 mb-5">
                <MiniStat label={t("school.dashboard.tokensToday")} value={(usage.data?.today_tokens ?? 0).toLocaleString()} />
                <MiniStat label={t("school.dashboard.callsToday")} value={usage.data?.today_calls ?? 0} />
                <MiniStat label={t("school.dashboard.errorRate")} value={`${Math.round((usage.data?.today_error_rate ?? 0) * 100)}%`} />
              </div>
              {!usage.data?.by_day.length ? (
                <p className="text-sm text-slate-400 text-center py-6">{t("school.dashboard.noLlmUsage")}</p>
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

      <Card>
        <CardHeader title={t("school.dashboard.recentActivity")} icon={<Icon name="audit" />} />
        <div className="p-2">
          {activity.isLoading ? (
            <Skeleton className="h-32 m-3" />
          ) : !activity.data?.items.length ? (
            <EmptyState title={t("school.dashboard.noActivity")} />
          ) : (
            <ul className="divide-y divide-slate-50">
              {activity.data.items.slice(0, 8).map((a) => (
                <li key={a.id} className="px-4 py-2.5 flex items-center justify-between text-sm">
                  <span className="text-slate-700 font-medium">{a.action}</span>
                  <span className="text-slate-400 text-xs">{new Date(a.ts).toLocaleString()}</span>
                </li>
              ))}
            </ul>
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
