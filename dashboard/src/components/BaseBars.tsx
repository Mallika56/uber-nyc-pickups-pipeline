import type { BaseShare } from "../api";
import { fmtInt } from "../format";

/** Pickups per dispatch base as horizontal bars, largest first. */
export function BaseBars({ bases }: { bases: BaseShare[] }) {
  const max = Math.max(...bases.map((b) => b.pickups), 1);
  return (
    <ul className="bars">
      {bases.map((b) => (
        <li key={b.base_code}>
          <div className="bar-label">
            <span>
              {b.base_name} <span className="muted">{b.base_code}</span>
            </span>
            <span>
              {fmtInt(b.pickups)} <span className="muted">({b.share_pct.toFixed(1)}%)</span>
            </span>
          </div>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(b.pickups / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
