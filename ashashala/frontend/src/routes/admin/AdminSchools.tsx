import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { adminApi } from "../../api/endpoints";
import type { School } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, Input, Label, Skeleton, Table } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";
import { Modal, useConfirm } from "../../components/ui/Modal";
import { DataBoundary } from "../../components/ui/DataBoundary";

export default function AdminSchools() {
  const toast = useToast();
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [detailsFor, setDetailsFor] = useState<School | null>(null);
  const [adminFor, setAdminFor] = useState<School | null>(null);
  const [adminName, setAdminName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [tempCredential, setTempCredential] = useState<{ email: string; password: string } | null>(null);

  const details = useQuery({
    queryKey: ["admin", "school-dashboard", detailsFor?.id],
    queryFn: () => adminApi.schoolDashboard(detailsFor!.id),
    enabled: !!detailsFor,
  });

  const schools = useQuery({ queryKey: ["admin", "schools"], queryFn: () => api.get<School[]>("/api/v1/admin/schools") });

  const create = useMutation({
    mutationFn: () => adminApi.createSchool({ name, address: address || undefined }),
    onSuccess: () => {
      toast.push("School created.", "success");
      setName("");
      setAddress("");
      qc.invalidateQueries({ queryKey: ["admin", "schools"] });
    },
    onError: () => toast.push("Couldn't create school.", "error"),
  });

  const toggle = useMutation({
    mutationFn: (s: School) => adminApi.updateSchool(s.id, { is_active: !s.is_active }),
    onSuccess: (_data, s) => {
      toast.push(s.is_active ? "School suspended." : "School reactivated.", "success");
      qc.invalidateQueries({ queryKey: ["admin", "schools"] });
    },
    onError: () => toast.push("Couldn't update school status.", "error"),
  });

  const del = useMutation({
    mutationFn: (id: string) => adminApi.deleteSchool(id),
    onSuccess: () => {
      toast.push("School deleted.", "success");
      qc.invalidateQueries({ queryKey: ["admin", "schools"] });
    },
    onError: () => toast.push("Couldn't delete school.", "error"),
  });

  const createAdmin = useMutation({
    mutationFn: () => adminApi.createSchoolAdmin(adminFor!.id, { name: adminName, email: adminEmail }),
    onSuccess: (res) => {
      setAdminFor(null);
      setTempCredential({ email: adminEmail, password: res.temp_password });
      setAdminName("");
      setAdminEmail("");
    },
    onError: () => toast.push("Couldn't create school admin (email may be taken).", "error"),
  });

  const askSuspend = (s: School) =>
    confirm.ask({
      title: s.is_active ? "Suspend this school?" : "Reactivate this school?",
      description: s.is_active
        ? `${s.name} and everyone in it will immediately lose access to the platform.`
        : `${s.name} will regain access to the platform.`,
      tone: s.is_active ? "danger" : "primary",
      confirmLabel: s.is_active ? "Suspend" : "Reactivate",
      onConfirm: () => toggle.mutateAsync(s),
    });

  const askDelete = (s: School) =>
    confirm.ask({
      title: "Delete this school?",
      description: `This permanently removes ${s.name} and all of its data. This can't be undone.`,
      tone: "danger",
      confirmLabel: "Delete",
      onConfirm: () => del.mutateAsync(s.id),
    });

  return (
    <div>
      <PageTitle subtitle="Onboard and manage schools across the platform.">Schools</PageTitle>

      <Card className="mb-6">
        <CardHeader title="Onboard a school" />
        <form
          className="p-5 flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div className="flex-1 min-w-[180px]">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="flex-1 min-w-[180px]">
            <Label>Address</Label>
            <Input value={address} onChange={(e) => setAddress(e.target.value)} />
          </div>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending ? "Creating…" : "Create"}
          </Button>
        </form>
      </Card>

      <Card>
        <CardHeader title="All schools" />
        <div className="p-2">
          <DataBoundary
            query={schools}
            isEmpty={(data) => data.length === 0}
            emptyTitle="No schools yet"
            emptyHint="Onboard your first school above."
            loadingFallback={<div className="h-24 m-3 rounded-xl bg-slate-100 animate-pulse" />}
          >
            {(data) => (
              <Table head={["Name", "Status", "Actions"]}>
                {data.map((s) => (
                  <tr key={s.id} className="border-b border-slate-50">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-700">{s.name}</div>
                      <div className="text-xs text-slate-400">{s.address}</div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={s.is_active ? "green" : "red"}>{s.is_active ? "active" : "suspended"}</Badge>
                    </td>
                    <td className="px-4 py-3 flex gap-2">
                      <Button variant="ghost" onClick={() => setDetailsFor(s)}>
                        View details
                      </Button>
                      <Button variant="ghost" onClick={() => setAdminFor(s)}>
                        Add admin
                      </Button>
                      <Button variant="ghost" onClick={() => askSuspend(s)}>
                        {s.is_active ? "Suspend" : "Reactivate"}
                      </Button>
                      <Button variant="danger" onClick={() => askDelete(s)}>
                        Delete
                      </Button>
                    </td>
                  </tr>
                ))}
              </Table>
            )}
          </DataBoundary>
        </div>
      </Card>

      <Modal
        open={!!detailsFor}
        onOpenChange={(open) => !open && setDetailsFor(null)}
        title={detailsFor?.name ?? "School"}
        description="Snapshot of teachers, students, classes and mastery."
        size="sm"
      >
        {details.isLoading ? (
          <Skeleton className="h-32" />
        ) : (
          <div className="grid grid-cols-2 gap-3">
            <Stat label="Teachers" value={details.data?.teachers ?? 0} />
            <Stat label="Students" value={details.data?.students ?? 0} />
            <Stat label="Classes" value={details.data?.classes ?? 0} />
            <Stat label="Avg mastery" value={details.data?.avg_mastery ?? 0} />
          </div>
        )}
      </Modal>

      <Modal
        open={!!adminFor}
        onOpenChange={(open) => !open && setAdminFor(null)}
        title="Create school admin"
        description={adminFor ? `Add a School Admin for ${adminFor.name}.` : undefined}
        size="sm"
      >
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            createAdmin.mutate();
          }}
        >
          <div>
            <Label>Name</Label>
            <Input value={adminName} onChange={(e) => setAdminName(e.target.value)} required />
          </div>
          <div>
            <Label>Email</Label>
            <Input type="email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)} required />
          </div>
          <Button type="submit" className="w-full" disabled={createAdmin.isPending}>
            {createAdmin.isPending ? "Creating…" : "Create admin"}
          </Button>
        </form>
      </Modal>

      <Modal
        open={!!tempCredential}
        onOpenChange={(open) => !open && setTempCredential(null)}
        title="Temporary password"
        description="Share this password securely — it won't be shown again."
        size="sm"
      >
        {tempCredential && (
          <div className="space-y-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Email</div>
              <div className="text-sm font-medium text-slate-700">{tempCredential.email}</div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Temporary password</div>
              <div className="flex items-center gap-2 mt-1">
                <code className="flex-1 px-3 py-2 rounded-lg bg-slate-50 border border-slate-200 text-sm font-mono text-slate-700">
                  {tempCredential.password}
                </code>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => navigator.clipboard.writeText(tempCredential.password)}
                >
                  Copy
                </Button>
              </div>
            </div>
            <Button type="button" className="w-full" onClick={() => setTempCredential(null)}>
              Done
            </Button>
          </div>
        )}
      </Modal>

      {confirm.dialog}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center rounded-xl bg-slate-50 py-4">
      <div className="text-xl font-bold text-slate-800 tabular-nums">{value}</div>
      <div className="text-[11px] text-slate-400 uppercase tracking-wide mt-0.5">{label}</div>
    </div>
  );
}
