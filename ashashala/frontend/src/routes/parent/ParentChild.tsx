import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { parentApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { MasteryRadar } from "../../components/dashboard/MasteryRadar";
import { TimetableGrid } from "../../components/dashboard/TimetableGrid";
import { Card, CardHeader, EmptyState, Skeleton } from "../../components/ui";

export default function ParentChild() {
  const { id = "" } = useParams();
  const dash = useQuery({ queryKey: ["parent", "child", id], queryFn: () => parentApi.childDashboard(id) });
  const tt = useQuery({ queryKey: ["parent", "child", id, "tt"], queryFn: () => parentApi.childTimetable(id) });

  return (
    <div>
      <Link to="/parent" className="text-sm text-brand-600 hover:underline">
        ← All children
      </Link>
      <PageTitle subtitle="Read-only progress overview.">
        {dash.data?.student.name ?? "Child"}
      </PageTitle>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Mastery" />
          <div className="p-4">
            {dash.isLoading ? <Skeleton className="h-64" /> : <MasteryRadar data={dash.data?.mastery ?? []} />}
          </div>
        </Card>
        <Card>
          <CardHeader title="Timetable" />
          <div className="p-4">
            {tt.isLoading ? <Skeleton className="h-40" /> : tt.data?.length ? <TimetableGrid rows={tt.data} /> : <EmptyState title="No periods" />}
          </div>
        </Card>
      </div>
    </div>
  );
}
