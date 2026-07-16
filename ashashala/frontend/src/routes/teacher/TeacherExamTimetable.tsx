import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, EmptyState, Input, Label, Select, Skeleton, Table } from "../../components/ui";
import { DatePicker } from "../../components/ui/DatePicker";
import { DataBoundary } from "../../components/ui/DataBoundary";
import { useToast } from "../../components/ui/Toast";
import { formatDate } from "../../lib/dates";

export default function TeacherExamTimetable() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const assignments = useQuery({ queryKey: ["teacher", "assignments"], queryFn: teacherApi.assignments });
  const exams = useQuery({ queryKey: ["teacher", "exam-timetable"], queryFn: () => teacherApi.examTimetable() });
  const [form, setForm] = useState({
    class_id: "",
    subject_id: "",
    exam_name: "",
    exam_date: "",
    start_time: "",
    duration_minutes: "",
    syllabus_ref: "",
  });

  const classOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const a of assignments.data ?? []) seen.set(a.class_id, a.class_name);
    return Array.from(seen.entries());
  }, [assignments.data]);
  const subjectsForClass = useMemo(
    () => (assignments.data ?? []).filter((a) => a.class_id === form.class_id),
    [assignments.data, form.class_id],
  );
  const names = useMemo(() => {
    const classes = new Map<string, string>();
    const subjects = new Map<string, string>();
    for (const a of assignments.data ?? []) {
      classes.set(a.class_id, a.class_name);
      subjects.set(a.subject_id, a.subject_name);
    }
    return { classes, subjects };
  }, [assignments.data]);

  useEffect(() => {
    if (!form.class_id && assignments.data?.length) {
      setForm((f) => ({ ...f, class_id: assignments.data![0].class_id, subject_id: assignments.data![0].subject_id }));
    }
  }, [assignments.data, form.class_id]);

  const create = useMutation({
    mutationFn: () =>
      teacherApi.createExamTimetable({
        class_id: form.class_id,
        subject_id: form.subject_id,
        exam_name: form.exam_name,
        exam_date: form.exam_date,
        start_time: form.start_time || undefined,
        duration_minutes: form.duration_minutes ? Number(form.duration_minutes) : undefined,
        syllabus_ref: form.syllabus_ref || undefined,
      }),
    onSuccess: () => {
      toast.push(t("teacher.examTimetable.examScheduled"), "success");
      setForm((f) => ({ ...f, exam_name: "", exam_date: "", start_time: "", duration_minutes: "", syllabus_ref: "" }));
      qc.invalidateQueries({ queryKey: ["teacher", "exam-timetable"] });
    },
    onError: () => toast.push(t("teacher.examTimetable.scheduleExamFailed"), "error"),
  });

  return (
    <div>
      <PageTitle subtitle={t("teacher.examTimetable.subtitle")}>{t("teacher.examTimetable.title")}</PageTitle>

      <Card>
        <CardHeader title={t("teacher.examTimetable.scheduleExam")} />
        {!assignments.isLoading && !assignments.data?.length ? (
          <div className="p-5">
            <EmptyState title={t("teacher.examTimetable.noClassAssignments")} hint={t("teacher.examTimetable.noClassAssignmentsHint")} />
          </div>
        ) : (
          <form
            className="p-5 grid md:grid-cols-3 gap-3 items-end"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate();
            }}
          >
            <div>
              <Label>{t("teacher.examTimetable.class")}</Label>
              <Select
                value={form.class_id}
                onChange={(e) => setForm({ ...form, class_id: e.target.value, subject_id: "" })}
              >
                <option value="">{assignments.isLoading ? t("common.loading") : t("teacher.examTimetable.selectAClass")}</option>
                {classOptions.map(([id, name]) => (
                  <option key={id} value={id}>{name}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label>{t("teacher.examTimetable.subject")}</Label>
              <Select
                value={form.subject_id}
                onChange={(e) => setForm({ ...form, subject_id: e.target.value })}
                disabled={!form.class_id}
              >
                <option value="">{t("teacher.examTimetable.selectASubject")}</option>
                {subjectsForClass.map((a) => (
                  <option key={a.subject_id} value={a.subject_id}>{a.subject_name}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label>{t("teacher.examTimetable.examName")}</Label>
              <Input value={form.exam_name} onChange={(e) => setForm({ ...form, exam_name: e.target.value })} />
            </div>
            <div>
              <Label>{t("teacher.examTimetable.date")}</Label>
              <DatePicker
                value={form.exam_date}
                onChange={(iso) => setForm({ ...form, exam_date: iso })}
                placeholder={t("teacher.examTimetable.selectDate")}
              />
            </div>
            <div>
              <Label>{t("teacher.examTimetable.startTime")}</Label>
              <Input type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} />
            </div>
            <div>
              <Label>{t("teacher.examTimetable.durationMin")}</Label>
              <Input
                type="number"
                min={1}
                value={form.duration_minutes}
                onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })}
              />
            </div>
            <div className="md:col-span-2">
              <Label>{t("teacher.examTimetable.syllabusRef")}</Label>
              <Input value={form.syllabus_ref} onChange={(e) => setForm({ ...form, syllabus_ref: e.target.value })} />
            </div>
            <Button
              type="submit"
              disabled={!form.class_id || !form.subject_id || !form.exam_name || !form.exam_date || create.isPending}
            >
              {create.isPending ? t("teacher.examTimetable.scheduling") : t("teacher.examTimetable.scheduleExamBtn")}
            </Button>
          </form>
        )}
      </Card>

      <Card className="mt-6">
        <CardHeader title={t("teacher.examTimetable.scheduledExams")} />
        <DataBoundary
          query={exams}
          isEmpty={(d) => d.length === 0}
          emptyTitle={t("teacher.examTimetable.noExamsScheduled")}
          loadingFallback={<Skeleton className="h-24 m-3" />}
        >
          {(rows) => (
            <Table head={[t("teacher.examTimetable.colExam"), t("teacher.examTimetable.colClass"), t("teacher.examTimetable.colSubject"), t("teacher.examTimetable.colDate"), t("teacher.examTimetable.colTime"), t("teacher.examTimetable.colDuration")]}>
              {[...rows]
                .sort((a, b) => a.exam_date.localeCompare(b.exam_date))
                .map((e) => (
                  <tr key={e.id} className="border-b border-slate-50">
                    <td className="px-4 py-2 font-medium text-slate-700">{e.exam_name}</td>
                    <td className="px-4 py-2 text-slate-500">{names.classes.get(e.class_id) ?? e.class_id}</td>
                    <td className="px-4 py-2 text-slate-500">{names.subjects.get(e.subject_id) ?? e.subject_id}</td>
                    <td className="px-4 py-2 text-slate-500">{formatDate(e.exam_date)}</td>
                    <td className="px-4 py-2 text-slate-500">{e.start_time ?? "—"}</td>
                    <td className="px-4 py-2 text-slate-500">{e.duration_minutes ? `${e.duration_minutes}m` : "—"}</td>
                  </tr>
                ))}
            </Table>
          )}
        </DataBoundary>
      </Card>
    </div>
  );
}
