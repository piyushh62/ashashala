import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, EmptyState, Select, Skeleton, Textarea } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";

export default function TeacherMessages() {
  const toast = useToast();
  const qc = useQueryClient();
  const assignments = useQuery({ queryKey: ["teacher", "assignments"], queryFn: teacherApi.assignments });
  const [classId, setClassId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [body, setBody] = useState("");

  const classOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const a of assignments.data ?? []) seen.set(a.class_id, a.class_name);
    return Array.from(seen.entries());
  }, [assignments.data]);

  const progress = useQuery({
    queryKey: ["teacher", "class-progress", classId],
    queryFn: () => teacherApi.classProgress(classId),
    enabled: !!classId,
  });

  const thread = useQuery({
    queryKey: ["teacher", "messages", studentId],
    queryFn: () => teacherApi.listMessages(studentId),
    enabled: !!studentId,
    refetchInterval: studentId ? 15000 : false,
  });

  const send = useMutation({
    mutationFn: () => teacherApi.sendMessage({ student_id: studentId, body }),
    onSuccess: () => {
      setBody("");
      qc.invalidateQueries({ queryKey: ["teacher", "messages", studentId] });
    },
    onError: (err: any) => {
      if (err?.status === 422) toast.push("This student has no linked parent to message.", "error");
      else toast.push("Couldn't send message.", "error");
    },
  });

  return (
    <div>
      <PageTitle subtitle="Message a student's parent directly.">Messages</PageTitle>

      <Card className="mb-6">
        <CardHeader title="Pick a student" />
        {!assignments.isLoading && !assignments.data?.length ? (
          <div className="p-5">
            <EmptyState title="No class assignments yet" hint="Ask your school admin to assign you to a class first." />
          </div>
        ) : (
          <div className="p-5 grid md:grid-cols-2 gap-3">
            <Select
              value={classId}
              onChange={(e) => {
                setClassId(e.target.value);
                setStudentId("");
              }}
            >
              <option value="">{assignments.isLoading ? "Loading…" : "Select a class"}</option>
              {classOptions.map(([id, name]) => (
                <option key={id} value={id}>{name}</option>
              ))}
            </Select>
            <Select value={studentId} onChange={(e) => setStudentId(e.target.value)} disabled={!classId}>
              <option value="">{progress.isLoading ? "Loading…" : "Select a student"}</option>
              {(progress.data ?? []).map((s) => (
                <option key={s.student_id} value={s.student_id}>{s.name}</option>
              ))}
            </Select>
          </div>
        )}
      </Card>

      {studentId && (
        <Card>
          <CardHeader title="Conversation" subtitle="With this student's linked parent(s)." />
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
                      m.sender_role === "teacher"
                        ? "ml-auto bg-brand-600 text-white"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    <p>{m.body}</p>
                    <p className={`text-[11px] mt-1 ${m.sender_role === "teacher" ? "text-white/70" : "text-slate-400"}`}>
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
