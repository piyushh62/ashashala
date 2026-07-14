import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { z } from "zod";
import { teacherApi } from "../../api/endpoints";
import type { SuggestedQuizOut } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Input, Pager, Select, Skeleton, Table } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { Modal } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";

type Tab = "file" | "url" | "youtube";

const PAGE_SIZE = 20;

const urlSchema = z.string().url("Enter a valid URL (including https://)");
const youtubeSchema = urlSchema.refine((v) => /youtu\.?be/.test(v), "Enter a valid YouTube URL");

const URL_VALIDATION_MESSAGE_KEYS: Record<string, string> = {
  "Enter a valid URL (including https://)": "teacher.materials.invalidUrl",
  "Enter a valid YouTube URL": "teacher.materials.invalidYoutubeUrl",
};

export default function TeacherMaterials() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("file");
  const [classId, setClassId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [url, setUrl] = useState("");
  const [urlError, setUrlError] = useState<string | undefined>();
  const [file, setFile] = useState<File | null>(null);
  const [offset, setOffset] = useState(0);
  const [draftQuiz, setDraftQuiz] = useState<SuggestedQuizOut | null>(null);

  const assignments = useQuery({ queryKey: ["teacher", "assignments"], queryFn: teacherApi.assignments });
  const materials = useQuery({
    queryKey: ["teacher", "materials", offset],
    queryFn: () => teacherApi.materials(PAGE_SIZE, offset),
  });
  const materialRows = materials.data?.items ?? [];
  const total = materials.data?.total ?? 0;

  // Subjects taught in the currently-selected class (a teacher can be assigned
  // to the same class for several subjects).
  const subjectsForClass = useMemo(
    () => (assignments.data ?? []).filter((a) => a.class_id === classId),
    [assignments.data, classId],
  );
  const classOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const a of assignments.data ?? []) seen.set(a.class_id, a.class_name);
    return Array.from(seen.entries());
  }, [assignments.data]);

  // Default to the teacher's first assignment once loaded.
  useEffect(() => {
    if (!classId && assignments.data?.length) {
      setClassId(assignments.data[0].class_id);
      setSubjectId(assignments.data[0].subject_id);
    }
  }, [assignments.data, classId]);

  const done = () => {
    toast.push(t("teacher.materials.uploaded"), "success");
    setUrl("");
    setFile(null);
    setOffset(0);
    qc.invalidateQueries({ queryKey: ["teacher", "materials"] });
  };
  const fail = () => toast.push(t("teacher.materials.uploadFailed"), "error");

  const upFile = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      fd.append("file", file!);
      fd.append("class_id", classId);
      if (subjectId) fd.append("subject_id", subjectId);
      return teacherApi.uploadFile(fd);
    },
    onSuccess: done,
    onError: fail,
  });
  const upUrl = useMutation({
    mutationFn: () => teacherApi.uploadUrl({ class_id: classId, subject_id: subjectId || undefined, url }),
    onSuccess: done,
    onError: fail,
  });
  const upYt = useMutation({
    mutationFn: () => teacherApi.uploadYoutube({ class_id: classId, subject_id: subjectId || undefined, url }),
    onSuccess: done,
    onError: fail,
  });

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

  const submit = () => {
    if (tab === "file") {
      upFile.mutate();
      return;
    }
    const schema = tab === "youtube" ? youtubeSchema : urlSchema;
    const result = schema.safeParse(url);
    if (!result.success) {
      setUrlError(result.error.issues[0]?.message);
      return;
    }
    setUrlError(undefined);
    if (tab === "url") upUrl.mutate();
    else upYt.mutate();
  };

  return (
    <div>
      <PageTitle subtitle={t("teacher.materials.subtitle")}>{t("teacher.materials.title")}</PageTitle>

      <Card className="mb-6">
        <CardHeader title={t("teacher.materials.addMaterial")} />
        <div className="px-5 pt-4 flex gap-2">
          {(["file", "url", "youtube"] as Tab[]).map((tabOption) => (
            <button
              key={tabOption}
              onClick={() => {
                setTab(tabOption);
                setUrlError(undefined);
              }}
              className={`px-3 py-1.5 rounded-lg text-sm ${
                tab === tabOption ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              {tabOption === "file" ? t("teacher.materials.tabFile") : tabOption === "url" ? t("teacher.materials.tabUrl") : t("teacher.materials.tabYoutube")}
            </button>
          ))}
        </div>
        {!assignments.isLoading && !assignments.data?.length ? (
          <div className="p-5">
            <EmptyState title={t("teacher.materials.noClassAssignments")} hint={t("teacher.materials.noClassAssignmentsHint")} />
          </div>
        ) : (
          <div className="p-5 grid md:grid-cols-3 gap-3 items-start">
            <FormField label={t("teacher.materials.class")}>
              <Select value={classId} onChange={(e) => { setClassId(e.target.value); setSubjectId(""); }}>
                <option value="">{assignments.isLoading ? t("common.loading") : t("teacher.materials.selectAClass")}</option>
                {classOptions.map(([id, name]) => (
                  <option key={id} value={id}>{name}</option>
                ))}
              </Select>
            </FormField>
            <FormField label={t("teacher.materials.subject")} optional>
              <Select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} disabled={!classId}>
                <option value="">{t("teacher.materials.noSpecificSubject")}</option>
                {subjectsForClass.map((a) => (
                  <option key={a.subject_id} value={a.subject_id}>{a.subject_name}</option>
                ))}
              </Select>
            </FormField>
            {tab === "file" ? (
              <FormField label={t("teacher.materials.file")}>
                <input type="file" accept=".pdf,.docx,.txt,.jpg,.png" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              </FormField>
            ) : (
              <FormField
                label={tab === "url" ? t("teacher.materials.url") : t("teacher.materials.youtubeUrl")}
                error={urlError ? t(URL_VALIDATION_MESSAGE_KEYS[urlError] ?? urlError) : undefined}
              >
                <Input
                  value={url}
                  invalid={!!urlError}
                  onChange={(e) => { setUrl(e.target.value); setUrlError(undefined); }}
                  placeholder={t("teacher.materials.urlPlaceholder")}
                />
              </FormField>
            )}
            <Button
              onClick={submit}
              disabled={!classId || (tab === "file" ? !file : !url) || upFile.isPending || upUrl.isPending || upYt.isPending}
            >
              {t("teacher.materials.upload")}
            </Button>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title={t("teacher.materials.myMaterials")} />
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
