// Typed wrappers around the metrics API. Shapes mirror api/schemas.py.

export interface DailyPoint {
  date: string;
  pickups: number;
}

export interface MonthPoint {
  month: string;
  pickups: number;
}

export interface HourCell {
  iso_weekday: number;
  weekday: string;
  hour: number;
  avg_pickups: number;
}

export interface BaseShare {
  base_code: string;
  base_name: string;
  pickups: number;
  share_pct: number;
}

export interface GridCell {
  lat: number;
  lon: number;
  pickups: number;
}

export interface Summary {
  total_pickups: number;
  first_date: string;
  last_date: string;
  days: number;
  busiest_day: DailyPoint;
  peak_slot: HourCell;
  monthly: MonthPoint[];
  growth_first_to_last_month_pct: number;
  bases: BaseShare[];
  quality: { rejected_rows: number; exact_duplicates: number; outside_nyc_bbox: number };
}

type Params = Record<string, string | number | undefined>;

async function get<T>(path: string, params: Params = {}): Promise<T> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") query.set(key, String(value));
  }
  const url = query.size ? `${path}?${query}` : path;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  summary: () => get<Summary>("/api/summary"),
  daily: (base?: string) => get<DailyPoint[]>("/api/daily", { base }),
  hourly: (base?: string) => get<HourCell[]>("/api/hourly", { base }),
  bases: (month?: number) => get<BaseShare[]>("/api/bases", { month }),
  map: (hourFrom: number, hourTo: number) =>
    get<GridCell[]>("/api/map", { hour_from: hourFrom, hour_to: hourTo }),
};
