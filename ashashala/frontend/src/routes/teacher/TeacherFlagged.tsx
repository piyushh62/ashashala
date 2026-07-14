import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { teacherApi } from "../../api/endpoints";
import type { FlaggedAnswer } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, EmptyState, Input, Pager, Skeleton } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";

const PAGE_SIZE = 20;

export default function TeacherFlagged() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const [offset, setOffset] = useState(0);
  const q = useQuery({
    queryKey: ["teacher", "flagged", offset],
    queryFn: () => teacherApi.flagged(PAGE_SIZE, offset),
  });
  const rows = q.data?.items ?? [];
  const total = q.data?.total ?? 0;

  return (
    <div>
      <PageTitle subtitle={t("teacher.flagged.subtitle")}>{t("teacher.flagged.title")}</PageTitle>
      {q.isLoading ? (
        <Skeleton className="h-24" />
      ) : !rows.length ? (
        <EmptyState title={t("teacher.flagged.queueEmpty")} hint={t("teacher.flagged.queueEmptyHint")} />
      ) : (
        <div className="space-y-4">
          {rows.map((f) => (
            <FlaggedCard key={f.id} f={f} onResolved={() => qc.invalidateQueries({ queryKey: ["teacher", "flagged"] })} toast={toast} />
          ))}
          <Pager offset={offset} limit={PAGE_SIZE} total={total} count={rows.length} onOffsetChange={setOffset} />
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
  const { t } = useTranslation();
  const [score, setScore] = useState("0.7");
  const [feedback, setFeedback] = useState("");
  const override = useMutation({
    mutationFn: () => teacherApi.override(f.id, { score: Number(score), feedback: feedback || undefined }),
    onSuccess: () => {
      toast.push(t("teacher.flagged.gradeOverridden"), "success");
      onResolved();
    },
    onError: () => toast.push(t("teacher.flagged.saveOverrideFailed"), "error"),
  });

  return (
    <Card>
      <CardHeader title={f.question_text} subtitle={t("teacher.flagged.aiScoreConfidence", { score: f.ai_score ?? "?", confidence: f.ai_confidence ?? "?" })} />
      <div className="p-5 space-y-3">
        <div className="text-sm">
          <span className="text-slate-400">{t("teacher.flagged.studentAnswer")}</span> {f.student_answer}
        </div>
        {f.expected_answer && (
          <div className="text-sm">
            <span className="text-slate-400">{t("teacher.flagged.expected")}</span> {f.expected_answer}
          </div>
        )}
        <div className="flex items-end gap-3 pt-2">
          <div>
            <label className="block text-xs text-slate-500 mb-1">{t("teacher.flagged.score01")}</label>
            <Input type="number" min={0} max={1} step={0.1} value={score} onChange={(e) => setScore(e.target.value)} className="w-24" />
          </div>
          <div className="flex-1">
            <label className="block text-xs text-slate-500 mb-1">{t("teacher.flagged.feedbackOptional")}</label>
            <Input value={feedback} onChange={(e) => setFeedback(e.target.value)} />
          </div>
          <Button onClick={() => override.mutate()} disabled={override.isPending}>
            {t("teacher.flagged.resolve")}
          </Button>
        </div>
      </div>
    </Card>
  );
}
