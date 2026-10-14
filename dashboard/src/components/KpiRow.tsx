import type { Summary } from "../api";
import { fmtDate, fmtHour, fmtInt } from "../format";

export function KpiRow({ summary }: { summary: Summary }) {
  const { quality, peak_slot: peak } = summary;
  const dupPct = (quality.exact_duplicates / summary.total_pickups) * 100;

  return (
    <section className="kpis">
      <Kpi label="Pickups loaded" value={fmtInt(summary.total_pickups)} note={`${summary.days} days, ${fmtInt(quality.rejected_rows)} rows rejected`} />
      <Kpi
        label="April → September"
        value={`+${summary.growth_first_to_last_month_pct}%`}
        note={`${fmtInt(summary.monthly[0].pickups)} → ${fmtInt(summary.monthly[summary.monthly.length - 1].pickups)} a month`}
      />
      <Kpi label="Busiest day" value={fmtInt(summary.busiest_day.pickups)} note={fmtDate(summary.busiest_day.date)} />
      <Kpi label="Peak hour" value={`${peak.weekday} ${fmtHour(peak.hour)}`} note={`${fmtInt(peak.avg_pickups)} pickups on an average ${peak.weekday}`} />
      <Kpi label="Exact duplicates kept" value={`${dupPct.toFixed(1)}%`} note={`${fmtInt(quality.exact_duplicates)} rows; see README`} />
    </section>
  );
}

function Kpi({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-note">{note}</div>
    </div>
  );
}
