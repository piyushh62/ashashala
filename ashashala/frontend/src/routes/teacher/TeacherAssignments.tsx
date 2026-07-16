import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { teacherApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Icon, Skeleton, Table } from "../../components/ui";

export default function TeacherAssignments() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const tasks = useQuery({ queryKey: ["teacher", "assignment-tasks"], queryFn: teacherApi.listAssignmentTasks });

  const rows = tasks.data ?? [];

  return (
    <div>
      <PageTitle subtitle={t("teacher.assignments.subtitle")}>
        {t("teacher.assignments.title")}
      </PageTitle>

      <Card>
        <CardHeader
          title={t("teacher.assignments.assignmentsCard")}
          action={
            <Button size="sm" onClick={() => navigate("/teacher/assignments/new")}>
              <Icon name="add" className="w-4 h-4" />
              {t("teacher.assignments.newAssignment")}
            </Button>
          }
        />
        <div className="p-2">
          {tasks.isLoading ? (
            <Skeleton className="h-24 m-3" />
          ) : !rows.length ? (
            <EmptyState title={t("teacher.assignments.noAssignmentsYet")} hint={t("teacher.assignments.noAssignmentsYetHint")} />
          ) : (
            <Table head={[t("teacher.assignments.colTopic"), t("teacher.assignments.colClass"), t("teacher.assignments.colDue"), t("teacher.assignments.colSubmissions"), t("teacher.assignments.colStatus")]}>
              {rows.map((a) => (
                <tr key={a.id} className="border-b border-slate-50">
                  <td className="px-4 py-2 font-medium text-slate-700">{a.topic}</td>
                  <td className="px-4 py-2 text-slate-500">{a.class_name}</td>
                  <td className="px-4 py-2 text-slate-500">{a.due_date}</td>
                  <td className="px-4 py-2 text-slate-500">{a.submission_count}</td>
                  <td className="px-4 py-2">
                    <Badge tone={a.status === "published" ? "green" : "slate"}>{a.status}</Badge>
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
