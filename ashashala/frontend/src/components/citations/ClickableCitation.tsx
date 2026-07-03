import type { Citation } from "../../types/api";

// Renders a citation as a clickable chip:
//  - PDF/file -> opens the R2 URL (at page via #page= when the viewer supports it)
//  - YouTube  -> opens the video at the timestamp
//  - URL      -> opens in a new tab
function tsToSeconds(ts: string | null): number | null {
  if (!ts) return null;
  const m = ts.match(/(?:(\d+)m)?(\d+)s/);
  if (!m) return null;
  return (parseInt(m[1] || "0", 10) * 60) + parseInt(m[2] || "0", 10);
}

function hrefFor(c: Citation): string | null {
  if (c.source_type === "youtube" && c.url) {
    const secs = tsToSeconds(c.timestamp);
    return secs != null ? `${c.url}${c.url.includes("?") ? "&" : "?"}t=${secs}` : c.url;
  }
  if (c.url) {
    return c.page != null && /\.pdf($|\?)/i.test(c.url) ? `${c.url}#page=${c.page}` : c.url;
  }
  return null;
}

function labelFor(c: Citation): string {
  if (c.source_type === "youtube") return `▶ ${c.title || "Video"}${c.timestamp ? ` · ${c.timestamp}` : ""}`;
  if (c.source_type === "pdf") return `📄 ${c.filename || "Document"}${c.page != null ? ` · p.${c.page}` : ""}`;
  return `🔗 ${c.title || c.url || "Source"}`;
}

export function ClickableCitation({ citation }: { citation: Citation }) {
  const href = hrefFor(citation);
  const label = labelFor(citation);
  const cls =
    "inline-flex items-center text-xs px-2 py-1 rounded-full bg-slate-100 hover:bg-brand-100 text-slate-700 transition max-w-full truncate";
  if (!href) return <span className={cls}>{label}</span>;
  return (
    <a href={href} target="_blank" rel="noreferrer" className={cls} title={label}>
      {label}
    </a>
  );
}

export function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations?.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {citations.map((c, i) => (
        <ClickableCitation key={i} citation={c} />
      ))}
    </div>
  );
}
