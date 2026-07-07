import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { teacherApi } from "../../api/endpoints";
import type { FlaggedAnswer } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, EmptyState, Input, Skeleton } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";

const PAGE_SIZE = 20;

export default function TeacherFlagged() {
  const toast = useToast();
  const qc = useQueryClient();
  const [offset, setOffset] = useState(0);
  const q = useQuery({
    queryKey: ["teacher", "flagged", offset],
    queryFn: () => teacherApi.flagged(PAGE_SIZE, offset),
  });
  const rows = q.data?.items ?? [];
  const total = q.data?.total ?? 0;
  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = offset + rows.length;

  return (
    <div>
      <PageTitle subtitle="Low-confidence AI grades awaiting your review.">Flagged Answers</PageTitle>
      {q.isLoading ? (
        <Skeleton className="h-24" />
      ) : !rows.length ? (
        <EmptyState title="Queue is empty" hint="Nothing needs review right now." />
      ) : (
        <div className="space-y-4">
          {rows.map((f) => (
            <FlaggedCard key={f.id} f={f} onResolved={() => qc.invalidateQueries({ queryKey: ["teacher", "flagged"] })} toast={toast} />
          ))}
          {total > 0 && (
            <div className="flex items-center justify-between px-1 py-2 text-sm text-slate-500">
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
      )}
    </div>
  );
}

function FlaggedCard({
  f,
  onResolved,
  toast,
}: {
  f: FlaggedAnswer;
  onResolved: () => void;
  toast: ReturnType<typeof useToast>;
}) {
  const [score, setScore] = useState("0.7");
  const [feedback, setFeedback] = useState("");
  const override = useMutation({
    mutationFn: () => teacherApi.override(f.id, { score: Number(score), feedback: feedback || undefined }),
    onSuccess: () => {
      toast.push("Grade overridden.", "success");
      onResolved();
    },
    onError: () => toast.push("Couldn't save override.", "error"),
  });

  return (
    <Card>
      <CardHeader title={f.question_text} subtitle={`AI: score ${f.ai_score ?? "?"} · confidence ${f.ai_confidence ?? "?"}`} />
      <div className="p-5 space-y-3">
        <div className="text-sm">
          <span className="text-slate-400">Student answer:</span> {f.student_answer}
        </div>
        {f.expected_answer && (
          <div className="text-sm">
            <span className="text-slate-400">Expected:</span> {f.expected_answer}
          </div>
        )}
        <div className="flex items-end gap-3 pt-2">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Score (0–1)</label>
            <Input type="number" min={0} max={1} step={0.1} value={score} onChange={(e) => setScore(e.target.value)} className="w-24" />
          </div>
          <div className="flex-1">
            <label className="block text-xs text-slate-500 mb-1">Feedback (optional)</label>
            <Input value={feedback} onChange={(e) => setFeedback(e.target.value)} />
          </div>
          <Button onClick={() => override.mutate()} disabled={override.isPending}>
            Resolve
          </Button>
        </div>
      </div>
    </Card>
  );
}
