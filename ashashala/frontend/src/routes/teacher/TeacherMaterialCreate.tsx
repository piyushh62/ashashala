import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, CardHeader, EmptyState, Input, Select } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";
import { Dropzone } from "../../components/ui/Dropzone";
import { useToast } from "../../components/ui/Toast";

type Tab = "file" | "url" | "youtube";

const urlSchema = z.string().url("Enter a valid URL (including https://)");
const youtubeSchema = urlSchema.refine((v) => /youtu\.?be/.test(v), "Enter a valid YouTube URL");

const URL_VALIDATION_MESSAGE_KEYS: Record<string, string> = {
  "Enter a valid URL (including https://)": "teacher.materials.invalidUrl",
  "Enter a valid YouTube URL": "teacher.materials.invalidYoutubeUrl",
};

export default function TeacherMaterialCreate() {
  const { t } = useTranslation();
  const toast = useToast();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("file");
  const [classId, setClassId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [url, setUrl] = useState("");
  const [urlError, setUrlError] = useState<string | undefined>();
  const [file, setFile] = useState<File | null>(null);

  const assignments = useQuery({ queryKey: ["teacher", "assignments"], queryFn: teacherApi.assignments });

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
    toast.push(t("teacher.materials.uploaded"), "success");
    qc.invalidateQueries({ queryKey: ["teacher", "materials"] });
    navigate("/teacher/materials");
  };
  const fail = () => toast.push(t("teacher.materials.uploadFailed"), "error");

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
      <PageTitle subtitle={t("teacher.materials.subtitle")}>{t("teacher.materials.addMaterial")}</PageTitle>

      <Card>
        <CardHeader title={t("teacher.materials.addMaterial")} />
        <div className="px-5 pt-4 flex gap-2">
          {(["file", "url", "youtube"] as Tab[]).map((tabOption) => (
            <button
              key={tabOption}
              onClick={() => {
                setTab(tabOption);
                setUrlError(undefined);
              }}
              className={`px-3 py-1.5 rounded-lg text-sm ${
                tab === tabOption ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              {tabOption === "file" ? t("teacher.materials.tabFile") : tabOption === "url" ? t("teacher.materials.tabUrl") : t("teacher.materials.tabYoutube")}
            </button>
          ))}
        </div>
        {!assignments.isLoading && !assignments.data?.length ? (
          <div className="p-5">
            <EmptyState title={t("teacher.materials.noClassAssignments")} hint={t("teacher.materials.noClassAssignmentsHint")} />
          </div>
        ) : (
          <div className="p-5 grid md:grid-cols-3 gap-3 items-start">
            <FormField label={t("teacher.materials.class")}>
              <Select value={classId} onChange={(e) => { setClassId(e.target.value); setSubjectId(""); }}>
                <option value="">{assignments.isLoading ? t("common.loading") : t("teacher.materials.selectAClass")}</option>
                {classOptions.map(([id, name]) => (
                  <option key={id} value={id}>{name}</option>
                ))}
              </Select>
            </FormField>
            <FormField label={t("teacher.materials.subject")} optional>
              <Select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} disabled={!classId}>
                <option value="">{t("teacher.materials.noSpecificSubject")}</option>
                {subjectsForClass.map((a) => (
                  <option key={a.subject_id} value={a.subject_id}>{a.subject_name}</option>
                ))}
              </Select>
            </FormField>
            {tab === "file" ? (
              <FormField label={t("teacher.materials.file")}>
                <Dropzone
                  file={file}
                  onFile={setFile}
                  accept={{
                    "application/pdf": [".pdf"],
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
                    "text/plain": [".txt"],
                    "image/jpeg": [".jpg"],
                    "image/png": [".png"],
                  }}
                  browseLabel={t("teacher.materials.dropzoneLabel")}
                  hint={t("teacher.materials.dropzoneHint")}
                />
              </FormField>
            ) : (
              <FormField
                label={tab === "url" ? t("teacher.materials.url") : t("teacher.materials.youtubeUrl")}
                error={urlError ? t(URL_VALIDATION_MESSAGE_KEYS[urlError] ?? urlError) : undefined}
              >
                <Input
                  value={url}
                  invalid={!!urlError}
                  onChange={(e) => { setUrl(e.target.value); setUrlError(undefined); }}
                  placeholder={t("teacher.materials.urlPlaceholder")}
                />
              </FormField>
            )}
            <Button
              onClick={submit}
              disabled={!classId || (tab === "file" ? !file : !url) || upFile.isPending || upUrl.isPending || upYt.isPending}
            >
              {t("teacher.materials.upload")}
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
