import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Input, Label, Skeleton, Table } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";

type Tab = "file" | "url" | "youtube";

export default function TeacherMaterials() {
  const toast = useToast();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("file");
  const [classId, setClassId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const materials = useQuery({ queryKey: ["teacher", "materials"], queryFn: teacherApi.materials });
  const done = () => {
    toast.push("Uploaded — indexing in the background.", "success");
    setUrl("");
    setFile(null);
    qc.invalidateQueries({ queryKey: ["teacher", "materials"] });
  };
  const fail = () => toast.push("Upload failed — check your class/subject assignment.", "error");

  const upFile = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      fd.append("file", file!);
      fd.append("class_id", classId);
      if (subjectId) fd.append("subject_id", subjectId);
      return teacherApi.uploadFile(fd);
    },
    onSuccess: done,
    onError: fail,
  });
  const upUrl = useMutation({
    mutationFn: () => teacherApi.uploadUrl({ class_id: classId, subject_id: subjectId || undefined, url }),
    onSuccess: done,
    onError: fail,
  });
  const upYt = useMutation({
    mutationFn: () => teacherApi.uploadYoutube({ class_id: classId, subject_id: subjectId || undefined, url }),
    onSuccess: done,
    onError: fail,
  });

  const submit = () => {
    if (tab === "file") upFile.mutate();
    else if (tab === "url") upUrl.mutate();
    else upYt.mutate();
  };

  return (
    <div>
      <PageTitle subtitle="Upload PDFs, links or YouTube videos for a class.">Materials</PageTitle>

      <Card className="mb-6">
        <CardHeader title="Add material" />
        <div className="px-5 pt-4 flex gap-2">
          {(["file", "url", "youtube"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded-lg text-sm ${
                tab === t ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              {t === "file" ? "📄 File" : t === "url" ? "🔗 URL" : "▶ YouTube"}
            </button>
          ))}
        </div>
        <div className="p-5 grid md:grid-cols-3 gap-3 items-end">
          <div>
            <Label>Class id</Label>
            <Input value={classId} onChange={(e) => setClassId(e.target.value)} />
          </div>
          <div>
            <Label>Subject id (optional)</Label>
            <Input value={subjectId} onChange={(e) => setSubjectId(e.target.value)} />
          </div>
          {tab === "file" ? (
            <div>
              <Label>File</Label>
              <input type="file" accept=".pdf,.docx,.txt,.jpg,.png" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </div>
          ) : (
            <div>
              <Label>{tab === "url" ? "URL" : "YouTube URL"}</Label>
              <Input value={url} onChange={(e) => setUrl(e.target.value)} />
            </div>
          )}
          <Button
            onClick={submit}
            disabled={!classId || (tab === "file" ? !file : !url) || upFile.isPending || upUrl.isPending || upYt.isPending}
          >
            Upload
          </Button>
        </div>
      </Card>

      <Card>
        <CardHeader title="My materials" />
        <div className="p-2">
          {materials.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !materials.data?.length ? (
            <EmptyState title="No materials yet" />
          ) : (
            <Table head={["Name", "Type", "Status"]}>
              {materials.data.map((m) => (
                <tr key={m.id} className="border-b border-slate-50">
                  <td className="px-4 py-2 font-medium text-slate-700 truncate max-w-xs">{m.filename}</td>
                  <td className="px-4 py-2">
                    <Badge>{m.source_type}</Badge>
                  </td>
                  <td className="px-4 py-2">
                    <Badge tone={m.status === "indexed" ? "green" : m.status === "failed" ? "red" : "amber"}>
                      {m.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </div>
      </Card>
    </div>
  );
}
