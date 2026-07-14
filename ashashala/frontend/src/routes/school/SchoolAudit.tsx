import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { schoolApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Card, CardHeader, EmptyState, Input, Pager, Skeleton, Table } from "../../components/ui";

const PAGE_SIZE = 20;

export default function SchoolAudit() {
  const { t } = useTranslation();
  const [action, setAction] = useState("");
  const [offset, setOffset] = useState(0);
  const q = useQuery({
    queryKey: ["school", "audit", action, offset],
    queryFn: () => schoolApi.audit(action || undefined, PAGE_SIZE, offset),
  });
  const rows = q.data?.items ?? [];
  const total = q.data?.total ?? 0;

  return (
    <div>
      <PageTitle subtitle={t("school.audit.subtitle")}>{t("school.audit.title")}</PageTitle>
      <Card>
        <CardHeader
          title={t("school.audit.recentActivity")}
          action={
            <Input
              placeholder={t("school.audit.filterPlaceholder")}
              value={action}
              onChange={(e) => {
                setAction(e.target.value.toUpperCase());
                setOffset(0);
              }}
              className="w-64"
            />
          }
        />
        <div className="p-2">
          {q.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !rows.length ? (
            <EmptyState title={t("school.audit.noEntries")} />
          ) : (
            <Table
              head={[
                t("school.audit.colTime"),
                t("school.audit.colAction"),
                t("school.audit.colActor"),
                t("school.audit.colTarget"),
                t("school.audit.colStatus"),
              ]}
            >
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-slate-50">
                  <td className="px-4 py-2 text-slate-400 text-xs">{new Date(r.ts).toLocaleString()}</td>
                  <td className="px-4 py-2">
                    <Badge>{r.action}</Badge>
                  </td>
                  <td className="px-4 py-2 text-slate-500 text-xs">{r.actor_role}</td>
                  <td className="px-4 py-2 text-slate-500 text-xs">
                    {r.target_type}:{r.target_id?.slice(0, 8)}
                  </td>
                  <td className="px-4 py-2">
                    <Badge tone={r.status === "success" ? "green" : "red"}>{r.status}</Badge>
                  </td>
                </tr>
              ))}
            </Table>
          )}
          <Pager offset={offset} limit={PAGE_SIZE} total={total} count={rows.length} onOffsetChange={setOffset} />
        </div>
      </Card>
    </div>
  );
}
