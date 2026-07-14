import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { studentApi } from "../../api/endpoints";
import type { QuizOut } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, EmptyState, Icon, Spinner } from "../../components/ui";
import { QuizGame } from "../../components/quiz/QuizGame";
import { useToast } from "../../components/ui/Toast";

export default function StudentQuiz() {
  const { t } = useTranslation();
  const toast = useToast();
  const classes = useQuery({ queryKey: ["student", "classes"], queryFn: studentApi.classes });
  const [quiz, setQuiz] = useState<QuizOut | null>(null);

  const start = useMutation({
    mutationFn: (classId: string) => studentApi.startQuiz({ class_id: classId }),
    onSuccess: (q) => setQuiz(q),
    onError: () => toast.push(t("student.quiz.startQuizFailed"), "error"),
  });

  if (quiz) return (
    <div>
      <PageTitle>{t("student.quiz.title")}</PageTitle>
      <QuizGame quiz={quiz} onDone={() => setQuiz(null)} />
    </div>
  );

  const classId = classes.data?.class_ids?.[0];

  return (
    <div>
      <PageTitle subtitle={t("student.quiz.subtitle")}>{t("student.quiz.title")}</PageTitle>
      <Card className="p-8 text-center">
        {classes.isLoading ? (
          <Spinner label={t("common.loading")} />
        ) : !classId ? (
          <EmptyState title={t("student.quiz.notEnrolled")} />
        ) : (
          <>
            <div className="mb-3"><Icon name="quiz" className="w-12 h-12 mx-auto" /></div>
            <p className="text-slate-600 mb-5">{t("student.quiz.readyToPractice")}</p>
            <Button onClick={() => start.mutate(classId)} disabled={start.isPending}>
              {start.isPending ? t("student.quiz.generating") : t("student.quiz.startQuiz")}
            </Button>
          </>
        )}
      </Card>
    </div>
  );
}
