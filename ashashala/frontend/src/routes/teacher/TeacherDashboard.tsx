import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Card, CardHeader, EmptyState, Skeleton, StatTile, Table } from "../../components/ui";

export default function TeacherDashboard() {
  const dash = useQuery({ queryKey: ["teacher", "dashboard"], queryFn: teacherApi.dashboard });
  const assignments = useQuery({ queryKey: ["teacher", "assignments"], queryFn: teacherApi.assignments });
  const flagged = useQuery({ queryKey: ["teacher", "flagged"], queryFn: () => teacherApi.flagged() });

  const classes = useMemo(() => {
    const seen = new Map<string, string>();
    for (const a of assignments.data ?? []) seen.set(a.class_id, a.class_name);
    return Array.from(seen.entries());
  }, [assignments.data]);

  const progressQueries = useQueries({
    queries: classes.map(([classId, className]) => ({
      queryKey: ["teacher", "class-progress", classId],
      queryFn: () =>
        teacherApi
          .classProgress(classId)
          .then((rows) => rows.map((r) => ({ ...r, class_id: classId, class_name: className }))),
    })),
  });

  const loadingProgress = classes.length > 0 && progressQueries.some((q) => q.isLoading);
  const weakest = useMemo(
    () =>
      progressQueries
        .flatMap((q) => q.data ?? [])
        .sort((a, b) => a.avg_mastery - b.avg_mastery)
        .slice(0, 8),
    [progressQueries],
  );

  return (
    <div>
      <PageTitle subtitle="Your classes at a glance.">Teacher Dashboard</PageTitle>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatTile label="Classes" value={dash.data?.classes.length ?? 0} icon="🗂️" tone="brand" />
        <StatTile label="Subjects" value={dash.data?.subjects.length ?? 0} icon="📖" tone="green" />
        <StatTile label="Materials uploaded" value={dash.data?.materials_uploaded ?? 0} icon="📚" tone="slate" />
        <StatTile
          label="Open reviews"
          value={flagged.data?.total ?? 0}
          icon="🚩"
          tone={(flagged.data?.total ?? 0) > 0 ? "amber" : "green"}
        />
      </div>

      <Card>
        <CardHeader title="Students needing attention" subtitle="Weakest average mastery across your classes" icon="🎯" />
        <div className="p-2">
          {loadingProgress ? (
            <Skeleton className="h-40 m-3" />
          ) : !weakest.length ? (
            <EmptyState title="No mastery data yet" hint="Once students attempt quizzes, this list fills in." />
          ) : (
            <Table head={["Student", "Class", "Avg mastery"]}>
              {weakest.map((s) => (
                <tr key={`${s.class_id}-${s.student_id}`} className="border-b border-slate-50">
                  <td className="px-4 py-2 font-medium text-slate-700">{s.name}</td>
                  <td className="px-4 py-2 text-slate-500">
                    <Link to={`/teacher/class-progress/${s.class_id}`} className="text-brand-600 hover:underline">
                      {s.class_name}
                    </Link>
                  </td>
                  <td className="px-4 py-2">
                    <Badge tone={s.avg_mastery < 40 ? "red" : s.avg_mastery < 70 ? "amber" : "green"}>
                      {s.avg_mastery}
                    </Badge>
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </div>
      </Card>

      {classes.length > 0 && (
        <Card className="mt-6">
          <CardHeader title="Your classes" subtitle="Jump to a class's full progress breakdown." icon="🗂️" />
          <div className="p-5 flex flex-wrap gap-2.5">
            {classes.map(([classId, className]) => (
              <Link
                key={classId}
                to={`/teacher/class-progress/${classId}`}
                className="text-sm font-medium rounded-xl px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 transition"
              >
                {className}
              </Link>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
