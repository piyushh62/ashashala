import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { schoolApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, Input, Label } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";
import { ClassPicker, Row, SubjectPicker, UserPicker } from "../../components/school/StructurePickers";

// The "add / assign" side of school structure: create classes and subjects,
// then wire up the id-based joins (teacher assignment / enrollment / parent
// link). Admins typically add several records in a row, so submitting keeps
// you on this page — the lists live on /school/structure.
export default function SchoolStructureCreate() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
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

  const [cls, setCls] = useState({ name: "", grade: "6" });
  const [subj, setSubj] = useState("");
  const [assign, setAssign] = useState({ teacher_id: "", class_id: "", subject_id: "" });
  const [enroll, setEnroll] = useState({ student_id: "", class_id: "" });
  const [link, setLink] = useState({ parent_id: "", student_id: "" });
  const [linkConsent, setLinkConsent] = useState(false);

  const mCls = useMutation({
    mutationFn: () => schoolApi.createClass({ name: cls.name, grade_level: Number(cls.grade) }),
    onSuccess: (r) => { ok(t("school.structure.classCreated", { name: r.name })); qc.invalidateQueries({ queryKey: ["school", "classes"] }); setCls({ name: "", grade: "6" }); },
    onError: fail,
  });
  const mSubj = useMutation({
    mutationFn: () => schoolApi.createSubject({ name: subj }),
    onSuccess: (r) => { ok(t("school.structure.subjectCreated", { name: r.name })); qc.invalidateQueries({ queryKey: ["school", "subjects"] }); setSubj(""); },
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

  return (
    <div>
      <PageTitle subtitle={t("school.structure.subtitle")}>{t("nav.structureAdd")}</PageTitle>

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
          <CardHeader title={t("school.structure.assignTeacherTitle")} />
          <Row>
            <div>
              <Label>{t("school.structure.teacher")}</Label>
              <UserPicker users={teachers.data?.items} total={teachers.data?.total} loading={teachers.isLoading} placeholder={t("school.structure.selectATeacher")}
                value={assign.teacher_id} onChange={(v) => setAssign({ ...assign, teacher_id: v })} />
            </div>
            <div>
              <Label>{t("school.structure.class")}</Label>
              <ClassPicker classes={classes.data} loading={classes.isLoading} value={assign.class_id} onChange={(v) => setAssign({ ...assign, class_id: v })} />
            </div>
            <div>
              <Label>{t("school.structure.subject")}</Label>
              <SubjectPicker subjects={subjects.data} loading={subjects.isLoading} value={assign.subject_id} onChange={(v) => setAssign({ ...assign, subject_id: v })} />
            </div>
            <Button onClick={() => mAssign.mutate()} disabled={!assign.teacher_id || !assign.class_id || !assign.subject_id}>{t("school.structure.assign")}</Button>
          </Row>
        </Card>

        <Card>
          <CardHeader title={t("school.structure.enrollStudentTitle")} />
          <Row>
            <div>
              <Label>{t("school.structure.student")}</Label>
              <UserPicker users={students.data?.items} total={students.data?.total} loading={students.isLoading} placeholder={t("school.structure.selectAStudent")}
                value={enroll.student_id} onChange={(v) => setEnroll({ ...enroll, student_id: v })} />
            </div>
            <div>
              <Label>{t("school.structure.class")}</Label>
              <ClassPicker classes={classes.data} loading={classes.isLoading} value={enroll.class_id} onChange={(v) => setEnroll({ ...enroll, class_id: v })} />
            </div>
            <Button onClick={() => mEnroll.mutate()} disabled={!enroll.student_id || !enroll.class_id}>{t("school.structure.enroll")}</Button>
          </Row>
        </Card>

        <Card>
          <CardHeader title={t("school.structure.linkParentTitle")} />
          <Row>
            <div>
              <Label>{t("school.structure.parent")}</Label>
              <UserPicker users={parents.data?.items} total={parents.data?.total} loading={parents.isLoading} placeholder={t("school.structure.selectAParent")}
                value={link.parent_id} onChange={(v) => setLink({ ...link, parent_id: v })} />
            </div>
            <div>
              <Label>{t("school.structure.student")}</Label>
              <UserPicker users={students.data?.items} total={students.data?.total} loading={students.isLoading} placeholder={t("school.structure.selectAStudent")}
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
        </Card>
      </div>
    </div>
  );
}
