import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Input, Select, Skeleton, Table } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { useToast } from "../../components/ui/Toast";

type Tab = "file" | "url" | "youtube";

const PAGE_SIZE = 20;

const urlSchema = z.string().url("Enter a valid URL (including https://)");
const youtubeSchema = urlSchema.refine((v) => /youtu\.?be/.test(v), "Enter a valid YouTube URL");

export default function TeacherMaterials() {
  const toast = useToast();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("file");
  const [classId, setClassId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [url, setUrl] = useState("");
  const [urlError, setUrlError] = useState<string | undefined>();
  const [file, setFile] = useState<File | null>(null);
  const [offset, setOffset] = useState(0);

  const assignments = useQuery({ queryKey: ["teacher", "assignments"], queryFn: teacherApi.assignments });
  const materials = useQuery({
    queryKey: ["teacher", "materials", offset],
    queryFn: () => teacherApi.materials(PAGE_SIZE, offset),
  });
  const materialRows = materials.data?.items ?? [];
  const total = materials.data?.total ?? 0;
  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = offset + materialRows.length;

  // Subjects taught in the currently-selected class (a teacher can be assigned
  // to the same class for several subjects).
  const subjectsForClass = useMemo(
    () => (assignments.data ?? []).filter((a) => a.class_id === classId),
    [assignments.data, classId],
  );
  const classOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const a of assignments.data ?? []) seen.set(a.class_id, a.class_name);
    return Array.from(seen.entries());
  }, [assignments.data]);

  // Default to the teacher's first assignment once loaded.
  useEffect(() => {
    if (!classId && assignments.data?.length) {
      setClassId(assignments.data[0].class_id);
      setSubjectId(assignments.data[0].subject_id);
    }
  }, [assignments.data, classId]);

  const done = () => {
    toast.push("Uploaded — indexing in the background.", "success");
    setUrl("");
    setFile(null);
    setOffset(0);
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
    if (tab === "file") {
      upFile.mutate();
      return;
    }
    const schema = tab === "youtube" ? youtubeSchema : urlSchema;
    const result = schema.safeParse(url);
    if (!result.success) {
      setUrlError(result.error.issues[0]?.message);
      return;
    }
    setUrlError(undefined);
    if (tab === "url") upUrl.mutate();
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
              onClick={() => {
                setTab(t);
                setUrlError(undefined);
              }}
              className={`px-3 py-1.5 rounded-lg text-sm ${
                tab === t ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              {t === "file" ? "📄 File" : t === "url" ? "🔗 URL" : "▶ YouTube"}
            </button>
          ))}
        </div>
        {!assignments.isLoading && !assignments.data?.length ? (
          <div className="p-5">
            <EmptyState title="No class assignments yet" hint="Ask your school admin to assign you to a class and subject first." />
          </div>
        ) : (
          <div className="p-5 grid md:grid-cols-3 gap-3 items-start">
            <FormField label="Class">
              <Select value={classId} onChange={(e) => { setClassId(e.target.value); setSubjectId(""); }}>
                <option value="">{assignments.isLoading ? "Loading…" : "Select a class"}</option>
                {classOptions.map(([id, name]) => (
                  <option key={id} value={id}>{name}</option>
                ))}
              </Select>
            </FormField>
            <FormField label="Subject" optional>
              <Select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} disabled={!classId}>
                <option value="">No specific subject</option>
                {subjectsForClass.map((a) => (
                  <option key={a.subject_id} value={a.subject_id}>{a.subject_name}</option>
                ))}
              </Select>
            </FormField>
            {tab === "file" ? (
              <FormField label="File">
                <input type="file" accept=".pdf,.docx,.txt,.jpg,.png" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              </FormField>
            ) : (
              <FormField label={tab === "url" ? "URL" : "YouTube URL"} error={urlError}>
                <Input
                  value={url}
                  invalid={!!urlError}
                  onChange={(e) => { setUrl(e.target.value); setUrlError(undefined); }}
                  placeholder="https://…"
                />
              </FormField>
            )}
            <Button
              onClick={submit}
              disabled={!classId || (tab === "file" ? !file : !url) || upFile.isPending || upUrl.isPending || upYt.isPending}
            >
              Upload
            </Button>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="My materials" />
        <div className="p-2">
          {materials.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !materialRows.length ? (
            <EmptyState title="No materials yet" />
          ) : (
            <Table head={["Name", "Type", "Status"]}>
              {materialRows.map((m) => (
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
          {total > 0 && (
            <div className="flex items-center justify-between px-3 py-3 text-sm text-slate-500">
              <span>
                {rangeStart}–{rangeEnd} of {total}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  disabled={offset === 0}
                >
                  Previous
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  disabled={rangeEnd >= total}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
