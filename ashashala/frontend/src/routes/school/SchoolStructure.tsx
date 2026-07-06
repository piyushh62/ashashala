import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { schoolApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, Input, Label, Select } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";

// Classes, subjects, and the id-based joins (teacher assignment / enrollment /
// parent link) — all pickers are populated by name from the school's real
// classes/subjects/users, so nobody has to type a UUID by hand.
export default function SchoolStructure() {
  const toast = useToast();
  const qc = useQueryClient();
  const ok = (m: string) => {
    toast.push(m, "success");
    qc.invalidateQueries({ queryKey: ["school"] });
  };
  const fail = () => toast.push("Request failed.", "error");

  const classes = useQuery({ queryKey: ["school", "classes"], queryFn: schoolApi.listClasses });
  const subjects = useQuery({ queryKey: ["school", "subjects"], queryFn: schoolApi.listSubjects });
  const teachers = useQuery({ queryKey: ["school", "users", "teacher"], queryFn: () => schoolApi.listUsers("teacher") });
  const students = useQuery({ queryKey: ["school", "users", "student"], queryFn: () => schoolApi.listUsers("student") });
  const parents = useQuery({ queryKey: ["school", "users", "parent"], queryFn: () => schoolApi.listUsers("parent") });

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
  const mAssign = useMutation({ mutationFn: () => schoolApi.assignTeacher(assign), onSuccess: () => ok("Teacher assigned."), onError: fail });
  const mEnroll = useMutation({ mutationFn: () => schoolApi.enroll(enroll), onSuccess: () => ok("Student enrolled."), onError: fail });
  const mLink = useMutation({ mutationFn: () => schoolApi.linkParent(link), onSuccess: () => ok("Parent linked (consent recorded)."), onError: fail });

  const Row = ({ children }: { children: React.ReactNode }) => (
    <div className="p-5 grid md:grid-cols-4 gap-3 items-end">{children}</div>
  );

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
          <CardHeader title="Assign teacher to (class, subject)" />
          <Row>
            <div>
              <Label>Teacher</Label>
              <UserPicker users={teachers.data} loading={teachers.isLoading} placeholder="Select a teacher"
                value={assign.teacher_id} onChange={(v) => setAssign({ ...assign, teacher_id: v })} />
            </div>
            <div><Label>Class</Label><ClassPicker value={assign.class_id} onChange={(v) => setAssign({ ...assign, class_id: v })} /></div>
            <div><Label>Subject</Label><SubjectPicker value={assign.subject_id} onChange={(v) => setAssign({ ...assign, subject_id: v })} /></div>
            <Button onClick={() => mAssign.mutate()} disabled={!assign.teacher_id || !assign.class_id || !assign.subject_id}>Assign</Button>
          </Row>
        </Card>

        <Card>
          <CardHeader title="Enroll student" />
          <Row>
            <div>
              <Label>Student</Label>
              <UserPicker users={students.data} loading={students.isLoading} placeholder="Select a student"
                value={enroll.student_id} onChange={(v) => setEnroll({ ...enroll, student_id: v })} />
            </div>
            <div><Label>Class</Label><ClassPicker value={enroll.class_id} onChange={(v) => setEnroll({ ...enroll, class_id: v })} /></div>
            <Button onClick={() => mEnroll.mutate()} disabled={!enroll.student_id || !enroll.class_id}>Enroll</Button>
          </Row>
        </Card>

        <Card>
          <CardHeader title="Link parent to student" />
          <Row>
            <div>
              <Label>Parent</Label>
              <UserPicker users={parents.data} loading={parents.isLoading} placeholder="Select a parent"
                value={link.parent_id} onChange={(v) => setLink({ ...link, parent_id: v })} />
            </div>
            <div>
              <Label>Student</Label>
              <UserPicker users={students.data} loading={students.isLoading} placeholder="Select a student"
                value={link.student_id} onChange={(v) => setLink({ ...link, student_id: v })} />
            </div>
            <Button onClick={() => mLink.mutate()} disabled={!link.parent_id || !link.student_id}>Link</Button>
          </Row>
        </Card>
      </div>
    </div>
  );
}
