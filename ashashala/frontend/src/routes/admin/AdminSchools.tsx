import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { adminApi } from "../../api/endpoints";
import type { School } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Input, Label, Skeleton, Table } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";

export default function AdminSchools() {
  const toast = useToast();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");

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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "schools"] }),
  });

  const del = useMutation({
    mutationFn: (id: string) => adminApi.deleteSchool(id),
    onSuccess: () => {
      toast.push("School deleted.", "success");
      qc.invalidateQueries({ queryKey: ["admin", "schools"] });
    },
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
          {schools.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !schools.data?.length ? (
            <EmptyState title="No schools yet" hint="Onboard your first school above." />
          ) : (
            <Table head={["Name", "Status", "Actions"]}>
              {schools.data.map((s) => (
                <tr key={s.id} className="border-b border-slate-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-700">{s.name}</div>
                    <div className="text-xs text-slate-400">{s.address}</div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={s.is_active ? "green" : "red"}>{s.is_active ? "active" : "suspended"}</Badge>
                  </td>
                  <td className="px-4 py-3 flex gap-2">
                    <Button variant="ghost" onClick={() => toggle.mutate(s)}>
                      {s.is_active ? "Suspend" : "Reactivate"}
                    </Button>
                    <Button variant="danger" onClick={() => del.mutate(s.id)}>
                      Delete
                    </Button>
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
