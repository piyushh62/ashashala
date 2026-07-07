import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { studentApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, EmptyState, Skeleton, Table } from "../../components/ui";

const PAGE_SIZE = 20;

export default function StudentHistory() {
  const [offset, setOffset] = useState(0);
  const hist = useQuery({
    queryKey: ["student", "history", offset],
    queryFn: () => studentApi.history(PAGE_SIZE, offset),
  });
  const prog = useQuery({ queryKey: ["student", "progress"], queryFn: studentApi.progress });
  const attempts = hist.data?.items ?? [];
  const total = hist.data?.total ?? 0;
  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = offset + attempts.length;

  return (
    <div>
      <PageTitle subtitle="Your quizzes and mastery over time.">History</PageTitle>

      <Card className="mb-6">
        <CardHeader title="Quiz attempts" />
        <div className="p-2">
          {hist.isLoading ? (
            <Skeleton className="h-20 m-3" />
          ) : !attempts.length ? (
            <EmptyState title="No attempts yet" />
          ) : (
            <Table head={["Quiz", "Score"]}>
              {attempts.map((a, i) => (
                <tr key={i} className="border-b border-slate-50">
                  <td className="px-4 py-2 text-slate-500 text-xs">{a.quiz_id.slice(0, 8)}</td>
                  <td className="px-4 py-2 font-medium">{Math.round((a.score ?? 0) * 100)}%</td>
                </tr>
              ))}
            </Table>
          )}
          {total > 0 && (
            <div className="flex items-center justify-between px-3 py-3 text-sm text-slate-500">
              <span>
                {rangeStart}–{rangeEnd} of {total}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  disabled={offset === 0}
                >
                  Previous
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  disabled={rangeEnd >= total}
                >
                  Next
                </Button>
              </div>
            </div>
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
