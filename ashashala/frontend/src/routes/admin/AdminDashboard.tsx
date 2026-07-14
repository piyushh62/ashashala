import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { adminApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Card, CardHeader, EmptyState, Icon, ProgressBar, Skeleton, StatTile } from "../../components/ui";

const tooltipStyle = {
  borderRadius: 12,
  border: "1px solid #e2e8f0",
  boxShadow: "0 4px 16px -4px rgba(15,23,42,0.12)",
  fontSize: 12,
};

export default function AdminDashboard() {
  const { t } = useTranslation();
  const q = useQuery({ queryKey: ["admin", "dashboard"], queryFn: () => adminApi.dashboard(14) });

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
      <PageTitle subtitle={t("admin.dashboard.subtitle")}>{t("admin.dashboard.title")}</PageTitle>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatTile label={t("admin.dashboard.activeSchools")} value={d?.active_schools ?? 0} icon={<Icon name="schools" />} tone="brand" />
        <StatTile label={t("admin.dashboard.totalUsers")} value={d?.total_users ?? 0} icon={<Icon name="users" />} tone="green" />
        <StatTile
          label={t("admin.dashboard.llmErrorRate")}
          value={`${Math.round((d?.error_rate ?? 0) * 100)}%`}
          icon={<Icon name="alert" />}
          tone={(d?.error_rate ?? 0) > 0.1 ? "rose" : "amber"}
        />
        <StatTile label={t("admin.dashboard.tokensToday")} value={totalToday.toLocaleString()} icon={<Icon name="activity" />} tone="slate" />
      </div>

      <Card className="mb-6">
        <CardHeader title={t("admin.dashboard.tokenUsageTrend")} subtitle={t("admin.dashboard.tokenUsageTrendSubtitle")} icon={<Icon name="trend" />} />
        <div className="p-5">
          {!d?.tokens_by_day.length ? (
            <p className="text-sm text-slate-400 text-center py-6">{t("admin.dashboard.noUsageRecorded")}</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={d.tokens_by_day} margin={{ left: -12 }}>
                <defs>
                  <linearGradient id="tokenTrend" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#7c3aed" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="day" tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "#94a3b8" }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "#94a3b8" }} />
                <Tooltip cursor={{ stroke: "#c4b5fd" }} contentStyle={tooltipStyle} />
                <Area type="monotone" dataKey="tokens" stroke="#7c3aed" strokeWidth={2} fill="url(#tokenTrend)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader title={t("admin.dashboard.tokenUsageToday")} subtitle={t("admin.dashboard.perSchool")} icon={<Icon name="platform" />} />
        <div className="p-5 space-y-4">
          {perSchool.length === 0 ? (
            <EmptyState title={t("admin.dashboard.noUsageRecordedTitle")} icon={<Icon name="trend" />} />
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
