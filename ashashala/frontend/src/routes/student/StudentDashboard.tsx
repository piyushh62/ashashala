import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { studentApi } from "../../api/endpoints";
import { MasteryRadar } from "../../components/dashboard/MasteryRadar";
import { TimetableGrid } from "../../components/dashboard/TimetableGrid";
import { Card, CardHeader, Skeleton } from "../../components/ui";

export default function StudentDashboard() {
  const dash = useQuery({ queryKey: ["student", "dashboard"], queryFn: studentApi.dashboard });
  const tt = useQuery({ queryKey: ["student", "timetable"], queryFn: studentApi.timetable });
  const exams = useQuery({ queryKey: ["student", "exams"], queryFn: studentApi.exams });

  return (
    <div>
      {/* Welcome banner */}
      <div className="rounded-2xl p-6 mb-6 bg-gradient-to-br from-brand-600 to-violet-600 text-white shadow-pop relative overflow-hidden animate-slide-up">
        <div className="absolute -top-16 -right-10 w-56 h-56 rounded-full bg-white/10 blur-2xl" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">{dash.data ? `Hi ${dash.data.name}! 👋` : "Welcome"}</h1>
            <p className="text-white/80 text-sm mt-1">
              {dash.data?.recommended_topic
                ? `Your tutor suggests reviewing “${dash.data.recommended_topic}” next.`
                : "Ready to learn something new today?"}
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              to="/student/chat"
              className="bg-white text-brand-700 font-semibold text-sm rounded-xl px-4 py-2.5 hover:bg-white/90 transition"
            >
              💬 Ask tutor
            </Link>
            <Link
              to="/student/quiz"
              className="bg-white/15 backdrop-blur text-white font-semibold text-sm rounded-xl px-4 py-2.5 hover:bg-white/25 transition"
            >
              🧠 Practice
            </Link>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Your mastery" icon="🎯" />
          <div className="p-4">
            {dash.isLoading ? <Skeleton className="h-64" /> : <MasteryRadar data={dash.data?.mastery ?? []} />}
          </div>
        </Card>

        <Card>
          <CardHeader title="This week" icon="🗓️" />
          <div className="p-4">{tt.isLoading ? <Skeleton className="h-40" /> : <TimetableGrid rows={tt.data ?? []} />}</div>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader title="Upcoming exams" icon="📝" />
        <div className="p-5">
          {exams.isLoading ? (
            <Skeleton className="h-16" />
          ) : !exams.data?.length ? (
            <p className="text-sm text-slate-400">No exams scheduled — enjoy the calm! 🌿</p>
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
