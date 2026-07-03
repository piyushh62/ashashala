import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { schoolApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, Input, Label } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";

// Classes, subjects, and the id-based joins (teacher assignment / enrollment /
// parent link). Ids are entered directly — a production build would use pickers,
// but this keeps the wiring honest against the API.
export default function SchoolStructure() {
  const toast = useToast();
  const qc = useQueryClient();
  const ok = (m: string) => {
    toast.push(m, "success");
    qc.invalidateQueries({ queryKey: ["school"] });
  };
  const fail = () => toast.push("Request failed — check the ids.", "error");

  const [cls, setCls] = useState({ name: "", grade: "6" });
  const [subj, setSubj] = useState("");
  const [assign, setAssign] = useState({ teacher_id: "", class_id: "", subject_id: "" });
  const [enroll, setEnroll] = useState({ student_id: "", class_id: "" });
  const [link, setLink] = useState({ parent_id: "", student_id: "" });

  const mCls = useMutation({ mutationFn: () => schoolApi.createClass({ name: cls.name, grade_level: Number(cls.grade) }), onSuccess: (r) => ok(`Class created: ${r.id}`), onError: fail });
  const mSubj = useMutation({ mutationFn: () => schoolApi.createSubject({ name: subj }), onSuccess: (r) => ok(`Subject created: ${r.id}`), onError: fail });
  const mAssign = useMutation({ mutationFn: () => schoolApi.assignTeacher(assign), onSuccess: () => ok("Teacher assigned."), onError: fail });
  const mEnroll = useMutation({ mutationFn: () => schoolApi.enroll(enroll), onSuccess: () => ok("Student enrolled."), onError: fail });
  const mLink = useMutation({ mutationFn: () => schoolApi.linkParent(link), onSuccess: () => ok("Parent linked (consent recorded)."), onError: fail });

  const Row = ({ children }: { children: React.ReactNode }) => (
    <div className="p-5 grid md:grid-cols-4 gap-3 items-end">{children}</div>
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
            <Button onClick={() => mCls.mutate()}>Create class</Button>
          </Row>
        </Card>

        <Card>
          <CardHeader title="Create subject" />
          <Row>
            <div className="md:col-span-2"><Label>Name</Label><Input value={subj} onChange={(e) => setSubj(e.target.value)} /></div>
            <Button onClick={() => mSubj.mutate()}>Create subject</Button>
          </Row>
        </Card>

        <Card>
          <CardHeader title="Assign teacher to (class, subject)" />
          <Row>
            <div><Label>Teacher id</Label><Input value={assign.teacher_id} onChange={(e) => setAssign({ ...assign, teacher_id: e.target.value })} /></div>
            <div><Label>Class id</Label><Input value={assign.class_id} onChange={(e) => setAssign({ ...assign, class_id: e.target.value })} /></div>
            <div><Label>Subject id</Label><Input value={assign.subject_id} onChange={(e) => setAssign({ ...assign, subject_id: e.target.value })} /></div>
            <Button onClick={() => mAssign.mutate()}>Assign</Button>
          </Row>
        </Card>

        <Card>
          <CardHeader title="Enroll student" />
          <Row>
            <div><Label>Student id</Label><Input value={enroll.student_id} onChange={(e) => setEnroll({ ...enroll, student_id: e.target.value })} /></div>
            <div><Label>Class id</Label><Input value={enroll.class_id} onChange={(e) => setEnroll({ ...enroll, class_id: e.target.value })} /></div>
            <Button onClick={() => mEnroll.mutate()}>Enroll</Button>
          </Row>
        </Card>

        <Card>
          <CardHeader title="Link parent to student" />
          <Row>
            <div><Label>Parent id</Label><Input value={link.parent_id} onChange={(e) => setLink({ ...link, parent_id: e.target.value })} /></div>
            <div><Label>Student id</Label><Input value={link.student_id} onChange={(e) => setLink({ ...link, student_id: e.target.value })} /></div>
            <Button onClick={() => mLink.mutate()}>Link</Button>
          </Row>
        </Card>
      </div>
    </div>
  );
}
