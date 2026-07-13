import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { parentApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Card, EmptyState, Skeleton } from "../../components/ui";

export default function ParentChildren() {
  const { t } = useTranslation();
  const q = useQuery({ queryKey: ["parent", "children"], queryFn: parentApi.children });

  return (
    <div>
      <PageTitle subtitle={t("parent.children.subtitle")}>{t("parent.children.title")}</PageTitle>
      {q.isLoading ? (
        <Skeleton className="h-24" />
      ) : !q.data?.length ? (
        <EmptyState title={t("parent.children.noLinkedChildren")} hint={t("parent.children.noLinkedChildrenHint")} />
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {q.data.map((c) => (
            <Link key={c.id} to={`/parent/child/${c.id}`}>
              <Card className="p-5 hover:border-brand-300 transition">
                <div className="text-lg font-semibold text-slate-800">{c.name}</div>
                <div className="text-sm text-slate-400">{t("parent.children.gradeLabel", { grade: c.grade ?? "—" })}</div>
                <div className="text-xs text-brand-600 mt-3">{t("parent.children.viewDashboard")}</div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
