import { useQuery } from "@tanstack/react-query";
import { studentApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { MasteryRadar } from "../../components/dashboard/MasteryRadar";
import { TimetableGrid } from "../../components/dashboard/TimetableGrid";
import { Badge, Card, CardHeader, Skeleton } from "../../components/ui";

export default function StudentDashboard() {
  const dash = useQuery({ queryKey: ["student", "dashboard"], queryFn: studentApi.dashboard });
  const tt = useQuery({ queryKey: ["student", "timetable"], queryFn: studentApi.timetable });
  const exams = useQuery({ queryKey: ["student", "exams"], queryFn: studentApi.exams });

  return (
    <div>
      <PageTitle subtitle={dash.data ? `Grade ${dash.data.grade ?? "—"}` : undefined}>
        {dash.data ? `Hi ${dash.data.name}!` : "Dashboard"}
      </PageTitle>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader
            title="Your mastery"
            action={
              dash.data?.recommended_topic ? (
                <Badge tone="amber">Next: {dash.data.recommended_topic}</Badge>
              ) : undefined
            }
          />
          <div className="p-4">
            {dash.isLoading ? <Skeleton className="h-64" /> : <MasteryRadar data={dash.data?.mastery ?? []} />}
          </div>
        </Card>

        <Card>
          <CardHeader title="This week" />
          <div className="p-4">{tt.isLoading ? <Skeleton className="h-40" /> : <TimetableGrid rows={tt.data ?? []} />}</div>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader title="Upcoming exams" />
        <div className="p-5">
          {exams.isLoading ? (
            <Skeleton className="h-16" />
          ) : !exams.data?.length ? (
            <p className="text-sm text-slate-400">No exams scheduled.</p>
          ) : (
            <ul className="space-y-2">
              {exams.data.map((e, i) => (
                <li key={i} className="flex justify-between text-sm">
                  <span className="text-slate-700">{e.exam_name}</span>
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
