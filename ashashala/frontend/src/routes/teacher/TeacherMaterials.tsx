import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { teacherApi } from "../../api/endpoints";
import type { SuggestedQuizOut } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Icon, Pager, Skeleton, Table } from "../../components/ui";
import { Modal } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";

const PAGE_SIZE = 20;

export default function TeacherMaterials() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const [offset, setOffset] = useState(0);
  const [draftQuiz, setDraftQuiz] = useState<SuggestedQuizOut | null>(null);

  const materials = useQuery({
    queryKey: ["teacher", "materials", offset],
    queryFn: () => teacherApi.materials(PAGE_SIZE, offset),
  });
  const materialRows = materials.data?.items ?? [];
  const total = materials.data?.total ?? 0;

  const suggestQuiz = useMutation({
    mutationFn: (docId: string) => teacherApi.suggestQuizFromMaterial(docId),
    onSuccess: (quiz) => setDraftQuiz(quiz),
    onError: () => toast.push(t("teacher.materials.quizGenerateFailed"), "error"),
  });

  const approveDraft = useMutation({
    mutationFn: (quizId: string) => teacherApi.approveQuiz(quizId, true),
    onSuccess: () => {
      toast.push(t("teacher.materials.quizApproved"), "success");
      setDraftQuiz(null);
    },
    onError: () => toast.push(t("teacher.materials.quizApproveFailed"), "error"),
  });

  return (
    <div>
      <PageTitle subtitle={t("teacher.materials.subtitle")}>{t("teacher.materials.title")}</PageTitle>

      <Card>
        <CardHeader
          title={t("teacher.materials.myMaterials")}
          action={
            <Button size="sm" onClick={() => navigate("/teacher/materials/new")}>
              <Icon name="add" className="w-4 h-4" />
              {t("teacher.materials.addMaterial")}
            </Button>
          }
        />
        <div className="p-2">
          {materials.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !materialRows.length ? (
            <EmptyState title={t("teacher.materials.noMaterialsYet")} />
          ) : (
            <Table head={[t("teacher.materials.colName"), t("teacher.materials.colType"), t("teacher.materials.colStatus"), ""]}>
              {materialRows.map((m) => (
                <tr key={m.id} className="border-b border-slate-50">
                  <td className="px-4 py-2 font-medium text-slate-700 truncate max-w-xs">{m.filename}</td>
                  <td className="px-4 py-2">
                    <Badge>{m.source_type}</Badge>
                  </td>
                  <td className="px-4 py-2">
                    <Badge tone={m.status === "indexed" ? "green" : m.status === "failed" ? "red" : "amber"}>
                      {m.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-2 text-right whitespace-nowrap">
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={m.status !== "indexed" || suggestQuiz.isPending}
                      onClick={() => suggestQuiz.mutate(m.id)}
                    >
                      {suggestQuiz.isPending && suggestQuiz.variables === m.id ? t("teacher.materials.generatingQuiz") : t("teacher.materials.generateQuiz")}
                    </Button>
                  </td>
                </tr>
              ))}
            </Table>
          )}
          <Pager offset={offset} limit={PAGE_SIZE} total={total} count={materialRows.length} onOffsetChange={setOffset} />
        </div>
      </Card>

      <Modal
        open={!!draftQuiz}
        onOpenChange={(open) => !open && setDraftQuiz(null)}
        title={draftQuiz ? t("teacher.materials.suggestedQuizTitle", { topic: draftQuiz.topic }) : ""}
        description={t("teacher.materials.suggestedQuizDesc")}
        size="lg"
      >
        {draftQuiz && (
          <div className="space-y-4">
            <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
              {draftQuiz.questions.map((q, i) => (
                <div key={i} className="rounded-xl bg-slate-50 px-4 py-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-slate-700">
                      {i + 1}. {q.question}
                    </p>
                    <Badge tone="slate">{q.xp} XP</Badge>
                  </div>
                  {q.type === "mcq" && q.options ? (
                    <ul className="mt-2 space-y-1">
                      {q.options.map((o, oi) => (
                        <li
                          key={oi}
                          className={
                            "text-sm " +
                            (oi === q.answer_index ? "text-brand-700 font-medium" : "text-slate-500")
                          }
                        >
                          {String.fromCharCode(65 + oi)}. {o}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-brand-700 font-medium">{t("teacher.materials.expectedAnswer", { answer: q.expected_answer })}</p>
                  )}
                  {q.explanation && <p className="mt-2 text-xs text-slate-400">{q.explanation}</p>}
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
              <Button variant="ghost" onClick={() => setDraftQuiz(null)}>
                {t("teacher.materials.discard")}
              </Button>
              <Button
                onClick={() => draftQuiz && approveDraft.mutate(draftQuiz.quiz_id)}
                disabled={approveDraft.isPending}
              >
                {approveDraft.isPending ? t("teacher.materials.publishing") : t("teacher.materials.approveAndPublish")}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
