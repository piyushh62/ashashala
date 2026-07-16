import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { parentApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { MasteryRadar } from "../../components/dashboard/MasteryRadar";
import { TimetableGrid } from "../../components/dashboard/TimetableGrid";
import { Card, CardHeader, EmptyState, Icon, Skeleton } from "../../components/ui";

const tooltipStyle = {
  borderRadius: 12,
  border: "1px solid #e2e8f0",
  boxShadow: "0 4px 16px -4px rgba(15,23,42,0.12)",
  fontSize: 12,
};

export default function ParentChild() {
  const { t } = useTranslation();
  const { id = "" } = useParams();
  const dash = useQuery({ queryKey: ["parent", "child", id], queryFn: () => parentApi.childDashboard(id) });
  const tt = useQuery({ queryKey: ["parent", "child", id, "tt"], queryFn: () => parentApi.childTimetable(id) });
  const hist = useQuery({ queryKey: ["parent", "child", id, "history"], queryFn: () => parentApi.childHistory(id) });
  const examTt = useQuery({
    queryKey: ["parent", "child", id, "exam-tt"],
    queryFn: () => parentApi.childExamTimetable(id),
  });

  const trend = (hist.data?.items ?? []).map((a) => ({
    date: new Date(a.attempted_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    score: Math.round((a.score ?? 0) * 100),
  }));

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-3">
        <Link to="/parent" className="text-sm text-brand-600 hover:underline">
          {t("parent.child.allChildren")}
        </Link>
        <div className="flex gap-2">
          <Link
            to={`/parent/child/${id}/reports`}
            className="inline-flex items-center gap-1.5 text-sm font-medium rounded-xl px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 transition"
          >
            <Icon name="reports" className="w-4 h-4" />
            {t("parent.child.reports")}
          </Link>
          <Link
            to={`/parent/child/${id}/messages`}
            className="inline-flex items-center gap-1.5 text-sm font-medium rounded-xl px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 transition"
          >
            <Icon name="messages" className="w-4 h-4" />
            {t("parent.child.messages")}
          </Link>
        </div>
      </div>
      <PageTitle subtitle={t("parent.child.subtitle")}>
        {dash.data?.student.name ?? t("parent.child.defaultName")}
      </PageTitle>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title={t("parent.child.mastery")} />
          <div className="p-4">
            {dash.isLoading ? <Skeleton className="h-64" /> : <MasteryRadar data={dash.data?.mastery ?? []} />}
          </div>
        </Card>
        <Card>
          <CardHeader title={t("parent.child.timetable")} />
          <div className="p-4">
            {tt.isLoading ? <Skeleton className="h-40" /> : tt.data?.length ? <TimetableGrid rows={tt.data} /> : <EmptyState title={t("parent.child.noPeriods")} />}
          </div>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader title={t("parent.child.quizScoreTrend")} icon={<Icon name="trend" />} />
        <div className="p-5">
          {hist.isLoading ? (
            <Skeleton className="h-40" />
          ) : trend.length < 2 ? (
            <p className="text-sm text-slate-400 text-center py-6">{t("parent.child.trendHint")}</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={trend} margin={{ left: -12 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "#94a3b8" }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "#94a3b8" }} domain={[0, 100]} />
                <Tooltip cursor={{ stroke: "#c4b5fd" }} contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="score" stroke="#7c3aed" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </Card>

      <Card className="mt-6">
        <CardHeader title={t("parent.child.upcomingExams")} icon={<Icon name="exams" />} />
        <div className="p-5">
          {examTt.isLoading ? (
            <Skeleton className="h-16" />
          ) : !examTt.data?.length ? (
            <p className="text-sm text-slate-400">{t("parent.child.noExamsScheduled")}</p>
          ) : (
            <ul className="space-y-2.5">
              {examTt.data.map((e, i) => (
                <li key={i} className="flex items-center justify-between text-sm rounded-xl bg-slate-50 px-4 py-2.5">
                  <span className="text-slate-700 font-medium">{e.exam_name}</span>
                  <span className="text-slate-400">{e.exam_date}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Card>
    </div>
  );
}
