import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import type { MasteryItem } from "../../types/api";
import { EmptyState } from "../ui";

export function MasteryRadar({ data }: { data: MasteryItem[] }) {
  if (!data.length) return <EmptyState title="No mastery data yet" hint="Take a quiz to get started." />;
  // Recharts needs a minimum of 3 axes to render a readable polygon.
  const padded = [...data];
  while (padded.length < 3) padded.push({ topic: `—${padded.length}`, score: 0 });

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={padded} outerRadius="75%">
        <PolarGrid />
        <PolarAngleAxis dataKey="topic" tick={{ fontSize: 12, fill: "#475569" }} />
        <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#94a3b8" }} />
        <Radar dataKey="score" stroke="#4f46e5" fill="#6366f1" fillOpacity={0.5} />
      </RadarChart>
    </ResponsiveContainer>
  );
}
