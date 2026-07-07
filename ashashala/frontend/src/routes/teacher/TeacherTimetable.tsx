import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, EmptyState, Input, Label, Select, Skeleton, Table } from "../../components/ui";
import { DataBoundary } from "../../components/ui/DataBoundary";
import { useConfirm } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function TeacherTimetable() {
  const toast = useToast();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const assignments = useQuery({ queryKey: ["teacher", "assignments"], queryFn: teacherApi.assignments });
  const timetable = useQuery({ queryKey: ["teacher", "timetable"], queryFn: teacherApi.listTimetable });
  const [form, setForm] = useState({ class_id: "", subject_id: "", day_of_week: 0, period_number: 1, room: "" });

  const names = useMemo(() => {
    const classes = new Map<string, string>();
    const subjects = new Map<string, string>();
    for (const a of assignments.data ?? []) {
      classes.set(a.class_id, a.class_name);
      subjects.set(a.subject_id, a.subject_name);
    }
    return { classes, subjects };
  }, [assignments.data]);

  const classOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const a of assignments.data ?? []) seen.set(a.class_id, a.class_name);
    return Array.from(seen.entries());
  }, [assignments.data]);
  const subjectsForClass = useMemo(
    () => (assignments.data ?? []).filter((a) => a.class_id === form.class_id),
    [assignments.data, form.class_id],
  );

  useEffect(() => {
    if (!form.class_id && assignments.data?.length) {
      setForm((f) => ({ ...f, class_id: assignments.data![0].class_id, subject_id: assignments.data![0].subject_id }));
    }
  }, [assignments.data, form.class_id]);

  const create = useMutation({
    mutationFn: () =>
      teacherApi.createTimetable({
        class_id: form.class_id,
        subject_id: form.subject_id,
        day_of_week: form.day_of_week,
        period_number: form.period_number,
        room: form.room || undefined,
      }),
    onSuccess: () => {
      toast.push("Period added.", "success");
      qc.invalidateQueries({ queryKey: ["teacher", "timetable"] });
    },
    onError: () => toast.push("Failed — check your assignment for this class/subject.", "error"),
  });

  const del = useMutation({
    mutationFn: (id: string) => teacherApi.deleteTimetableEntry(id),
    onSuccess: () => {
      toast.push("Period removed.", "success");
      qc.invalidateQueries({ queryKey: ["teacher", "timetable"] });
    },
    onError: () => toast.push("Couldn't remove period.", "error"),
  });

  return (
    <div>
      <PageTitle subtitle="Add weekly recurring periods.">Timetable</PageTitle>
      <Card>
        <CardHeader title="Add a period" />
        {!assignments.isLoading && !assignments.data?.length ? (
          <div className="p-5">
            <EmptyState title="No class assignments yet" hint="Ask your school admin to assign you to a class and subject first." />
          </div>
        ) : (
          <div className="p-5 grid md:grid-cols-3 gap-3 items-end">
            <div>
              <Label>Class</Label>
              <Select
                value={form.class_id}
                onChange={(e) => setForm({ ...form, class_id: e.target.value, subject_id: "" })}
              >
                <option value="">{assignments.isLoading ? "Loading…" : "Select a class"}</option>
                {classOptions.map(([id, name]) => (
                  <option key={id} value={id}>{name}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label>Subject</Label>
              <Select
                value={form.subject_id}
                onChange={(e) => setForm({ ...form, subject_id: e.target.value })}
                disabled={!form.class_id}
              >
                <option value="">Select a subject</option>
                {subjectsForClass.map((a) => (
                  <option key={a.subject_id} value={a.subject_id}>{a.subject_name}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label>Day</Label>
              <Select
                value={form.day_of_week}
                onChange={(e) => setForm({ ...form, day_of_week: Number(e.target.value) })}
              >
                {DAYS.map((d, i) => (
                  <option key={d} value={i}>
                    {d}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label>Period</Label>
              <Input
                type="number"
                min={1}
                value={form.period_number}
                onChange={(e) => setForm({ ...form, period_number: Number(e.target.value) })}
              />
            </div>
            <div>
              <Label>Room</Label>
              <Input value={form.room} onChange={(e) => setForm({ ...form, room: e.target.value })} />
            </div>
            <Button onClick={() => create.mutate()} disabled={!form.class_id || !form.subject_id}>
              Add period
            </Button>
          </div>
        )}
      </Card>

      <Card className="mt-6">
        <CardHeader title="My weekly periods" />
        <DataBoundary
          query={timetable}
          isEmpty={(d) => d.length === 0}
          emptyTitle="No periods scheduled yet"
          emptyHint="Add a period above to see it here."
          loadingFallback={<Skeleton className="h-24 m-3" />}
        >
          {(rows) => (
            <Table head={["Day", "Period", "Class", "Subject", "Room", ""]}>
              {[...rows]
                .sort((a, b) => a.day_of_week - b.day_of_week || a.period_number - b.period_number)
                .map((r) => (
                  <tr key={r.id} className="border-b border-slate-50">
                    <td className="px-4 py-2 font-medium text-slate-700">{DAYS[r.day_of_week]}</td>
                    <td className="px-4 py-2 text-slate-500">{r.period_number}</td>
                    <td className="px-4 py-2 text-slate-500">{names.classes.get(r.class_id) ?? r.class_id}</td>
                    <td className="px-4 py-2 text-slate-500">{names.subjects.get(r.subject_id) ?? r.subject_id}</td>
                    <td className="px-4 py-2 text-slate-500">{r.room || "—"}</td>
                    <td className="px-4 py-2 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => confirm.ask({
                          title: "Remove this period?",
                          description: `${DAYS[r.day_of_week]}, period ${r.period_number} will be removed from your timetable.`,
                          confirmLabel: "Remove",
                          onConfirm: () => del.mutateAsync(r.id),
                        })}
                      >
                        Remove
                      </Button>
                    </td>
                  </tr>
                ))}
            </Table>
          )}
        </DataBoundary>
      </Card>
      {confirm.dialog}
    </div>
  );
}
