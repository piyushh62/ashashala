import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { parentApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, EmptyState, Select, Skeleton, Textarea } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";

export default function ParentMessages() {
  const { t } = useTranslation();
  const { id = "" } = useParams();
  const toast = useToast();
  const qc = useQueryClient();
  const teachers = useQuery({ queryKey: ["parent", "child", id, "teachers"], queryFn: () => parentApi.childTeachers(id) });
  const [teacherId, setTeacherId] = useState("");
  const [body, setBody] = useState("");

  const thread = useQuery({
    queryKey: ["parent", "messages", id, teacherId],
    queryFn: () => parentApi.listMessages(id, teacherId),
    enabled: !!teacherId,
    refetchInterval: teacherId ? 15000 : false,
  });

  const send = useMutation({
    mutationFn: () => parentApi.sendMessage({ student_id: id, teacher_id: teacherId, body }),
    onSuccess: () => {
      setBody("");
      qc.invalidateQueries({ queryKey: ["parent", "messages", id, teacherId] });
    },
    onError: () => toast.push(t("parent.messages.sendFailed"), "error"),
  });

  return (
    <div>
      <Link to={`/parent/child/${id}`} className="text-sm text-brand-600 hover:underline">
        {t("parent.back")}
      </Link>
      <PageTitle subtitle={t("parent.messages.subtitle")}>{t("parent.messages.title")}</PageTitle>

      <Card className="mb-6">
        <CardHeader title={t("parent.messages.pickTeacher")} />
        {!teachers.isLoading && !teachers.data?.length ? (
          <div className="p-5">
            <EmptyState title={t("parent.messages.noTeachersFound")} hint={t("parent.messages.noTeachersFoundHint")} />
          </div>
        ) : (
          <div className="p-5">
            <Select value={teacherId} onChange={(e) => setTeacherId(e.target.value)}>
              <option value="">{teachers.isLoading ? t("common.loading") : t("parent.messages.selectTeacher")}</option>
              {(teachers.data ?? []).map((tch) => (
                <option key={`${tch.teacher_id}-${tch.subject_id}`} value={tch.teacher_id}>
                  {tch.teacher_name} · {tch.subject_name}
                </option>
              ))}
            </Select>
          </div>
        )}
      </Card>

      {teacherId && (
        <Card>
          <CardHeader title={t("parent.messages.conversation")} />
          <div className="p-5 space-y-4">
            {thread.isLoading ? (
              <Skeleton className="h-32" />
            ) : !thread.data?.length ? (
              <p className="text-sm text-slate-400 text-center py-4">{t("parent.messages.noMessagesYet")}</p>
            ) : (
              <div className="space-y-2.5 max-h-96 overflow-y-auto">
                {thread.data.map((m) => (
                  <div
                    key={m.id}
                    className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm ${
                      m.sender_role === "parent"
                        ? "ml-auto bg-brand-600 text-white"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    <p>{m.body}</p>
                    <p className={`text-[11px] mt-1 ${m.sender_role === "parent" ? "text-white/70" : "text-slate-400"}`}>
                      {new Date(m.created_at).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
            <form
              className="flex gap-2.5"
              onSubmit={(e) => {
                e.preventDefault();
                if (body.trim()) send.mutate();
              }}
            >
              <Textarea
                className="flex-1"
                rows={2}
                placeholder={t("parent.messages.messagePlaceholder")}
                value={body}
                onChange={(e) => setBody(e.target.value)}
              />
              <Button type="submit" disabled={!body.trim() || send.isPending}>
                {send.isPending ? t("parent.messages.sending") : t("parent.messages.send")}
              </Button>
            </form>
          </div>
        </Card>
      )}
    </div>
  );
}
