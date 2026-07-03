import { useQuery } from "@tanstack/react-query";
import { studentApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Card, CardHeader, EmptyState, Skeleton, Table } from "../../components/ui";

export default function StudentHistory() {
  const hist = useQuery({ queryKey: ["student", "history"], queryFn: studentApi.history });
  const prog = useQuery({ queryKey: ["student", "progress"], queryFn: studentApi.progress });

  return (
    <div>
      <PageTitle subtitle="Your quizzes and mastery over time.">History</PageTitle>

      <Card className="mb-6">
        <CardHeader title="Quiz attempts" />
        <div className="p-2">
          {hist.isLoading ? (
            <Skeleton className="h-20 m-3" />
          ) : !hist.data?.quiz_attempts.length ? (
            <EmptyState title="No attempts yet" />
          ) : (
            <Table head={["Quiz", "Score"]}>
              {hist.data.quiz_attempts.map((a, i) => (
                <tr key={i} className="border-b border-slate-50">
                  <td className="px-4 py-2 text-slate-500 text-xs">{a.quiz_id.slice(0, 8)}</td>
                  <td className="px-4 py-2 font-medium">{Math.round((a.score ?? 0) * 100)}%</td>
                </tr>
              ))}
            </Table>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader title="Mastery by topic" />
        <div className="p-5 space-y-2">
          {prog.isLoading ? (
            <Skeleton className="h-16" />
          ) : !prog.data?.length ? (
            <p className="text-sm text-slate-400">No mastery yet.</p>
          ) : (
            prog.data.map((p) => (
              <div key={p.topic}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-600">{p.topic}</span>
                  <span className="text-slate-400">{p.score}/100</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-brand-500" style={{ width: `${p.score}%` }} />
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
