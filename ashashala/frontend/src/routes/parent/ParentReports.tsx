import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { parentApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, Icon, Skeleton } from "../../components/ui";
import { DataBoundary } from "../../components/ui/DataBoundary";
import { useToast } from "../../components/ui/Toast";
import { formatDate } from "../../lib/dates";

export default function ParentReports() {
  const { t } = useTranslation();
  const { id = "" } = useParams();
  const toast = useToast();
  const reports = useQuery({ queryKey: ["parent", "child", id, "reports"], queryFn: () => parentApi.childReports(id) });
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const download = useMutation({
    mutationFn: (reportId: string) => parentApi.downloadReportPdf(id, reportId),
    onMutate: (reportId) => setDownloadingId(reportId),
    onSettled: () => setDownloadingId(null),
    onError: () => toast.push(t("parent.reports.downloadFailed"), "error"),
  });

  return (
    <div>
      <Link to={`/parent/child/${id}`} className="text-sm text-brand-600 hover:underline">
        {t("parent.back")}
      </Link>
      <PageTitle subtitle={t("parent.reports.subtitle")}>{t("parent.reports.title")}</PageTitle>

      <DataBoundary
        query={reports}
        isEmpty={(d) => d.length === 0}
        emptyTitle={t("parent.reports.noReportsSentYet")}
        emptyHint={t("parent.reports.noReportsSentYetHint")}
        loadingFallback={<Skeleton className="h-32" />}
      >
        {(rows) => (
          <div className="space-y-4">
            {[...rows]
              .sort((a, b) => b.period_start.localeCompare(a.period_start))
              .map((r) => (
                <Card key={r.id}>
                  <CardHeader
                    title={`${formatDate(r.period_start)} → ${formatDate(r.period_end)}`}
                    subtitle={r.sent_at ? t("parent.reports.sentOn", { date: formatDate(r.sent_at) }) : undefined}
                    action={
                      <div className="flex items-center gap-2">
                        <Badge tone="green">{r.status}</Badge>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => download.mutate(r.id)}
                          disabled={downloadingId === r.id}
                        >
                          <Icon name="download" className="w-4 h-4" />
                          {downloadingId === r.id ? t("parent.reports.downloading") : t("parent.reports.downloadPdf")}
                        </Button>
                      </div>
                    }
                  />
                  <div className="p-5 space-y-4">
                    {r.narrative && (
                      <div className="prose prose-sm prose-slate max-w-none dark:prose-invert whitespace-pre-line">
                        {r.narrative}
                      </div>
                    )}
                    {r.mastery_snapshot_json.length > 0 && (
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">
                          {t("parent.reports.masterySnapshot")}
                        </div>
                        <div className="space-y-2">
                          {r.mastery_snapshot_json.map((m) => (
                            <div key={m.topic}>
                              <div className="flex justify-between text-sm mb-1">
                                <span className="text-slate-600">{m.topic}</span>
                                <span className="text-slate-400">{m.score}/100</span>
                              </div>
                              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                                <div className="h-full bg-brand-500" style={{ width: `${m.score}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {r.teacher_notes && (
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1">
                          {t("parent.reports.teacherNotes")}
                        </div>
                        <p className="text-sm text-slate-600">{r.teacher_notes}</p>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
          </div>
        )}
      </DataBoundary>
    </div>
  );
}
