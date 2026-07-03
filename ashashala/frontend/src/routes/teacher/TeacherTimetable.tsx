import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, Input, Label } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function TeacherTimetable() {
  const toast = useToast();
  const [form, setForm] = useState({ class_id: "", subject_id: "", day_of_week: 0, period_number: 1, room: "" });

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
        <div className="p-5 grid md:grid-cols-3 gap-3 items-end">
          <div>
            <Label>Class id</Label>
            <Input value={form.class_id} onChange={(e) => setForm({ ...form, class_id: e.target.value })} />
          </div>
          <div>
            <Label>Subject id</Label>
            <Input value={form.subject_id} onChange={(e) => setForm({ ...form, subject_id: e.target.value })} />
          </div>
          <div>
            <Label>Day</Label>
            <select
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
              value={form.day_of_week}
              onChange={(e) => setForm({ ...form, day_of_week: Number(e.target.value) })}
            >
              {DAYS.map((d, i) => (
                <option key={d} value={i}>
                  {d}
                </option>
              ))}
            </select>
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
      </Card>
    </div>
  );
}
