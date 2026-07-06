import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, EmptyState, Input, Label, Select } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function TeacherTimetable() {
  const toast = useToast();
  const assignments = useQuery({ queryKey: ["teacher", "assignments"], queryFn: teacherApi.assignments });
  const [form, setForm] = useState({ class_id: "", subject_id: "", day_of_week: 0, period_number: 1, room: "" });

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
    onSuccess: () => toast.push("Period added.", "success"),
    onError: () => toast.push("Failed — check your assignment for this class/subject.", "error"),
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
    </div>
  );
}
