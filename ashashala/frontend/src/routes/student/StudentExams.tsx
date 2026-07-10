import { useQuery } from "@tanstack/react-query";
import { studentApi } from "../../api/endpoints";
import { PageTitle } from "../../components/layout/AppLayout";
import { Card, CardHeader, Skeleton, Table } from "../../components/ui";
import { DataBoundary } from "../../components/ui/DataBoundary";

export default function StudentExams() {
  const exams = useQuery({ queryKey: ["student", "exams"], queryFn: studentApi.exams });

  return (
    <div>
      <PageTitle subtitle="Your upcoming exams, across all classes.">Exams</PageTitle>

      <Card>
        <CardHeader title="Exam timetable" icon="📝" />
        <DataBoundary
          query={exams}
          isEmpty={(d) => d.length === 0}
          emptyTitle="No exams scheduled"
          emptyHint="Enjoy the calm! 🌿"
          loadingFallback={<Skeleton className="h-24 m-3" />}
        >
          {(rows) => (
            <Table head={["Exam", "Date"]}>
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
