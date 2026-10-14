import { useState } from "react";
import type { HourCell } from "../api";
import { WEEKDAYS, fmtHour, fmtInt } from "../format";

const CELL_W = 34;
const CELL_H = 26;
const LEFT = 40;
const TOP = 22;

/** Average pickups per day for each weekday-hour slot. Darker = busier. */
export function HourHeatmap({ cells }: { cells: HourCell[] }) {
  const [hover, setHover] = useState<HourCell | null>(null);
  const lookup = new Map(cells.map((c) => [`${c.iso_weekday}-${c.hour}`, c]));
  const max = Math.max(...cells.map((c) => c.avg_pickups), 1);

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${LEFT + 24 * CELL_W} ${TOP + 7 * CELL_H}`} className="chart" role="img" aria-label="Average pickups by weekday and hour">
        {Array.from({ length: 24 }, (_, hour) =>
          hour % 3 === 0 ? (
            <text key={hour} x={LEFT + hour * CELL_W + CELL_W / 2} y={TOP - 8} className="axis" textAnchor="middle">{fmtHour(hour)}</text>
          ) : null,
        )}
        {WEEKDAYS.map((day, row) => (
          <g key={day}>
            <text x={LEFT - 8} y={TOP + row * CELL_H + CELL_H / 2} className="axis" textAnchor="end" dominantBaseline="middle">{day}</text>
            {Array.from({ length: 24 }, (_, hour) => {
              const cell = lookup.get(`${row + 1}-${hour}`);
              const value = cell?.avg_pickups ?? 0;
              return (
                <rect
                  key={hour}
                  x={LEFT + hour * CELL_W + 1}
                  y={TOP + row * CELL_H + 1}
                  width={CELL_W - 2}
                  height={CELL_H - 2}
                  rx={3}
                  fill={heat(value / max)}
                  onMouseEnter={() => cell && setHover(cell)}
                  onMouseLeave={() => setHover(null)}
                />
              );
            })}
          </g>
        ))}
      </svg>
      <div className="readout">
        {hover ? `${hover.weekday} ${fmtHour(hover.hour)}: ${fmtInt(hover.avg_pickups)} pickups on an average ${hover.weekday}` : "Hover a cell for the average"}
      </div>
    </div>
  );
}

/** Sequential blue scale from near-white (0) to deep blue (1). */
function heat(t: number): string {
  const lightness = 96 - Math.pow(t, 0.8) * 62;
  return `hsl(214 72% ${lightness.toFixed(1)}%)`;
}
