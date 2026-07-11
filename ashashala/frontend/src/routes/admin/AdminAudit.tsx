import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Input, Select, Skeleton, Table } from "../../components/ui";
import { FormField } from "../../components/ui/FormField";

const PAGE_SIZE = 20;

export default function AdminAudit() {
  const [schoolId, setSchoolId] = useState("");
  const [action, setAction] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [offset, setOffset] = useState(0);

  const schools = useQuery({ queryKey: ["admin", "schools"], queryFn: adminApi.listSchools });
  const q = useQuery({
    queryKey: ["admin", "audit", schoolId, action, dateFrom, dateTo, offset],
    queryFn: () => adminApi.audit({ schoolId: schoolId || undefined, action: action || undefined, dateFrom: dateFrom || undefined, dateTo: dateTo || undefined }, PAGE_SIZE, offset),
  });
  const rows = q.data?.items ?? [];
  const total = q.data?.total ?? 0;
  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = offset + rows.length;

  const schoolName = (id: string | null | undefined) => schools.data?.find((s) => s.id === id)?.name ?? "—";

  const resetOffset = () => setOffset(0);

  return (
    <div>
      <PageTitle subtitle="Every state-changing action and sensitive read, across all schools.">Cross-Tenant Audit Log</PageTitle>
      <Card>
        <CardHeader
          title="Recent activity"
          action={
            <div className="flex flex-wrap items-end gap-3">
              <FormField label="School" optional>
                <Select
                  value={schoolId}
                  onChange={(e) => { setSchoolId(e.target.value); resetOffset(); }}
                  className="w-48"
                >
                  <option value="">All schools</option>
                  {schools.data?.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </Select>
              </FormField>
              <FormField label="Action" optional>
                <Input
                  placeholder="e.g. USER_CREATE"
                  value={action}
                  onChange={(e) => { setAction(e.target.value.toUpperCase()); resetOffset(); }}
                  className="w-48"
                />
              </FormField>
              <FormField label="From" optional>
                <Input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); resetOffset(); }} />
              </FormField>
              <FormField label="To" optional>
                <Input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); resetOffset(); }} />
              </FormField>
            </div>
          }
        />
        <div className="p-2">
          {q.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !rows.length ? (
            <EmptyState title="No audit entries" />
          ) : (
            <Table head={["Time", "School", "Action", "Actor", "Target", "Status"]}>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-slate-50">
                  <td className="px-4 py-2 text-slate-400 text-xs">{new Date(r.ts).toLocaleString()}</td>
                  <td className="px-4 py-2 text-slate-500 text-xs">{schoolName(r.school_id)}</td>
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
