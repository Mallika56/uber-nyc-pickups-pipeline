import { useEffect, useState } from "react";
import { api, type BaseShare, type DailyPoint, type GridCell, type HourCell, type Summary } from "./api";
import { BaseBars } from "./components/BaseBars";
import { DailyChart } from "./components/DailyChart";
import { HourHeatmap } from "./components/HourHeatmap";
import { KpiRow } from "./components/KpiRow";
import { PickupMap } from "./components/PickupMap";
import { QualityCard } from "./components/QualityCard";
import { MONTH_NAMES, fmtHour } from "./format";

const HOUR_PRESETS = [
  { label: "All day", from: 0, to: 23 },
  { label: "Morning rush", from: 7, to: 9 },
  { label: "Midday", from: 11, to: 14 },
  { label: "Evening rush", from: 17, to: 19 },
  { label: "Late night", from: 0, to: 3 },
];

/**
 * Run an API call whenever its inputs change, ignoring responses that arrive after the
 * inputs have changed again (so a slow earlier request can't overwrite a newer one).
 */
function useApi<T>(load: () => Promise<T>, deps: unknown[]): [T | null, string | null] {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let current = true;
    load()
      .then((d) => current && (setData(d), setError(null)))
      .catch((e: Error) => current && setError(e.message));
    return () => {
      current = false;
    };
  }, deps);
  return [data, error];
}

export default function App() {
  const [base, setBase] = useState("");
  const [month, setMonth] = useState<number | "">("");
  const [preset, setPreset] = useState(0);
  const hours = HOUR_PRESETS[preset];

  const [summary, summaryError] = useApi<Summary>(api.summary, []);
  const [daily] = useApi<DailyPoint[]>(() => api.daily(base || undefined), [base]);
  const [hourly] = useApi<HourCell[]>(() => api.hourly(base || undefined), [base]);
  const [bases] = useApi<BaseShare[]>(() => api.bases(month || undefined), [month]);
  const [cells] = useApi<GridCell[]>(() => api.map(hours.from, hours.to), [preset]);

  if (summaryError) {
    return (
      <main className="page">
        <p className="error">Couldn't reach the API ({summaryError}). Is it running on port 8000, and has the pipeline been run?</p>
      </main>
    );
  }
  if (!summary) return <main className="page"><p className="muted">Loading…</p></main>;

  const baseName = summary.bases.find((b) => b.base_code === base)?.base_name;

  return (
    <main className="page">
      <header className="header">
        <div>
          <h1>Uber pickups in New York City</h1>
          <p className="muted">
            {summary.total_pickups.toLocaleString("en-US")} pickups, April–September 2014. Trip records from the NYC Taxi &amp;
            Limousine Commission, released to FiveThirtyEight under a Freedom of Information Law request.
          </p>
        </div>
        <label className="control">
          Dispatch base
          <select value={base} onChange={(e) => setBase(e.target.value)}>
            <option value="">All bases</option>
            {summary.bases.map((b) => (
              <option key={b.base_code} value={b.base_code}>
                {b.base_name} ({b.base_code})
              </option>
            ))}
          </select>
        </label>
      </header>

      <KpiRow summary={summary} />

      <section className="card">
        <h2>Daily pickups{baseName ? `: ${baseName}` : ""}</h2>
        {daily ? <DailyChart points={daily} /> : <p className="muted">Loading…</p>}
      </section>

      <section className="card">
        <h2>When people ride{baseName ? `: ${baseName}` : ""}</h2>
        <p className="caption">Average pickups per day for each weekday and hour.</p>
        {hourly ? <HourHeatmap cells={hourly} /> : <p className="muted">Loading…</p>}
      </section>

      <div className="grid-2">
        <section className="card">
          <div className="card-head">
            <h2>Where pickups happen</h2>
          </div>
          <div className="chips" role="group" aria-label="Time of day">
            {HOUR_PRESETS.map((p, i) => (
              <button key={p.label} className={i === preset ? "chip active" : "chip"} onClick={() => setPreset(i)}>
                {p.label}
              </button>
            ))}
          </div>
          <p className="caption">
            Pickups inside the five boroughs, {fmtHour(hours.from)} to {fmtHour(hours.to)} (hours starting in that range).
            Brighter cells are busier, on a log scale. There is no basemap: the city's outline comes from the pickups
            themselves.
          </p>
          {cells ? <PickupMap cells={cells} /> : <p className="muted">Loading…</p>}
        </section>

        <div className="stack">
          <section className="card">
            <div className="card-head">
              <h2>Dispatch bases</h2>
              <label className="control">
                <select value={month} onChange={(e) => setMonth(e.target.value ? Number(e.target.value) : "")}>
                  <option value="">All months</option>
                  {Object.entries(MONTH_NAMES).map(([m, name]) => (
                    <option key={m} value={m}>{name}</option>
                  ))}
                </select>
              </label>
            </div>
            <p className="caption">Pickups by the TLC-licensed Uber base that dispatched them.</p>
            {bases ? <BaseBars bases={bases} /> : <p className="muted">Loading…</p>}
          </section>
          <QualityCard summary={summary} />
        </div>
      </div>

      <footer className="footer muted">
        Pipeline, API and dashboard by Mallika Chourasia ·{" "}
        <a href="https://github.com/Mallika56/uber-nyc-pickups-pipeline">source on GitHub</a>
      </footer>
    </main>
  );
}
