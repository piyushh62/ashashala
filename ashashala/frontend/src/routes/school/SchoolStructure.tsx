import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { schoolApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, Input, Label, Select, Skeleton, Table } from "../../components/ui";
import { DataBoundary } from "../../components/ui/DataBoundary";
import { Modal, useConfirm } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";

// Classes, subjects, and the id-based joins (teacher assignment / enrollment /
// parent link) — all pickers are populated by name from the school's real
// classes/subjects/users, so nobody has to type a UUID by hand.
export default function SchoolStructure() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const ok = (m: string) => {
    toast.push(m, "success");
    qc.invalidateQueries({ queryKey: ["school"] });
  };
  const fail = () => toast.push(t("common.requestFailed"), "error");

  const classes = useQuery({ queryKey: ["school", "classes"], queryFn: schoolApi.listClasses });
  const subjects = useQuery({ queryKey: ["school", "subjects"], queryFn: schoolApi.listSubjects });
  // Dropdown data sources — not a browsable list, so fetch the max page size
  // instead of adding Prev/Next (a <select> has no pagination UI).
  const teachers = useQuery({ queryKey: ["school", "users", "teacher"], queryFn: () => schoolApi.listUsers("teacher", 200) });
  const students = useQuery({ queryKey: ["school", "users", "student"], queryFn: () => schoolApi.listUsers("student", 200) });
  const parents = useQuery({ queryKey: ["school", "users", "parent"], queryFn: () => schoolApi.listUsers("parent", 200) });

  const PAGE_SIZE = 20;
  const [taOffset, setTaOffset] = useState(0);
  const [enrollOffset, setEnrollOffset] = useState(0);
  const [linkOffset, setLinkOffset] = useState(0);
  const [taShowEnded, setTaShowEnded] = useState(false);
  const [enrollShowEnded, setEnrollShowEnded] = useState(false);
  const [endTarget, setEndTarget] = useState<{ kind: "assignment" | "enrollment"; id: string; label: string } | null>(null);
  const [endDate, setEndDate] = useState(() => new Date().toISOString().slice(0, 10));

  const teacherAssignments = useQuery({
    queryKey: ["school", "teacher-assignments", taOffset, taShowEnded],
    queryFn: () => schoolApi.listTeacherAssignments(PAGE_SIZE, taOffset, taShowEnded),
  });
  const enrollments = useQuery({
    queryKey: ["school", "enrollments", enrollOffset, enrollShowEnded],
    queryFn: () => schoolApi.listEnrollments(PAGE_SIZE, enrollOffset, enrollShowEnded),
  });
  const parentLinks = useQuery({
    queryKey: ["school", "parent-links", linkOffset],
    queryFn: () => schoolApi.listParentLinks(PAGE_SIZE, linkOffset),
  });

  const [cls, setCls] = useState({ name: "", grade: "6" });
  const [subj, setSubj] = useState("");
  const [assign, setAssign] = useState({ teacher_id: "", class_id: "", subject_id: "" });
  const [enroll, setEnroll] = useState({ student_id: "", class_id: "" });
  const [link, setLink] = useState({ parent_id: "", student_id: "" });
  const [linkConsent, setLinkConsent] = useState(false);

  const mCls = useMutation({
    mutationFn: () => schoolApi.createClass({ name: cls.name, grade_level: Number(cls.grade) }),
    onSuccess: (r) => { ok(t("school.structure.classCreated", { name: r.name })); qc.invalidateQueries({ queryKey: ["school", "classes"] }); },
    onError: fail,
  });
  const mSubj = useMutation({
    mutationFn: () => schoolApi.createSubject({ name: subj }),
    onSuccess: (r) => { ok(t("school.structure.subjectCreated", { name: r.name })); qc.invalidateQueries({ queryKey: ["school", "subjects"] }); },
    onError: fail,
  });
  const mAssign = useMutation({
    mutationFn: () => schoolApi.assignTeacher(assign),
    onSuccess: () => { ok(t("school.structure.teacherAssigned")); qc.invalidateQueries({ queryKey: ["school", "teacher-assignments"] }); setAssign({ teacher_id: "", class_id: "", subject_id: "" }); },
    onError: fail,
  });
  const mEnroll = useMutation({
    mutationFn: () => schoolApi.enroll(enroll),
    onSuccess: () => { ok(t("school.structure.studentEnrolled")); qc.invalidateQueries({ queryKey: ["school", "enrollments"] }); setEnroll({ student_id: "", class_id: "" }); },
    onError: fail,
  });
  const mLink = useMutation({
    mutationFn: () => schoolApi.linkParent({ ...link, consent_confirmed: linkConsent }),
    onSuccess: () => { ok(t("school.structure.parentLinked")); qc.invalidateQueries({ queryKey: ["school", "parent-links"] }); setLink({ parent_id: "", student_id: "" }); setLinkConsent(false); },
    onError: fail,
  });

  const mUnassign = useMutation({
    mutationFn: (id: string) => schoolApi.unassignTeacher(id),
    onSuccess: () => { ok(t("school.structure.assignmentRemoved")); qc.invalidateQueries({ queryKey: ["school", "teacher-assignments"] }); },
    onError: fail,
  });
  const mUnenroll = useMutation({
    mutationFn: (id: string) => schoolApi.unenrollStudent(id),
    onSuccess: () => { ok(t("school.structure.enrollmentRemoved")); qc.invalidateQueries({ queryKey: ["school", "enrollments"] }); },
    onError: fail,
  });
  const mUnlink = useMutation({
    mutationFn: (id: string) => schoolApi.unlinkParent(id),
    onSuccess: () => { ok(t("school.structure.parentLinkRemoved")); qc.invalidateQueries({ queryKey: ["school", "parent-links"] }); },
    onError: fail,
  });

  const mEndAssignment = useMutation({
    mutationFn: () => schoolApi.updateTeacherAssignment(endTarget!.id, endDate),
    onSuccess: () => { ok(t("school.structure.assignmentEndDated")); qc.invalidateQueries({ queryKey: ["school", "teacher-assignments"] }); setEndTarget(null); },
    onError: fail,
  });
  const mEndEnrollment = useMutation({
    mutationFn: () => schoolApi.updateEnrollment(endTarget!.id, endDate),
    onSuccess: () => { ok(t("school.structure.enrollmentEndDated")); qc.invalidateQueries({ queryKey: ["school", "enrollments"] }); setEndTarget(null); },
    onError: fail,
  });

  const Row = ({ children }: { children: React.ReactNode }) => (
    <div className="p-5 grid md:grid-cols-4 gap-3 items-end">{children}</div>
  );

  // Minimal Prev/Next footer shared by the three paginated join-tables below.
  const Pager = ({
    offset, limit, total, count, onOffsetChange,
  }: {
    offset: number;
    limit: number;
    total: number;
    count: number;
    onOffsetChange: (next: number) => void;
  }) => {
    if (total === 0) return null;
    const rangeStart = offset + 1;
    const rangeEnd = offset + count;
    return (
      <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{t("common.rangeOfTotal", { start: rangeStart, end: rangeEnd, total })}</span>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => onOffsetChange(Math.max(0, offset - limit))} disabled={offset === 0}>
            {t("common.previous")}
          </Button>
          <Button variant="ghost" size="sm" onClick={() => onOffsetChange(offset + limit)} disabled={rangeEnd >= total}>
            {t("common.next")}
          </Button>
        </div>
      </div>
    );
  };

  const ClassPicker = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <Select value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">{classes.isLoading ? t("common.loading") : t("school.structure.selectAClass")}</option>
      {classes.data?.map((c) => (
        <option key={c.id} value={c.id}>{t("school.structure.classGradeOption", { name: c.name, grade: c.grade_level })}</option>
      ))}
    </Select>
  );

  const SubjectPicker = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <Select value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">{subjects.isLoading ? t("common.loading") : t("school.structure.selectASubject")}</option>
      {subjects.data?.map((s) => (
        <option key={s.id} value={s.id}>{s.name}</option>
      ))}
    </Select>
  );

  const UserPicker = ({
    users, loading, value, onChange, placeholder,
  }: {
    users?: { id: string; name: string; email: string }[];
    loading: boolean;
    value: string;
    onChange: (v: string) => void;
    placeholder: string;
  }) => (
    <Select value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">{loading ? t("common.loading") : placeholder}</option>
      {users?.map((u) => (
        <option key={u.id} value={u.id}>{t("school.structure.userEmailOption", { name: u.name, email: u.email })}</option>
      ))}
    </Select>
  );

  return (
    <div>
      <PageTitle subtitle={t("school.structure.subtitle")}>{t("school.structure.title")}</PageTitle>

      <div className="grid gap-6">
        <Card>
          <CardHeader title={t("school.structure.createClass")} />
          <Row>
            <div><Label>{t("school.structure.name")}</Label><Input value={cls.name} onChange={(e) => setCls({ ...cls, name: e.target.value })} /></div>
            <div><Label>{t("school.structure.grade")}</Label><Input type="number" value={cls.grade} onChange={(e) => setCls({ ...cls, grade: e.target.value })} /></div>
            <Button onClick={() => mCls.mutate()} disabled={!cls.name}>{t("school.structure.createClass")}</Button>
          </Row>
        </Card>

        <Card>
          <CardHeader title={t("school.structure.createSubject")} />
          <Row>
            <div className="md:col-span-2"><Label>{t("school.structure.name")}</Label><Input value={subj} onChange={(e) => setSubj(e.target.value)} /></div>
            <Button onClick={() => mSubj.mutate()} disabled={!subj}>{t("school.structure.createSubject")}</Button>
          </Row>
        </Card>

        <Card>
          <CardHeader
            title={t("school.structure.assignTeacherTitle")}
            action={
              <label className="flex items-center gap-1.5 text-xs text-slate-500 font-normal cursor-pointer">
                <input type="checkbox" checked={taShowEnded} onChange={(e) => { setTaOffset(0); setTaShowEnded(e.target.checked); }} />
                {t("school.structure.showEnded")}
              </label>
            }
          />
          <Row>
            <div>
              <Label>{t("school.structure.teacher")}</Label>
              <UserPicker users={teachers.data?.items} loading={teachers.isLoading} placeholder={t("school.structure.selectATeacher")}
                value={assign.teacher_id} onChange={(v) => setAssign({ ...assign, teacher_id: v })} />
            </div>
            <div><Label>{t("school.structure.class")}</Label><ClassPicker value={assign.class_id} onChange={(v) => setAssign({ ...assign, class_id: v })} /></div>
            <div><Label>{t("school.structure.subject")}</Label><SubjectPicker value={assign.subject_id} onChange={(v) => setAssign({ ...assign, subject_id: v })} /></div>
            <Button onClick={() => mAssign.mutate()} disabled={!assign.teacher_id || !assign.class_id || !assign.subject_id}>{t("school.structure.assign")}</Button>
          </Row>
          <div className="border-t border-slate-100">
            <DataBoundary
              query={teacherAssignments}
              isEmpty={(d) => d.items.length === 0}
              emptyTitle={t("school.structure.noAssignments")}
              emptyHint={t("school.structure.noAssignmentsHint")}
              loadingFallback={<Skeleton className="h-20 m-3" />}
            >
              {(page) => (
                <>
                  <Table head={[t("school.structure.teacher"), t("school.structure.class"), t("school.structure.subject"), "", ""]}>
                    {page.items.map((r) => (
                      <tr key={r.id} className="border-b border-slate-50">
                        <td className="px-4 py-2 font-medium text-slate-700">{r.teacher_name}</td>
                        <td className="px-4 py-2 text-slate-500">{r.class_name}</td>
                        <td className="px-4 py-2 text-slate-500">{r.subject_name}</td>
                        <td className="px-4 py-2">
                          {r.end_date && <Badge tone="amber">{t("school.structure.endsOn", { date: r.end_date })}</Badge>}
                        </td>
                        <td className="px-4 py-2 text-right whitespace-nowrap">
                          {!r.end_date && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setEndDate(new Date().toISOString().slice(0, 10));
                                setEndTarget({ kind: "assignment", id: r.id, label: `${r.teacher_name} teaching ${r.subject_name} to ${r.class_name}` });
                              }}
                            >
                              {t("school.structure.end")}
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => confirm.ask({
                              title: t("school.structure.removeAssignmentTitle"),
                              description: t("school.structure.removeAssignmentDesc", { teacher: r.teacher_name, subject: r.subject_name, class: r.class_name }),
                              confirmLabel: t("school.structure.remove"),
                              onConfirm: () => mUnassign.mutateAsync(r.id),
                            })}
                          >
                            {t("school.structure.remove")}
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </Table>
                  <Pager offset={taOffset} limit={PAGE_SIZE} total={page.total} count={page.items.length} onOffsetChange={setTaOffset} />
                </>
              )}
            </DataBoundary>
          </div>
        </Card>

        <Card>
          <CardHeader
            title={t("school.structure.enrollStudentTitle")}
            action={
              <label className="flex items-center gap-1.5 text-xs text-slate-500 font-normal cursor-pointer">
                <input type="checkbox" checked={enrollShowEnded} onChange={(e) => { setEnrollOffset(0); setEnrollShowEnded(e.target.checked); }} />
                {t("school.structure.showEnded")}
              </label>
            }
          />
          <Row>
            <div>
              <Label>{t("school.structure.student")}</Label>
              <UserPicker users={students.data?.items} loading={students.isLoading} placeholder={t("school.structure.selectAStudent")}
                value={enroll.student_id} onChange={(v) => setEnroll({ ...enroll, student_id: v })} />
            </div>
            <div><Label>{t("school.structure.class")}</Label><ClassPicker value={enroll.class_id} onChange={(v) => setEnroll({ ...enroll, class_id: v })} /></div>
            <Button onClick={() => mEnroll.mutate()} disabled={!enroll.student_id || !enroll.class_id}>{t("school.structure.enroll")}</Button>
          </Row>
          <div className="border-t border-slate-100">
            <DataBoundary
              query={enrollments}
              isEmpty={(d) => d.items.length === 0}
              emptyTitle={t("school.structure.noEnrollments")}
              emptyHint={t("school.structure.noEnrollmentsHint")}
              loadingFallback={<Skeleton className="h-20 m-3" />}
            >
              {(page) => (
                <>
                  <Table head={[t("school.structure.student"), t("school.structure.class"), "", ""]}>
                    {page.items.map((r) => (
                      <tr key={r.id} className="border-b border-slate-50">
                        <td className="px-4 py-2 font-medium text-slate-700">{r.student_name}</td>
                        <td className="px-4 py-2 text-slate-500">{r.class_name}</td>
                        <td className="px-4 py-2">
                          {r.end_date && <Badge tone="amber">{t("school.structure.endsOn", { date: r.end_date })}</Badge>}
                        </td>
                        <td className="px-4 py-2 text-right whitespace-nowrap">
                          {!r.end_date && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setEndDate(new Date().toISOString().slice(0, 10));
                                setEndTarget({ kind: "enrollment", id: r.id, label: `${r.student_name} in ${r.class_name}` });
                              }}
                            >
                              {t("school.structure.end")}
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => confirm.ask({
                              title: t("school.structure.removeEnrollmentTitle"),
                              description: t("school.structure.removeEnrollmentDesc", { student: r.student_name, class: r.class_name }),
                              confirmLabel: t("school.structure.remove"),
                              onConfirm: () => mUnenroll.mutateAsync(r.id),
                            })}
                          >
                            {t("school.structure.remove")}
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </Table>
                  <Pager offset={enrollOffset} limit={PAGE_SIZE} total={page.total} count={page.items.length} onOffsetChange={setEnrollOffset} />
                </>
              )}
            </DataBoundary>
          </div>
        </Card>

        <Card>
          <CardHeader title={t("school.structure.linkParentTitle")} />
          <Row>
            <div>
              <Label>{t("school.structure.parent")}</Label>
              <UserPicker users={parents.data?.items} loading={parents.isLoading} placeholder={t("school.structure.selectAParent")}
                value={link.parent_id} onChange={(v) => setLink({ ...link, parent_id: v })} />
            </div>
            <div>
              <Label>{t("school.structure.student")}</Label>
              <UserPicker users={students.data?.items} loading={students.isLoading} placeholder={t("school.structure.selectAStudent")}
                value={link.student_id} onChange={(v) => setLink({ ...link, student_id: v })} />
            </div>
          </Row>
          <div className="px-5 pb-4 flex items-center justify-between gap-3 flex-wrap">
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                className="rounded border-slate-300"
                checked={linkConsent}
                onChange={(e) => setLinkConsent(e.target.checked)}
              />
              {t("school.structure.consentLabel")}
            </label>
            <Button onClick={() => mLink.mutate()} disabled={!link.parent_id || !link.student_id || !linkConsent}>{t("school.structure.link")}</Button>
          </div>
          <div className="border-t border-slate-100">
            <DataBoundary
              query={parentLinks}
              isEmpty={(d) => d.items.length === 0}
              emptyTitle={t("school.structure.noParentLinks")}
              emptyHint={t("school.structure.noParentLinksHint")}
              loadingFallback={<Skeleton className="h-20 m-3" />}
            >
              {(page) => (
                <>
                  <Table head={[t("school.structure.parent"), t("school.structure.student"), ""]}>
                    {page.items.map((r) => (
                      <tr key={r.id} className="border-b border-slate-50">
                        <td className="px-4 py-2 font-medium text-slate-700">{r.parent_name}</td>
                        <td className="px-4 py-2 text-slate-500">{r.student_name}</td>
                        <td className="px-4 py-2 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => confirm.ask({
                              title: t("school.structure.removeLinkTitle"),
                              description: t("school.structure.removeLinkDesc", { parent: r.parent_name, student: r.student_name }),
                              confirmLabel: t("school.structure.remove"),
                              onConfirm: () => mUnlink.mutateAsync(r.id),
                            })}
                          >
                            {t("school.structure.remove")}
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </Table>
                  <Pager offset={linkOffset} limit={PAGE_SIZE} total={page.total} count={page.items.length} onOffsetChange={setLinkOffset} />
                </>
              )}
            </DataBoundary>
          </div>
        </Card>
      </div>
      {confirm.dialog}

      <Modal
        open={!!endTarget}
        onOpenChange={(open) => !open && setEndTarget(null)}
        title={t("school.structure.setEndDateTitle")}
        description={endTarget?.label}
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <Label>{t("school.structure.endDate")}</Label>
            <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setEndTarget(null)}>{t("common.cancel")}</Button>
            <Button
              onClick={() => (endTarget?.kind === "assignment" ? mEndAssignment.mutate() : mEndEnrollment.mutate())}
              disabled={!endDate || mEndAssignment.isPending || mEndEnrollment.isPending}
            >
              {mEndAssignment.isPending || mEndEnrollment.isPending ? t("school.structure.saving") : t("school.structure.setEndDate")}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
