import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { QuizOut, QuizSubmitResponse } from "../../types/api";
import { studentApi } from "../../api/endpoints";
import { Button, Card, EmptyState } from "../ui";
import { useToast } from "../ui/Toast";

// Gamified quiz runner: per-question timer, XP tally, and a results view with
// a level-up flourish when mastery increases.
export function QuizGame({ quiz, onDone }: { quiz: QuizOut; onDone: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const [answers, setAnswers] = useState<(number | string)[]>(() => quiz.questions.map(() => ""));
  const [seconds, setSeconds] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<QuizSubmitResponse | null>(null);

  useEffect(() => {
    if (result) return;
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [result]);

  const setAnswer = (i: number, v: number | string) =>
    setAnswers((a) => a.map((x, idx) => (idx === i ? v : x)));

  const submit = async () => {
    setSubmitting(true);
    try {
      const res = await studentApi.submitQuiz(quiz.id, answers);
      setResult(res);
    } catch {
      toast.push(t("student.quizGame.submitFailed"), "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (!quiz.questions.length) return <EmptyState title={t("student.quizGame.noQuestions")} />;

  if (result) {
    const leveledUp = !!result.mastery_update && result.mastery_update.new > result.mastery_update.old;
    return (
      <Card className="p-6 text-center">
        {leveledUp && <div className="text-4xl mb-2 animate-bounce">🎉</div>}
        <h3 className="text-lg font-semibold text-slate-800">{result.feedback_summary}</h3>
        <div className="flex justify-center gap-6 my-4">
          <Stat label={t("student.quizGame.score")} value={`${Math.round(result.attempt_score * 100)}%`} />
          <Stat label={t("student.quizGame.xp")} value={`+${result.total_xp}`} />
          {result.mastery_update && (
            <Stat
              label={t("student.quizGame.mastery")}
              value={`${result.mastery_update.old} → ${result.mastery_update.new}`}
            />
          )}
        </div>
        <div className="text-left space-y-2 max-h-64 overflow-y-auto my-4">
          {result.per_question.map((q) => (
            <div key={q.index} className="text-sm border-l-2 pl-3 border-slate-200">
              <span className={q.score >= 0.5 ? "text-emerald-600" : "text-amber-600"}>
                Q{q.index + 1}: {Math.round(q.score * 100)}%
              </span>{" "}
              — {q.feedback}
              {q.flagged && <span className="ml-1 text-xs text-amber-500">{t("student.quizGame.sentToTeacher")}</span>}
            </div>
          ))}
        </div>
        <Button onClick={onDone}>{t("student.quizGame.done")}</Button>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-800">{t("student.quizGame.quizTopic", { topic: quiz.topic })}</h3>
        <span className="text-sm text-slate-500 tabular-nums">
          ⏱ {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")}
        </span>
      </div>

      <div className="space-y-5">
        {quiz.questions.map((q, i) => (
          <div key={q.index}>
            <p className="font-medium text-slate-700 mb-2">
              {i + 1}. {q.question}{" "}
              {q.xp ? <span className="text-xs text-brand-500">{t("student.quizGame.xpBadge", { xp: q.xp })}</span> : null}
            </p>
            {q.type === "mcq" ? (
              <div className="grid gap-2">
                {(q.options || []).map((opt, oi) => (
                  <label
                    key={oi}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-sm ${
                      answers[i] === oi
                        ? "border-brand-500 bg-brand-50"
                        : "border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    <input
                      type="radio"
                      name={`q-${i}`}
                      checked={answers[i] === oi}
                      onChange={() => setAnswer(i, oi)}
                    />
                    {opt}
                  </label>
                ))}
              </div>
            ) : (
              <textarea
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
                rows={2}
                placeholder={t("student.quizGame.answerPlaceholder")}
                value={String(answers[i] ?? "")}
                onChange={(e) => setAnswer(i, e.target.value)}
              />
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 flex justify-end gap-2">
        <Button variant="ghost" onClick={onDone}>
          {t("common.cancel")}
        </Button>
        <Button onClick={submit} disabled={submitting}>
          {submitting ? t("student.quizGame.grading") : t("student.quizGame.submitQuiz")}
        </Button>
      </div>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-2xl font-bold text-brand-600">{value}</div>
      <div className="text-xs text-slate-400 uppercase tracking-wide">{label}</div>
    </div>
  );
}
