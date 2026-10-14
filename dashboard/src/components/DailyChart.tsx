import { useMemo, useState } from "react";
import type { DailyPoint } from "../api";
import { fmtCompact, fmtDate, fmtInt, fmtMonth } from "../format";

const W = 960;
const H = 280;
const M = { top: 16, right: 16, bottom: 28, left: 48 };

/** Daily pickups as a line over an area, with a hover readout. */
export function DailyChart({ points }: { points: DailyPoint[] }) {
  const [hover, setHover] = useState<number | null>(null);

  const geom = useMemo(() => {
    const max = Math.max(...points.map((p) => p.pickups), 1);
    const step = niceStep(max / 4);
    const yMax = Math.ceil(max / step) * step;
    const x = (i: number) => M.left + (i / Math.max(points.length - 1, 1)) * (W - M.left - M.right);
    const y = (v: number) => H - M.bottom - (v / yMax) * (H - M.top - M.bottom);
    const line = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.pickups).toFixed(1)}`).join("");
    const area = `${line}L${x(points.length - 1)},${y(0)}L${x(0)},${y(0)}Z`;
    const ticks = Array.from({ length: Math.round(yMax / step) + 1 }, (_, k) => k * step);
    const months = points.flatMap((p, i) => (p.date.endsWith("-01") ? [{ i, label: fmtMonth(p.date) }] : []));
    return { x, y, line, area, ticks, months };
  }, [points]);

  if (!points.length) return <p className="empty">No data for this selection.</p>;

  function onMove(e: React.MouseEvent<SVGSVGElement>) {
    const box = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - box.left) / box.width) * W;
    const i = Math.round(((px - M.left) / (W - M.left - M.right)) * (points.length - 1));
    setHover(Math.min(Math.max(i, 0), points.length - 1));
  }

  const h = hover !== null ? points[hover] : null;
  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} className="chart" onMouseMove={onMove} onMouseLeave={() => setHover(null)} role="img" aria-label="Daily pickups, April to September 2014">
        {geom.ticks.map((t) => (
          <g key={t}>
            <line x1={M.left} x2={W - M.right} y1={geom.y(t)} y2={geom.y(t)} className="grid" />
            <text x={M.left - 8} y={geom.y(t)} className="axis" textAnchor="end" dominantBaseline="middle">{fmtCompact(t)}</text>
          </g>
        ))}
        {geom.months.map((m) => (
          <text key={m.i} x={geom.x(m.i)} y={H - 8} className="axis" textAnchor="start">{m.label}</text>
        ))}
        <path d={geom.area} className="area" />
        <path d={geom.line} className="line" />
        {h && hover !== null && (
          <g>
            <line x1={geom.x(hover)} x2={geom.x(hover)} y1={M.top} y2={H - M.bottom} className="crosshair" />
            <circle cx={geom.x(hover)} cy={geom.y(h.pickups)} r={4} className="dot" />
          </g>
        )}
      </svg>
      <div className="readout">{h ? `${fmtDate(h.date)}: ${fmtInt(h.pickups)} pickups` : "Hover the chart for a daily count"}</div>
    </div>
  );
}

/** Round a raw axis step up to 1, 2 or 5 times a power of ten. */
function niceStep(raw: number): number {
  const pow = 10 ** Math.floor(Math.log10(raw || 1));
  const f = raw / pow;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * pow;
}
