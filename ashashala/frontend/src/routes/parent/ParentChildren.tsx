import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { parentApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Card, EmptyState, Skeleton } from "../../components/ui";

export default function ParentChildren() {
  const q = useQuery({ queryKey: ["parent", "children"], queryFn: parentApi.children });

  return (
    <div>
      <PageTitle subtitle="Read-only view of your linked children.">My Children</PageTitle>
      {q.isLoading ? (
        <Skeleton className="h-24" />
      ) : !q.data?.length ? (
        <EmptyState title="No linked children" hint="Ask the school to link your account." />
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {q.data.map((c) => (
            <Link key={c.id} to={`/parent/child/${c.id}`}>
              <Card className="p-5 hover:border-brand-300 transition">
                <div className="text-lg font-semibold text-slate-800">{c.name}</div>
                <div className="text-sm text-slate-400">Grade {c.grade ?? "—"}</div>
                <div className="text-xs text-brand-600 mt-3">View dashboard →</div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
