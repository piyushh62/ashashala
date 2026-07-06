import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { MasteryItem } from "../../types/api";
import { EmptyState } from "../ui";

// Single-series magnitude on a radial layout → one brand hue, recessive grid,
// hover tooltip (dataviz mark specs). No legend needed for one series.
export function MasteryRadar({ data }: { data: MasteryItem[] }) {
  if (!data.length) return <EmptyState title="No mastery yet" hint="Take a quiz to get started." icon="🧠" />;

  const padded = [...data];
  while (padded.length < 3) padded.push({ topic: "", score: 0 });

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={padded} outerRadius="72%">
        <PolarGrid stroke="#e2e8f0" />
        <PolarAngleAxis dataKey="topic" tick={{ fontSize: 12, fill: "#475569" }} />
        <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#cbd5e1" }} axisLine={false} />
        <Radar dataKey="score" stroke="#4f46e5" strokeWidth={2} fill="#6366f1" fillOpacity={0.35} />
        <Tooltip
          contentStyle={{
            borderRadius: 12,
            border: "1px solid #e2e8f0",
            boxShadow: "0 4px 16px -4px rgba(15,23,42,0.12)",
            fontSize: 12,
          }}
          formatter={(v) => [`${v}/100`, "Mastery"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
