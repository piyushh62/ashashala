import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Card, CardHeader } from "../../components/ui";
import { DataBoundary } from "../../components/ui/DataBoundary";

export default function TeacherClassProgress() {
  const { classId = "" } = useParams();
  const assignments = useQuery({ queryKey: ["teacher", "assignments"], queryFn: teacherApi.assignments });
  const progress = useQuery({
    queryKey: ["teacher", "class-progress", classId],
    queryFn: () => teacherApi.classProgress(classId),
  });

  const className = assignments.data?.find((a) => a.class_id === classId)?.class_name ?? "Class";

  return (
    <div>
      <Link to="/teacher" className="text-sm text-brand-600 hover:underline">
        ← Dashboard
      </Link>
      <PageTitle subtitle="Per-student mastery, weakest first.">{className} — Progress</PageTitle>

      <DataBoundary
        query={progress}
        isEmpty={(d) => d.length === 0}
        emptyTitle="No students enrolled yet"
        emptyHint="Once students are enrolled and attempt quizzes, their mastery will appear here."
      >
        {(rows) => (
          <div className="space-y-4">
            {rows.map((s) => (
              <Card key={s.student_id}>
                <CardHeader
                  title={s.name}
                  subtitle={s.grade != null ? `Grade ${s.grade}` : undefined}
                  action={
                    <Badge tone={s.avg_mastery < 40 ? "red" : s.avg_mastery < 70 ? "amber" : "green"}>
                      Avg {s.avg_mastery}
                    </Badge>
                  }
                />
                <div className="p-5 space-y-2.5">
                  {!s.topics.length ? (
                    <p className="text-sm text-slate-400">No mastery data yet.</p>
                  ) : (
                    s.topics.map((t) => (
                      <div key={t.topic}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-slate-600">{t.topic}</span>
                          <span className="text-slate-400">{t.score}/100</span>
                        </div>
                        <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-brand-500" style={{ width: `${t.score}%` }} />
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </DataBoundary>
    </div>
  );
}
