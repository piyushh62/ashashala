import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { schoolApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, Icon, Input, Label, Pager, Skeleton, Table } from "../../components/ui";
import { DataBoundary } from "../../components/ui/DataBoundary";
import { Modal, useConfirm } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";

// The browse/manage side of school structure: teacher assignments,
// enrollments, and parent links. Creating classes/subjects and the id-based
// joins live on /school/structure/new.
export default function SchoolStructure() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const navigate = useNavigate();
  const ok = (m: string) => {
    toast.push(m, "success");
    qc.invalidateQueries({ queryKey: ["school"] });
  };
  const fail = () => toast.push(t("common.requestFailed"), "error");

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

  return (
    <div>
      <PageTitle subtitle={t("school.structure.subtitle")}>{t("school.structure.title")}</PageTitle>

      <div className="mb-6 flex justify-end">
        <Button size="sm" onClick={() => navigate("/school/structure/new")}>
          <Icon name="add" className="w-4 h-4" />
          {t("nav.structureAdd")}
        </Button>
      </div>

      <div className="grid gap-6">
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
                  <Pager offset={taOffset} limit={PAGE_SIZE} total={page.total} count={page.items.length} onOffsetChange={setTaOffset} className="border-t border-slate-100 dark:border-slate-800" />
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
                  <Pager offset={enrollOffset} limit={PAGE_SIZE} total={page.total} count={page.items.length} onOffsetChange={setEnrollOffset} className="border-t border-slate-100 dark:border-slate-800" />
                </>
              )}
            </DataBoundary>
          </div>
        </Card>

        <Card>
          <CardHeader title={t("school.structure.linkParentTitle")} />
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
                  <Pager offset={linkOffset} limit={PAGE_SIZE} total={page.total} count={page.items.length} onOffsetChange={setLinkOffset} className="border-t border-slate-100 dark:border-slate-800" />
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
