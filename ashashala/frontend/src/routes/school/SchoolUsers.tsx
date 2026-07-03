import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { schoolApi } from "../../api/endpoints";
import type { Role } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Input, Label, Skeleton, Table } from "../../components/ui";
import { useToast } from "../../components/ui/Toast";

const ROLES: Role[] = ["teacher", "student", "parent"];

export default function SchoolUsers() {
  const toast = useToast();
  const qc = useQueryClient();
  const [filter, setFilter] = useState<Role | "">("");
  const [form, setForm] = useState({ name: "", email: "", role: "student" as Role, grade: "" });

  const users = useQuery({
    queryKey: ["school", "users", filter],
    queryFn: () => schoolApi.listUsers(filter || undefined),
  });

  const create = useMutation({
    mutationFn: () =>
      schoolApi.createUser({
        name: form.name,
        email: form.email,
        role: form.role,
        grade: form.grade ? Number(form.grade) : undefined,
      }),
    onSuccess: (res) => {
      toast.push(
        res.temp_password ? `Created. Temp password: ${res.temp_password}` : "User created.",
        "success",
      );
      setForm({ name: "", email: "", role: "student", grade: "" });
      qc.invalidateQueries({ queryKey: ["school", "users"] });
    },
    onError: () => toast.push("Couldn't create user (email may be taken).", "error"),
  });

  return (
    <div>
      <PageTitle subtitle="Invite teachers, students and parents.">Users</PageTitle>

      <Card className="mb-6">
        <CardHeader title="Add a user" />
        <form
          className="p-5 grid md:grid-cols-5 gap-3 items-end"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div>
            <Label>Name</Label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div>
            <Label>Email</Label>
            <Input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
          </div>
          <div>
            <Label>Role</Label>
            <select
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as Role })}
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label>Grade</Label>
            <Input
              type="number"
              value={form.grade}
              onChange={(e) => setForm({ ...form, grade: e.target.value })}
              disabled={form.role !== "student"}
            />
          </div>
          <Button type="submit" disabled={create.isPending}>
            Add
          </Button>
        </form>
      </Card>

      <Card>
        <CardHeader
          title="All users"
          action={
            <select
              className="text-sm border border-slate-300 rounded-lg px-2 py-1"
              value={filter}
              onChange={(e) => setFilter(e.target.value as Role | "")}
            >
              <option value="">All roles</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          }
        />
        <div className="p-2">
          {users.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !users.data?.length ? (
            <EmptyState title="No users found" />
          ) : (
            <Table head={["Name", "Email", "Role", "Status"]}>
              {users.data.map((u) => (
                <tr key={u.id} className="border-b border-slate-50">
                  <td className="px-4 py-2 font-medium text-slate-700">{u.name}</td>
                  <td className="px-4 py-2 text-slate-500">{u.email}</td>
                  <td className="px-4 py-2">
                    <Badge>{u.role}</Badge>
                  </td>
                  <td className="px-4 py-2">
                    <Badge tone={u.is_active ? "green" : "red"}>{u.is_active ? "active" : "inactive"}</Badge>
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
