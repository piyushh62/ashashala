import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Icon, Input, Label, Select } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";
import type { TimetableOptionOut } from "../../types/api";

const DAY_KEYS = ["common.days.mon", "common.days.tue", "common.days.wed", "common.days.thu", "common.days.fri", "common.days.sat"];

export default function TeacherTimetableCreate() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const navigate = useNavigate();
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

  const goToList = () => {
    qc.invalidateQueries({ queryKey: ["teacher", "timetable"] });
    navigate("/teacher/timetable");
  };

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
      toast.push(t("teacher.timetable.periodAdded"), "success");
      goToList();
    },
    onError: () => toast.push(t("teacher.timetable.periodAddFailed"), "error"),
  });

  const [periodsPerWeek, setPeriodsPerWeek] = useState(3);
  const [options, setOptions] = useState<TimetableOptionOut[] | null>(null);

  const aiSuggest = useMutation({
    mutationFn: () =>
      teacherApi.aiSuggestTimetable({
        class_id: form.class_id,
        subject_id: form.subject_id,
        periods_per_week: periodsPerWeek,
      }),
    onSuccess: (opts) => setOptions(opts),
    onError: () => toast.push(t("teacher.timetable.suggestFailed"), "error"),
  });

  const selectOption = useMutation({
    mutationFn: (optionId: string) => teacherApi.selectTimetableOption(optionId),
    onSuccess: () => {
      toast.push(t("teacher.timetable.periodsAddedFromSuggestion"), "success");
      setOptions(null);
      goToList();
    },
    onError: (err: any) => {
      if (err?.status === 422) toast.push(t("teacher.timetable.optionNoLongerFree"), "error");
      else toast.push(t("teacher.timetable.applySuggestionFailed"), "error");
    },
  });

  return (
    <div>
      <PageTitle subtitle={t("teacher.timetable.subtitle")}>{t("teacher.timetable.addAPeriod")}</PageTitle>
      <Card>
        <CardHeader title={t("teacher.timetable.addAPeriod")} />
        {!assignments.isLoading && !assignments.data?.length ? (
          <div className="p-5">
            <EmptyState title={t("teacher.timetable.noClassAssignments")} hint={t("teacher.timetable.noClassAssignmentsHint")} />
          </div>
        ) : (
          <div className="p-5 grid md:grid-cols-3 gap-3 items-end">
            <div>
              <Label>{t("teacher.timetable.class")}</Label>
              <Select
                value={form.class_id}
                onChange={(e) => setForm({ ...form, class_id: e.target.value, subject_id: "" })}
              >
                <option value="">{assignments.isLoading ? t("common.loading") : t("teacher.timetable.selectAClass")}</option>
                {classOptions.map(([id, name]) => (
                  <option key={id} value={id}>{name}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label>{t("teacher.timetable.subject")}</Label>
              <Select
                value={form.subject_id}
                onChange={(e) => setForm({ ...form, subject_id: e.target.value })}
                disabled={!form.class_id}
              >
                <option value="">{t("teacher.timetable.selectASubject")}</option>
                {subjectsForClass.map((a) => (
                  <option key={a.subject_id} value={a.subject_id}>{a.subject_name}</option>
                ))}
              </Select>
            </div>
            <div>
              <Label>{t("teacher.timetable.day")}</Label>
              <Select
                value={form.day_of_week}
                onChange={(e) => setForm({ ...form, day_of_week: Number(e.target.value) })}
              >
                {DAY_KEYS.map((key, i) => (
                  <option key={key} value={i}>
                    {t(key)}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label>{t("teacher.timetable.period")}</Label>
              <Input
                type="number"
                min={1}
                value={form.period_number}
                onChange={(e) => setForm({ ...form, period_number: Number(e.target.value) })}
              />
            </div>
            <div>
              <Label>{t("teacher.timetable.room")}</Label>
              <Input value={form.room} onChange={(e) => setForm({ ...form, room: e.target.value })} />
            </div>
            <Button onClick={() => create.mutate()} disabled={!form.class_id || !form.subject_id}>
              {t("teacher.timetable.addPeriod")}
            </Button>
          </div>
        )}
      </Card>

      <Card className="mt-6">
        <CardHeader
          title={t("teacher.timetable.aiSuggest")}
          subtitle={t("teacher.timetable.aiSuggestSubtitle")}
        />
        <div className="p-5">
          <div className="flex flex-wrap items-end gap-3 mb-4">
            <div>
              <Label>{t("teacher.timetable.periodsPerWeek")}</Label>
              <Input
                type="number"
                min={1}
                max={10}
                className="w-28"
                value={periodsPerWeek}
                onChange={(e) => setPeriodsPerWeek(Number(e.target.value))}
              />
            </div>
            <Button
              variant="subtle"
              onClick={() => aiSuggest.mutate()}
              disabled={!form.class_id || !form.subject_id || aiSuggest.isPending}
            >
              {aiSuggest.isPending ? (
                t("teacher.timetable.generating")
              ) : (
                <>
                  <Icon name="sparkles" className="w-4 h-4" />
                  {t("teacher.timetable.suggestOptions")}
                </>
              )}
            </Button>
          </div>

          {options && (
            <div className="grid md:grid-cols-2 gap-4">
              {options.map((opt) => (
                <div key={opt.option_id} className="rounded-xl border border-slate-200 dark:border-slate-800 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <Badge tone="brand">{opt.strategy}</Badge>
                  </div>
                  <p className="text-sm text-slate-500 mb-3">{opt.rationale}</p>
                  <ul className="text-sm space-y-1 mb-4">
                    {opt.slots.map((s, i) => (
                      <li key={i} className="flex justify-between text-slate-600">
                        <span>{t("teacher.timetable.periodLabel", { day: t(DAY_KEYS[s.day_of_week]), period: s.period_number })}</span>
                        <span className="text-slate-400">{s.room || "—"}</span>
                      </li>
                    ))}
                  </ul>
                  <Button
                    size="sm"
                    className="w-full"
                    onClick={() => selectOption.mutate(opt.option_id)}
                    disabled={selectOption.isPending}
                  >
                    {t("teacher.timetable.useThisOption")}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
