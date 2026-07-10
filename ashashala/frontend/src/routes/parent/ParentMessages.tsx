import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { parentApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, EmptyState, Select, Skeleton, Textarea } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";

export default function ParentMessages() {
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
    onError: () => toast.push("Couldn't send message.", "error"),
  });

  return (
    <div>
      <Link to={`/parent/child/${id}`} className="text-sm text-brand-600 hover:underline">
        ← Back
      </Link>
      <PageTitle subtitle="Message your child's teachers directly.">Messages</PageTitle>

      <Card className="mb-6">
        <CardHeader title="Pick a teacher" />
        {!teachers.isLoading && !teachers.data?.length ? (
          <div className="p-5">
            <EmptyState title="No teachers found" hint="Your child isn't assigned to any class yet." />
          </div>
        ) : (
          <div className="p-5">
            <Select value={teacherId} onChange={(e) => setTeacherId(e.target.value)}>
              <option value="">{teachers.isLoading ? "Loading…" : "Select a teacher"}</option>
              {(teachers.data ?? []).map((t) => (
                <option key={`${t.teacher_id}-${t.subject_id}`} value={t.teacher_id}>
                  {t.teacher_name} · {t.subject_name}
                </option>
              ))}
            </Select>
          </div>
        )}
      </Card>

      {teacherId && (
        <Card>
          <CardHeader title="Conversation" />
          <div className="p-5 space-y-4">
            {thread.isLoading ? (
              <Skeleton className="h-32" />
            ) : !thread.data?.length ? (
              <p className="text-sm text-slate-400 text-center py-4">No messages yet — start the conversation below.</p>
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
                placeholder="Write a message…"
                value={body}
                onChange={(e) => setBody(e.target.value)}
              />
              <Button type="submit" disabled={!body.trim() || send.isPending}>
                {send.isPending ? "Sending…" : "Send"}
              </Button>
            </form>
          </div>
        </Card>
      )}
    </div>
  );
}
