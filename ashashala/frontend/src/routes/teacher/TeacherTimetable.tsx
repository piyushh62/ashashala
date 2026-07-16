import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, Icon, Input, Skeleton, Table } from "../../components/ui";
import { DataBoundary } from "../../components/ui/DataBoundary";
import { useConfirm } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";

const DAY_KEYS = ["common.days.mon", "common.days.tue", "common.days.wed", "common.days.thu", "common.days.fri", "common.days.sat"];

export default function TeacherTimetable() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const navigate = useNavigate();
  const assignments = useQuery({ queryKey: ["teacher", "assignments"], queryFn: teacherApi.assignments });
  const timetable = useQuery({ queryKey: ["teacher", "timetable"], queryFn: teacherApi.listTimetable });

  const names = useMemo(() => {
    const classes = new Map<string, string>();
    const subjects = new Map<string, string>();
    for (const a of assignments.data ?? []) {
      classes.set(a.class_id, a.class_name);
      subjects.set(a.subject_id, a.subject_name);
    }
    return { classes, subjects };
  }, [assignments.data]);

  const del = useMutation({
    mutationFn: (id: string) => teacherApi.deleteTimetableEntry(id),
    onSuccess: () => {
      toast.push(t("teacher.timetable.periodRemoved"), "success");
      qc.invalidateQueries({ queryKey: ["teacher", "timetable"] });
    },
    onError: () => toast.push(t("teacher.timetable.periodRemoveFailed"), "error"),
  });

  const updateTopic = useMutation({
    mutationFn: ({ id, topic }: { id: string; topic: string }) => teacherApi.updateTimetableEntry(id, { topic }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teacher", "timetable"] }),
    onError: () => toast.push(t("teacher.timetable.topicUpdateFailed"), "error"),
  });

  return (
    <div>
      <PageTitle subtitle={t("teacher.timetable.subtitle")}>{t("teacher.timetable.title")}</PageTitle>

      <Card>
        <CardHeader
          title={t("teacher.timetable.myWeeklyPeriods")}
          action={
            <Button size="sm" onClick={() => navigate("/teacher/timetable/new")}>
              <Icon name="add" className="w-4 h-4" />
              {t("teacher.timetable.addAPeriod")}
            </Button>
          }
        />
        <DataBoundary
          query={timetable}
          isEmpty={(d) => d.length === 0}
          emptyTitle={t("teacher.timetable.noPeriodsScheduled")}
          emptyHint={t("teacher.timetable.noPeriodsScheduledHint")}
          loadingFallback={<Skeleton className="h-24 m-3" />}
        >
          {(rows) => (
            <Table head={[t("teacher.timetable.colDay"), t("teacher.timetable.colPeriod"), t("teacher.timetable.colClass"), t("teacher.timetable.colSubject"), t("teacher.timetable.colRoom"), t("teacher.timetable.colTopic"), ""]}>
              {[...rows]
                .sort((a, b) => a.day_of_week - b.day_of_week || a.period_number - b.period_number)
                .map((r) => (
                  <tr key={r.id} className="border-b border-slate-50">
                    <td className="px-4 py-2 font-medium text-slate-700">{t(DAY_KEYS[r.day_of_week])}</td>
                    <td className="px-4 py-2 text-slate-500">{r.period_number}</td>
                    <td className="px-4 py-2 text-slate-500">{names.classes.get(r.class_id) ?? r.class_id}</td>
                    <td className="px-4 py-2 text-slate-500">{names.subjects.get(r.subject_id) ?? r.subject_id}</td>
                    <td className="px-4 py-2 text-slate-500">{r.room || "—"}</td>
                    <td className="px-4 py-2 text-slate-500">
                      <Input
                        defaultValue={r.topic ?? ""}
                        placeholder={t("teacher.timetable.topicPlaceholder")}
                        className="!py-1 !px-2 text-sm w-40"
                        onBlur={(e) => {
                          const topic = e.target.value;
                          if (topic !== (r.topic ?? "")) updateTopic.mutate({ id: r.id, topic });
                        }}
                      />
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => confirm.ask({
                          title: t("teacher.timetable.removePeriodTitle"),
                          description: t("teacher.timetable.removePeriodDesc", { day: t(DAY_KEYS[r.day_of_week]), period: r.period_number }),
                          confirmLabel: t("teacher.timetable.remove"),
                          onConfirm: () => del.mutateAsync(r.id),
                        })}
                      >
                        {t("teacher.timetable.remove")}
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
