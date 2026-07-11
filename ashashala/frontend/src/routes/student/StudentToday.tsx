import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { studentApi } from "../../api/endpoints";
import type { LearningFeedItemOut } from "../../types/api";
import { PageTitle } from "../../components/layout/AppLayout";
import { Badge, Button, Card, CardHeader, EmptyState, Skeleton } from "../../components/ui";

export default function StudentToday() {
  const feed = useQuery({ queryKey: ["student", "today"], queryFn: studentApi.today });
  const items = feed.data ?? [];

  return (
    <div>
      <PageTitle subtitle="A short explainer for each class on your timetable today.">Today's Learning</PageTitle>
      {feed.isLoading ? (
        <Skeleton className="h-40" />
      ) : !items.length ? (
        <EmptyState
          title="Nothing scheduled today"
          hint="Check back on a school day once your timetable has classes on it."
          icon="🌿"
        />
      ) : (
        <div className="space-y-5">
          {items.map((item, i) => (
            <FeedCard key={i} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function FeedCard({ item }: { item: LearningFeedItemOut }) {
  const [revealed, setRevealed] = useState<Record<number, boolean>>({});

  return (
    <Card>
      <CardHeader
        title={item.topic}
        subtitle={`Period ${item.period_number}`}
        icon="📖"
        action={<Badge tone="brand">Explainer</Badge>}
      />
      <div className="p-5 space-y-5">
        <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{item.explainer}</p>

        {item.questions.length > 0 && (
          <div className="space-y-3 pt-1 border-t border-slate-100">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400 pt-3">
              Check yourself
            </div>
            {item.questions.map((q, qi) => (
              <div key={qi} className="rounded-xl bg-slate-50 px-4 py-3">
                <p className="text-sm font-medium text-slate-700">{q.question}</p>
                {q.options && (
                  <ul className="mt-2 space-y-1">
                    {q.options.map((o, oi) => (
                      <li key={oi} className="text-sm text-slate-500">
                        {String.fromCharCode(65 + oi)}. {o}
                      </li>
                    ))}
                  </ul>
                )}
                {revealed[qi] ? (
                  <p className="mt-2 text-sm text-brand-700 font-medium">Answer: {q.answer}</p>
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-2"
                    onClick={() => setRevealed((r) => ({ ...r, [qi]: true }))}
                  >
                    Show answer
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
