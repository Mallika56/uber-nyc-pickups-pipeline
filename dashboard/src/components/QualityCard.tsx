import type { Summary } from "../api";
import { fmtInt } from "../format";

/** What the pipeline rejected, and what it kept but flagged, with the reasoning. */
export function QualityCard({ summary }: { summary: Summary }) {
  const { quality, total_pickups: total } = summary;
  const pct = (n: number) => `${((n / total) * 100).toFixed(1)}%`;
  const rows: [string, string][] = [
    ["Rows read from the six files", fmtInt(total + quality.rejected_rows)],
    ["Rejected by validation", fmtInt(quality.rejected_rows)],
    ["Exact duplicates, kept", `${fmtInt(quality.exact_duplicates)} (${pct(quality.exact_duplicates)})`],
    ["Outside the five boroughs, kept and flagged", `${fmtInt(quality.outside_nyc_bbox)} (${pct(quality.outside_nyc_bbox)})`],
  ];

  return (
    <section className="card">
      <h2>Data quality</h2>
      <dl className="facts">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="caption">
        Every row is checked for a parseable timestamp, coordinates in range, a known Uber base and the right month for its
        file. Duplicates share the same minute, coordinates and base; with minute-level timestamps two riders picked up at one
        corner in the same minute look identical, so they are counted rather than deleted.
      </p>
    </section>
  );
}
