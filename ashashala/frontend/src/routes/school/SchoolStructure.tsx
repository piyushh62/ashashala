import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
  const toast = useToast();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const ok = (m: string) => {
    toast.push(m, "success");
    qc.invalidateQueries({ queryKey: ["school"] });
  };
  const fail = () => toast.push("Request failed.", "error");

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

  const mCls = useMutation({
    mutationFn: () => schoolApi.createClass({ name: cls.name, grade_level: Number(cls.grade) }),
    onSuccess: (r) => { ok(`Class created: ${r.name}`); qc.invalidateQueries({ queryKey: ["school", "classes"] }); },
    onError: fail,
  });
  const mSubj = useMutation({
    mutationFn: () => schoolApi.createSubject({ name: subj }),
    onSuccess: (r) => { ok(`Subject created: ${r.name}`); qc.invalidateQueries({ queryKey: ["school", "subjects"] }); },
    onError: fail,
  });
  const mAssign = useMutation({
    mutationFn: () => schoolApi.assignTeacher(assign),
    onSuccess: () => { ok("Teacher assigned."); qc.invalidateQueries({ queryKey: ["school", "teacher-assignments"] }); setAssign({ teacher_id: "", class_id: "", subject_id: "" }); },
    onError: fail,
  });
  const mEnroll = useMutation({
    mutationFn: () => schoolApi.enroll(enroll),
    onSuccess: () => { ok("Student enrolled."); qc.invalidateQueries({ queryKey: ["school", "enrollments"] }); setEnroll({ student_id: "", class_id: "" }); },
    onError: fail,
  });
  const mLink = useMutation({
    mutationFn: () => schoolApi.linkParent(link),
    onSuccess: () => { ok("Parent linked (consent recorded)."); qc.invalidateQueries({ queryKey: ["school", "parent-links"] }); setLink({ parent_id: "", student_id: "" }); },
    onError: fail,
  });

  const mUnassign = useMutation({
    mutationFn: (id: string) => schoolApi.unassignTeacher(id),
    onSuccess: () => { ok("Assignment removed."); qc.invalidateQueries({ queryKey: ["school", "teacher-assignments"] }); },
    onError: fail,
  });
  const mUnenroll = useMutation({
    mutationFn: (id: string) => schoolApi.unenrollStudent(id),
    onSuccess: () => { ok("Enrollment removed."); qc.invalidateQueries({ queryKey: ["school", "enrollments"] }); },
    onError: fail,
  });
  const mUnlink = useMutation({
    mutationFn: (id: string) => schoolApi.unlinkParent(id),
    onSuccess: () => { ok("Parent link removed."); qc.invalidateQueries({ queryKey: ["school", "parent-links"] }); },
    onError: fail,
  });

  const mEndAssignment = useMutation({
    mutationFn: () => schoolApi.updateTeacherAssignment(endTarget!.id, endDate),
    onSuccess: () => { ok("Assignment end-dated."); qc.invalidateQueries({ queryKey: ["school", "teacher-assignments"] }); setEndTarget(null); },
    onError: fail,
  });
  const mEndEnrollment = useMutation({
    mutationFn: () => schoolApi.updateEnrollment(endTarget!.id, endDate),
    onSuccess: () => { ok("Enrollment end-dated."); qc.invalidateQueries({ queryKey: ["school", "enrollments"] }); setEndTarget(null); },
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
        <span>{rangeStart}–{rangeEnd} of {total}</span>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => onOffsetChange(Math.max(0, offset - limit))} disabled={offset === 0}>
            Previous
          </Button>
          <Button variant="ghost" size="sm" onClick={() => onOffsetChange(offset + limit)} disabled={rangeEnd >= total}>
            Next
          </Button>
        </div>
      </div>
    );
  };

  const ClassPicker = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <Select value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">{classes.isLoading ? "Loading…" : "Select a class"}</option>
      {classes.data?.map((c) => (
        <option key={c.id} value={c.id}>{c.name} (Grade {c.grade_level})</option>
      ))}
    </Select>
  );

  const SubjectPicker = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <Select value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">{subjects.isLoading ? "Loading…" : "Select a subject"}</option>
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
      <option value="">{loading ? "Loading…" : placeholder}</option>
      {users?.map((u) => (
        <option key={u.id} value={u.id}>{u.name} ({u.email})</option>
      ))}
    </Select>
  );

  return (
    <div>
      <PageTitle subtitle="Set up classes, subjects and the people in them.">Classes & Structure</PageTitle>

      <div className="grid gap-6">
        <Card>
          <CardHeader title="Create class" />
          <Row>
            <div><Label>Name</Label><Input value={cls.name} onChange={(e) => setCls({ ...cls, name: e.target.value })} /></div>
            <div><Label>Grade</Label><Input type="number" value={cls.grade} onChange={(e) => setCls({ ...cls, grade: e.target.value })} /></div>
            <Button onClick={() => mCls.mutate()} disabled={!cls.name}>Create class</Button>
          </Row>
        </Card>

        <Card>
          <CardHeader title="Create subject" />
          <Row>
            <div className="md:col-span-2"><Label>Name</Label><Input value={subj} onChange={(e) => setSubj(e.target.value)} /></div>
            <Button onClick={() => mSubj.mutate()} disabled={!subj}>Create subject</Button>
          </Row>
        </Card>

        <Card>
          <CardHeader
            title="Assign teacher to (class, subject)"
            action={
              <label className="flex items-center gap-1.5 text-xs text-slate-500 font-normal cursor-pointer">
                <input type="checkbox" checked={taShowEnded} onChange={(e) => { setTaOffset(0); setTaShowEnded(e.target.checked); }} />
                Show ended
              </label>
            }
          />
          <Row>
            <div>
              <Label>Teacher</Label>
              <UserPicker users={teachers.data?.items} loading={teachers.isLoading} placeholder="Select a teacher"
                value={assign.teacher_id} onChange={(v) => setAssign({ ...assign, teacher_id: v })} />
            </div>
            <div><Label>Class</Label><ClassPicker value={assign.class_id} onChange={(v) => setAssign({ ...assign, class_id: v })} /></div>
            <div><Label>Subject</Label><SubjectPicker value={assign.subject_id} onChange={(v) => setAssign({ ...assign, subject_id: v })} /></div>
            <Button onClick={() => mAssign.mutate()} disabled={!assign.teacher_id || !assign.class_id || !assign.subject_id}>Assign</Button>
          </Row>
          <div className="border-t border-slate-100">
            <DataBoundary
              query={teacherAssignments}
              isEmpty={(d) => d.items.length === 0}
              emptyTitle="No assignments yet"
              emptyHint="Assign a teacher to a class and subject above."
              loadingFallback={<Skeleton className="h-20 m-3" />}
            >
              {(page) => (
                <>
                  <Table head={["Teacher", "Class", "Subject", "", ""]}>
                    {page.items.map((r) => (
                      <tr key={r.id} className="border-b border-slate-50">
                        <td className="px-4 py-2 font-medium text-slate-700">{r.teacher_name}</td>
                        <td className="px-4 py-2 text-slate-500">{r.class_name}</td>
                        <td className="px-4 py-2 text-slate-500">{r.subject_name}</td>
                        <td className="px-4 py-2">
                          {r.end_date && <Badge tone="amber">Ends {r.end_date}</Badge>}
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
                              End
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => confirm.ask({
                              title: "Remove this assignment?",
                              description: `${r.teacher_name} will no longer teach ${r.subject_name} to ${r.class_name}.`,
                              confirmLabel: "Remove",
                              onConfirm: () => mUnassign.mutateAsync(r.id),
                            })}
                          >
                            Remove
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
            title="Enroll student"
            action={
              <label className="flex items-center gap-1.5 text-xs text-slate-500 font-normal cursor-pointer">
                <input type="checkbox" checked={enrollShowEnded} onChange={(e) => { setEnrollOffset(0); setEnrollShowEnded(e.target.checked); }} />
                Show ended
              </label>
            }
          />
          <Row>
            <div>
              <Label>Student</Label>
              <UserPicker users={students.data?.items} loading={students.isLoading} placeholder="Select a student"
                value={enroll.student_id} onChange={(v) => setEnroll({ ...enroll, student_id: v })} />
            </div>
            <div><Label>Class</Label><ClassPicker value={enroll.class_id} onChange={(v) => setEnroll({ ...enroll, class_id: v })} /></div>
            <Button onClick={() => mEnroll.mutate()} disabled={!enroll.student_id || !enroll.class_id}>Enroll</Button>
          </Row>
          <div className="border-t border-slate-100">
            <DataBoundary
              query={enrollments}
              isEmpty={(d) => d.items.length === 0}
              emptyTitle="No enrollments yet"
              emptyHint="Enroll a student into a class above."
              loadingFallback={<Skeleton className="h-20 m-3" />}
            >
              {(page) => (
                <>
                  <Table head={["Student", "Class", "", ""]}>
                    {page.items.map((r) => (
                      <tr key={r.id} className="border-b border-slate-50">
                        <td className="px-4 py-2 font-medium text-slate-700">{r.student_name}</td>
                        <td className="px-4 py-2 text-slate-500">{r.class_name}</td>
                        <td className="px-4 py-2">
                          {r.end_date && <Badge tone="amber">Ends {r.end_date}</Badge>}
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
                              End
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => confirm.ask({
                              title: "Remove this enrollment?",
                              description: `${r.student_name} will no longer be enrolled in ${r.class_name}.`,
                              confirmLabel: "Remove",
                              onConfirm: () => mUnenroll.mutateAsync(r.id),
                            })}
                          >
                            Remove
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
          <CardHeader title="Link parent to student" />
          <Row>
            <div>
              <Label>Parent</Label>
              <UserPicker users={parents.data?.items} loading={parents.isLoading} placeholder="Select a parent"
                value={link.parent_id} onChange={(v) => setLink({ ...link, parent_id: v })} />
            </div>
            <div>
              <Label>Student</Label>
              <UserPicker users={students.data?.items} loading={students.isLoading} placeholder="Select a student"
                value={link.student_id} onChange={(v) => setLink({ ...link, student_id: v })} />
            </div>
            <Button onClick={() => mLink.mutate()} disabled={!link.parent_id || !link.student_id}>Link</Button>
          </Row>
          <div className="border-t border-slate-100">
            <DataBoundary
              query={parentLinks}
              isEmpty={(d) => d.items.length === 0}
              emptyTitle="No parent links yet"
              emptyHint="Link a parent to a student above."
              loadingFallback={<Skeleton className="h-20 m-3" />}
            >
              {(page) => (
                <>
                  <Table head={["Parent", "Student", ""]}>
                    {page.items.map((r) => (
                      <tr key={r.id} className="border-b border-slate-50">
                        <td className="px-4 py-2 font-medium text-slate-700">{r.parent_name}</td>
                        <td className="px-4 py-2 text-slate-500">{r.student_name}</td>
                        <td className="px-4 py-2 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => confirm.ask({
                              title: "Remove this link?",
                              description: `${r.parent_name} will no longer be linked to ${r.student_name}.`,
                              confirmLabel: "Remove",
                              onConfirm: () => mUnlink.mutateAsync(r.id),
                            })}
                          >
                            Remove
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
        title="Set an end date"
        description={endTarget?.label}
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <Label>End date</Label>
            <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setEndTarget(null)}>Cancel</Button>
            <Button
              onClick={() => (endTarget?.kind === "assignment" ? mEndAssignment.mutate() : mEndEnrollment.mutate())}
              disabled={!endDate || mEndAssignment.isPending || mEndEnrollment.isPending}
            >
              {mEndAssignment.isPending || mEndEnrollment.isPending ? "Saving…" : "Set end date"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
