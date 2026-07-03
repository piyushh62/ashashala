import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { studentApi } from "../../api/endpoints";
import type { QuizOut } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Button, Card, EmptyState, Spinner } from "../../components/ui";
import { QuizGame } from "../../components/quiz/QuizGame";
import { useToast } from "../../components/ui/Toast";

export default function StudentQuiz() {
  const toast = useToast();
  const classes = useQuery({ queryKey: ["student", "classes"], queryFn: studentApi.classes });
  const [quiz, setQuiz] = useState<QuizOut | null>(null);

  const start = useMutation({
    mutationFn: (classId: string) => studentApi.startQuiz({ class_id: classId }),
    onSuccess: (q) => setQuiz(q),
    onError: () => toast.push("Couldn't start a quiz — try again.", "error"),
  });

  if (quiz) return (
    <div>
      <PageTitle>Practice Quiz</PageTitle>
      <QuizGame quiz={quiz} onDone={() => setQuiz(null)} />
    </div>
  );

  const classId = classes.data?.class_ids?.[0];

  return (
    <div>
      <PageTitle subtitle="An adaptive quiz on your weakest topic.">Practice Quiz</PageTitle>
      <Card className="p-8 text-center">
        {classes.isLoading ? (
          <Spinner label="Loading…" />
        ) : !classId ? (
          <EmptyState title="You're not enrolled in a class yet" />
        ) : (
          <>
            <div className="text-5xl mb-3">🧠</div>
            <p className="text-slate-600 mb-5">Ready to practice? We'll pick the topic you need most.</p>
            <Button onClick={() => start.mutate(classId)} disabled={start.isPending}>
              {start.isPending ? "Generating…" : "Start quiz"}
            </Button>
          </>
        )}
      </Card>
    </div>
  );
}
