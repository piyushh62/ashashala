import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { studentApi } from "../../api/endpoints";
import { MasteryRadar } from "../../components/dashboard/MasteryRadar";
import { TimetableGrid } from "../../components/dashboard/TimetableGrid";
import { Card, CardHeader, Skeleton } from "../../components/ui";

const tooltipStyle = {
  borderRadius: 12,
  border: "1px solid #e2e8f0",
  boxShadow: "0 4px 16px -4px rgba(15,23,42,0.12)",
  fontSize: 12,
};

export default function StudentDashboard() {
  const { t } = useTranslation();
  const dash = useQuery({ queryKey: ["student", "dashboard"], queryFn: studentApi.dashboard });
  const tt = useQuery({ queryKey: ["student", "timetable"], queryFn: studentApi.timetable });
  const exams = useQuery({ queryKey: ["student", "exams"], queryFn: studentApi.exams });
  const hist = useQuery({ queryKey: ["student", "history"], queryFn: () => studentApi.history() });

  const trend = (hist.data?.items ?? []).map((a) => ({
    date: new Date(a.attempted_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    score: Math.round((a.score ?? 0) * 100),
  }));

  return (
    <div>
      {/* Welcome banner */}
      <div className="rounded-2xl p-6 mb-6 bg-gradient-to-br from-brand-600 to-violet-600 text-white shadow-pop relative overflow-hidden animate-slide-up">
        <div className="absolute -top-16 -right-10 w-56 h-56 rounded-full bg-white/10 blur-2xl" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">{dash.data ? t("student.dashboard.greeting", { name: dash.data.name }) : t("student.dashboard.welcome")}</h1>
            <p className="text-white/80 text-sm mt-1">
              {dash.data?.recommended_topic
                ? t("student.dashboard.recommendedTopic", { topic: dash.data.recommended_topic })
                : t("student.dashboard.readyToLearn")}
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              to="/student/chat"
              className="bg-white text-brand-700 font-semibold text-sm rounded-xl px-4 py-2.5 hover:bg-white/90 transition"
            >
              {t("student.dashboard.askTutor")}
            </Link>
            <Link
              to="/student/quiz"
              className="bg-white/15 backdrop-blur text-white font-semibold text-sm rounded-xl px-4 py-2.5 hover:bg-white/25 transition"
            >
              {t("student.dashboard.practice")}
            </Link>
          </div>
        </div>
      </div>

      <Link to="/student/today" className="block mb-6 group">
        <div className="rounded-2xl px-5 py-4 bg-white border border-slate-200/70 shadow-card flex items-center justify-between gap-4 transition group-hover:border-brand-200 group-hover:shadow-soft">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 grid place-items-center text-lg shrink-0">
              📖
            </div>
            <div>
              <div className="font-semibold text-slate-800">{t("student.dashboard.todaysLearning")}</div>
              <div className="text-sm text-slate-500">{t("student.dashboard.todaysLearningHint")}</div>
            </div>
          </div>
          <span className="text-brand-600 text-sm font-medium shrink-0">{t("student.dashboard.viewArrow")}</span>
        </div>
      </Link>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title={t("student.dashboard.yourMastery")} icon="🎯" />
          <div className="p-4">
            {dash.isLoading ? <Skeleton className="h-64" /> : <MasteryRadar data={dash.data?.mastery ?? []} />}
          </div>
        </Card>

        <Card>
          <CardHeader title={t("student.dashboard.thisWeek")} icon="🗓️" />
          <div className="p-4">{tt.isLoading ? <Skeleton className="h-40" /> : <TimetableGrid rows={tt.data ?? []} />}</div>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader title={t("student.dashboard.quizScoreTrend")} icon="📈" />
        <div className="p-5">
          {hist.isLoading ? (
            <Skeleton className="h-40" />
          ) : trend.length < 2 ? (
            <p className="text-sm text-slate-400 text-center py-6">{t("student.dashboard.trendHint")}</p>
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
        <CardHeader title={t("student.dashboard.upcomingExams")} icon="📝" />
        <div className="p-5">
          {exams.isLoading ? (
            <Skeleton className="h-16" />
          ) : !exams.data?.length ? (
            <p className="text-sm text-slate-400">{t("student.dashboard.noExamsScheduled")}</p>
          ) : (
            <ul className="space-y-2.5">
              {exams.data.map((e, i) => (
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
