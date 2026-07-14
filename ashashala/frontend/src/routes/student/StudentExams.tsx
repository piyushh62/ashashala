import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { studentApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Card, CardHeader, Icon, Skeleton, Table } from "../../components/ui";
import { DataBoundary } from "../../components/ui/DataBoundary";

export default function StudentExams() {
  const { t } = useTranslation();
  const exams = useQuery({ queryKey: ["student", "exams"], queryFn: studentApi.exams });

  return (
    <div>
      <PageTitle subtitle={t("student.exams.subtitle")}>{t("student.exams.title")}</PageTitle>

      <Card>
        <CardHeader title={t("student.exams.examTimetable")} icon={<Icon name="exams" />} />
        <DataBoundary
          query={exams}
          isEmpty={(d) => d.length === 0}
          emptyTitle={t("student.exams.noExamsScheduled")}
          emptyHint={t("student.exams.enjoyCalm")}
          loadingFallback={<Skeleton className="h-24 m-3" />}
        >
          {(rows) => (
            <Table head={[t("student.exams.colExam"), t("student.exams.colDate")]}>
              {[...rows]
                .sort((a, b) => a.exam_date.localeCompare(b.exam_date))
                .map((e, i) => (
                  <tr key={i} className="border-b border-slate-50">
                    <td className="px-4 py-2 font-medium text-slate-700">{e.exam_name}</td>
                    <td className="px-4 py-2 text-slate-500">{e.exam_date}</td>
                  </tr>
                ))}
            </Table>
          )}
        </DataBoundary>
      </Card>
    </div>
  );
}
