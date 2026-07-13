import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Input, Select, Skeleton, Table } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { useToast } from "../../components/ui/Toast";

export default function TeacherAssignments() {
  const { t } = useTranslation();
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
      toast.push(t("teacher.assignments.assignmentCreated"), "success");
      setTopic("");
      setDueDate("");
      qc.invalidateQueries({ queryKey: ["teacher", "assignment-tasks"] });
    },
    onError: () => toast.push(t("teacher.assignments.assignmentCreateFailed"), "error"),
  });

  const rows = tasks.data ?? [];

  return (
    <div>
      <PageTitle subtitle={t("teacher.assignments.subtitle")}>
        {t("teacher.assignments.title")}
      </PageTitle>

      <Card className="mb-6">
        <CardHeader title={t("teacher.assignments.newAssignment")} />
        {!assignments.isLoading && !assignments.data?.length ? (
          <div className="p-5">
            <EmptyState title={t("teacher.assignments.noClassAssignments")} hint={t("teacher.assignments.noClassAssignmentsHint")} />
          </div>
        ) : (
          <div className="p-5 grid md:grid-cols-5 gap-3 items-start">
            <FormField label={t("teacher.assignments.class")}>
              <Select value={classId} onChange={(e) => { setClassId(e.target.value); setSubjectId(""); }}>
                <option value="">{assignments.isLoading ? t("common.loading") : t("teacher.assignments.selectAClass")}</option>
                {classOptions.map(([id, name]) => (
                  <option key={id} value={id}>{name}</option>
                ))}
              </Select>
            </FormField>
            <FormField label={t("teacher.assignments.subject")} optional>
              <Select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} disabled={!classId}>
                <option value="">{t("teacher.assignments.noSpecificSubject")}</option>
                {subjectsForClass.map((a) => (
                  <option key={a.subject_id} value={a.subject_id}>{a.subject_name}</option>
                ))}
              </Select>
            </FormField>
            <FormField label={t("teacher.assignments.topic")}>
              <Input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder={t("teacher.assignments.topicPlaceholder")} />
            </FormField>
            <FormField label={t("teacher.assignments.dueDate")}>
              <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
            </FormField>
            <Button
              onClick={() => create.mutate()}
              disabled={!classId || !topic || !dueDate || create.isPending}
              className="mt-6"
            >
              {create.isPending ? t("teacher.assignments.generating") : t("teacher.assignments.createAndPublish")}
            </Button>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title={t("teacher.assignments.assignmentsCard")} />
        <div className="p-2">
          {tasks.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !rows.length ? (
            <EmptyState title={t("teacher.assignments.noAssignmentsYet")} hint={t("teacher.assignments.noAssignmentsYetHint")} />
          ) : (
            <Table head={[t("teacher.assignments.colTopic"), t("teacher.assignments.colClass"), t("teacher.assignments.colDue"), t("teacher.assignments.colSubmissions"), t("teacher.assignments.colStatus")]}>
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
