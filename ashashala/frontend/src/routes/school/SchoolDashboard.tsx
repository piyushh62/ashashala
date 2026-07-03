import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { schoolApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Card, CardHeader, Skeleton } from "../../components/ui";

export default function SchoolDashboard() {
  const q = useQuery({ queryKey: ["school", "dashboard"], queryFn: schoolApi.dashboard });
  if (q.isLoading) return <Skeleton className="h-40" />;
  const d = q.data ?? {};

  const chartData = [
    { name: "Teachers", value: d.teachers ?? 0 },
    { name: "Students", value: d.students ?? 0 },
    { name: "Classes", value: d.classes ?? 0 },
    { name: "Avg mastery", value: d.avg_mastery ?? 0 },
  ];

  return (
    <div>
      <PageTitle subtitle="Your school at a glance.">School Dashboard</PageTitle>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {chartData.map((c) => (
          <Card key={c.name} className="p-5">
            <div className="text-3xl font-bold text-brand-600">{c.value}</div>
            <div className="text-sm text-slate-500 mt-1">{c.name}</div>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader title="Overview" />
        <div className="p-5">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#475569" }} />
              <YAxis tick={{ fontSize: 12, fill: "#94a3b8" }} />
              <Tooltip />
              <Bar dataKey="value" fill="#6366f1" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
