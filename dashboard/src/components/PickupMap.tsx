import { useEffect, useMemo, useRef, useState } from "react";
import type { GridCell } from "../api";
import { fmtInt } from "../format";

// Bounding box of the five boroughs; matches in_nyc_bbox in sql/schema.sql.
const LAT_MIN = 40.4774;
const LAT_MAX = 40.9176;
const LON_MIN = -74.2591;
const LON_MAX = -73.7004;
const CELL_DEG = 0.005; // grid size used by marts.pickup_grid
// Longitude degrees shrink with latitude; scale x so the map isn't stretched sideways.
const LON_SCALE = Math.cos(((LAT_MIN + LAT_MAX) / 2) * (Math.PI / 180));

const WIDTH = 560;
const HEIGHT = Math.round((WIDTH * (LAT_MAX - LAT_MIN)) / ((LON_MAX - LON_MIN) * LON_SCALE));

const px = (lon: number) => ((lon - LON_MIN) / (LON_MAX - LON_MIN)) * WIDTH;
const py = (lat: number) => ((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * HEIGHT;
const cellKey = (lat: number, lon: number) => `${lat.toFixed(4)},${lon.toFixed(4)}`;

/**
 * Pickup density drawn straight from the grid cells; no basemap. The shape of the city
 * appears from where people were picked up. Colour is on a log scale because Midtown cells
 * are hundreds of times busier than outer-borough ones.
 */
export function PickupMap({ cells }: { cells: GridCell[] }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<GridCell | null>(null);
  const byKey = useMemo(() => new Map(cells.map((c) => [cellKey(c.lat, c.lon), c])), [cells]);

  useEffect(() => {
    const el = canvas.current;
    const ctx = el?.getContext("2d");
    if (!el || !ctx) return;
    const dpr = window.devicePixelRatio || 1;
    el.width = WIDTH * dpr;
    el.height = HEIGHT * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = "#0b1220";
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    const logMax = Math.log1p(Math.max(...cells.map((c) => c.pickups), 1));
    const w = px(LON_MIN + CELL_DEG) + 0.6;
    const h = py(LAT_MAX - CELL_DEG) + 0.6;
    for (const c of cells) {
      ctx.fillStyle = glow(Math.log1p(c.pickups) / logMax);
      ctx.fillRect(px(c.lon - CELL_DEG / 2), py(c.lat + CELL_DEG / 2), w, h);
    }
  }, [cells]);

  function onMove(e: React.MouseEvent<HTMLCanvasElement>) {
    const box = e.currentTarget.getBoundingClientRect();
    const lon = LON_MIN + ((e.clientX - box.left) / box.width) * (LON_MAX - LON_MIN);
    const lat = LAT_MAX - ((e.clientY - box.top) / box.height) * (LAT_MAX - LAT_MIN);
    const snap = (v: number) => Math.floor(v / CELL_DEG) * CELL_DEG + CELL_DEG / 2;
    setHover(byKey.get(cellKey(snap(lat), snap(lon))) ?? null);
  }

  return (
    <div className="chart-wrap">
      <canvas
        ref={canvas}
        className="map"
        style={{ aspectRatio: `${WIDTH} / ${HEIGHT}` }}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        role="img"
        aria-label="Map of pickup density across New York City"
      />
      <div className="readout">
        {hover
          ? `${fmtInt(hover.pickups)} pickups in the cell at ${hover.lat.toFixed(4)}, ${hover.lon.toFixed(4)}`
          : "Hover the map for the pickup count in a cell (about 550 m by 420 m)"}
      </div>
    </div>
  );
}

// "Inferno"-style ramp: quiet cells sit just above the dark background, busy ones glow yellow.
const RAMP: [number, number, number][] = [
  [20, 11, 52], [66, 10, 104], [106, 23, 110], [147, 38, 103],
  [188, 55, 84], [221, 81, 58], [243, 120, 25], [252, 165, 10], [246, 215, 70], [252, 255, 164],
];

function glow(t: number): string {
  const pos = Math.min(Math.max(t, 0), 1) * (RAMP.length - 1);
  const i = Math.min(Math.floor(pos), RAMP.length - 2);
  const f = pos - i;
  const [r, g, b] = RAMP[i].map((c, k) => Math.round(c + (RAMP[i + 1][k] - c) * f));
  return `rgb(${r} ${g} ${b})`;
}
