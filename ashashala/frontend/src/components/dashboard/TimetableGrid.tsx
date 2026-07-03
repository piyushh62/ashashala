import type { TimetableRow } from "../../types/api";
import { EmptyState } from "../ui";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function TimetableGrid({ rows }: { rows: TimetableRow[] }) {
  if (!rows.length) return <EmptyState title="No periods scheduled" />;

  const maxPeriod = Math.max(...rows.map((r) => r.period_number), 6);
  const periods = Array.from({ length: maxPeriod }, (_, i) => i + 1);
  const cell = (day: number, period: number) =>
    rows.find((r) => r.day_of_week === day && r.period_number === period);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr>
            <th className="p-2 text-slate-400">Period</th>
            {DAYS.map((d) => (
              <th key={d} className="p-2 text-slate-500 font-medium">
                {d}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {periods.map((p) => (
            <tr key={p}>
              <td className="p-2 text-center text-slate-400 font-medium">{p}</td>
              {DAYS.map((_, dayIdx) => {
                const c = cell(dayIdx, p);
                return (
                  <td key={dayIdx} className="p-1 border border-slate-100">
                    {c ? (
                      <div className="bg-brand-50 text-brand-700 rounded px-2 py-1 text-center">
                        <div className="font-medium truncate">{c.subject_id.slice(0, 8)}</div>
                        {c.room && <div className="text-[10px] text-brand-500">{c.room}</div>}
                      </div>
                    ) : (
                      <div className="h-6" />
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
