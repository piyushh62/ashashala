import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { parentApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, Skeleton } from "../../components/ui";
import { DataBoundary } from "../../components/ui/DataBoundary";
import { useToast } from "../../components/ui/Toast";

export default function ParentReports() {
  const { id = "" } = useParams();
  const toast = useToast();
  const reports = useQuery({ queryKey: ["parent", "child", id, "reports"], queryFn: () => parentApi.childReports(id) });
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const download = useMutation({
    mutationFn: (reportId: string) => parentApi.downloadReportPdf(id, reportId),
    onMutate: (reportId) => setDownloadingId(reportId),
    onSettled: () => setDownloadingId(null),
    onError: () => toast.push("Couldn't download the report PDF.", "error"),
  });

  return (
    <div>
      <Link to={`/parent/child/${id}`} className="text-sm text-brand-600 hover:underline">
        ← Back
      </Link>
      <PageTitle subtitle="Sent progress reports for this child.">Reports</PageTitle>

      <DataBoundary
        query={reports}
        isEmpty={(d) => d.length === 0}
        emptyTitle="No reports sent yet"
        emptyHint="Your child's teacher will publish reports here once ready."
        loadingFallback={<Skeleton className="h-32" />}
      >
        {(rows) => (
          <div className="space-y-4">
            {[...rows]
              .sort((a, b) => b.period_start.localeCompare(a.period_start))
              .map((r) => (
                <Card key={r.id}>
                  <CardHeader
                    title={`${r.period_start} → ${r.period_end}`}
                    subtitle={r.sent_at ? `Sent ${new Date(r.sent_at).toLocaleDateString()}` : undefined}
                    action={
                      <div className="flex items-center gap-2">
                        <Badge tone="green">{r.status}</Badge>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => download.mutate(r.id)}
                          disabled={downloadingId === r.id}
                        >
                          {downloadingId === r.id ? "Downloading…" : "⬇ PDF"}
                        </Button>
                      </div>
                    }
                  />
                  <div className="p-5 space-y-4">
                    {r.narrative && <p className="text-sm text-slate-600 whitespace-pre-line">{r.narrative}</p>}
                    {r.mastery_snapshot_json.length > 0 && (
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">
                          Mastery snapshot
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
                          Teacher notes
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
