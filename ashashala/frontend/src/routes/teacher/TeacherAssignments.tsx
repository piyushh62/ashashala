import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Input, Select, Skeleton, Table } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { useToast } from "../../components/ui/Toast";

export default function TeacherAssignments() {
  const toast = useToast();
  const qc = useQueryClient();
  const [classId, setClassId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [topic, setTopic] = useState("");
  const [dueDate, setDueDate] = useState("");

  const assignments = useQuery({ queryKey: ["teacher", "assignments"], queryFn: teacherApi.assignments });
  const tasks = useQuery({ queryKey: ["teacher", "assignment-tasks"], queryFn: teacherApi.listAssignmentTasks });

  const subjectsForClass = useMemo(
    () => (assignments.data ?? []).filter((a) => a.class_id === classId),
    [assignments.data, classId],
  );
  const classOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const a of assignments.data ?? []) seen.set(a.class_id, a.class_name);
    return Array.from(seen.entries());
  }, [assignments.data]);

  useEffect(() => {
    if (!classId && assignments.data?.length) {
      setClassId(assignments.data[0].class_id);
      setSubjectId(assignments.data[0].subject_id);
    }
  }, [assignments.data, classId]);

  const create = useMutation({
    mutationFn: () =>
      teacherApi.createAssignmentTask({
        class_id: classId,
        subject_id: subjectId || undefined,
        topic,
        due_date: dueDate,
      }),
    onSuccess: () => {
      toast.push("Assignment created and published to students.", "success");
      setTopic("");
      setDueDate("");
      qc.invalidateQueries({ queryKey: ["teacher", "assignment-tasks"] });
    },
    onError: () => toast.push("Couldn't create the assignment — check your class assignment.", "error"),
  });

  const rows = tasks.data ?? [];

  return (
    <div>
      <PageTitle subtitle="Pick a topic, we'll generate the quiz and publish it to the class.">
        Assignment Builder
      </PageTitle>

      <Card className="mb-6">
        <CardHeader title="New assignment" />
        {!assignments.isLoading && !assignments.data?.length ? (
          <div className="p-5">
            <EmptyState title="No class assignments yet" hint="Ask your school admin to assign you to a class and subject first." />
          </div>
        ) : (
          <div className="p-5 grid md:grid-cols-5 gap-3 items-start">
            <FormField label="Class">
              <Select value={classId} onChange={(e) => { setClassId(e.target.value); setSubjectId(""); }}>
                <option value="">{assignments.isLoading ? "Loading…" : "Select a class"}</option>
                {classOptions.map(([id, name]) => (
                  <option key={id} value={id}>{name}</option>
                ))}
              </Select>
            </FormField>
            <FormField label="Subject" optional>
              <Select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} disabled={!classId}>
                <option value="">No specific subject</option>
                {subjectsForClass.map((a) => (
                  <option key={a.subject_id} value={a.subject_id}>{a.subject_name}</option>
                ))}
              </Select>
            </FormField>
            <FormField label="Topic">
              <Input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. Photosynthesis" />
            </FormField>
            <FormField label="Due date">
              <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
            </FormField>
            <Button
              onClick={() => create.mutate()}
              disabled={!classId || !topic || !dueDate || create.isPending}
              className="mt-6"
            >
              {create.isPending ? "Generating…" : "Create & publish"}
            </Button>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="Assignments" />
        <div className="p-2">
          {tasks.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !rows.length ? (
            <EmptyState title="No assignments yet" hint="Create one above — it publishes immediately." />
          ) : (
            <Table head={["Topic", "Class", "Due", "Submissions", "Status"]}>
              {rows.map((a) => (
                <tr key={a.id} className="border-b border-slate-50">
                  <td className="px-4 py-2 font-medium text-slate-700">{a.topic}</td>
                  <td className="px-4 py-2 text-slate-500">{a.class_name}</td>
                  <td className="px-4 py-2 text-slate-500">{a.due_date}</td>
                  <td className="px-4 py-2 text-slate-500">{a.submission_count}</td>
                  <td className="px-4 py-2">
                    <Badge tone={a.status === "published" ? "green" : "slate"}>{a.status}</Badge>
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </div>
      </Card>
    </div>
  );
}
