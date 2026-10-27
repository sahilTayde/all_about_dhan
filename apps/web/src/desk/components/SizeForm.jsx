import { useMemo, useState } from "react";
import { inr } from "../../lib/paperBoard.js";

const RISKS = [
  { id: "half", label: "0.5%", frac: 0.005 },
  { id: "one", label: "1%", frac: 0.01 },
  { id: "one5", label: "1.5%", frac: 0.015 },
];

/** Compact paper size. Local only — not an order. */
export function SizeForm({ lots: startLots = 10, entry, qtyPerLot = 50, deskInr = 1000000 }) {
  const [lots, setLots] = useState(Number(startLots) || 10);
  const [risk, setRisk] = useState("one");
  const capital = useMemo(() => {
    const px = Number(entry);
    if (!Number.isFinite(px)) return null;
    return px * lots * qtyPerLot;
  }, [entry, lots, qtyPerLot]);
  const riskAmt = deskInr * (RISKS.find((r) => r.id === risk)?.frac || 0.01);
  return (
    <form className="size-form" data-testid="size-form" onSubmit={(e) => e.preventDefault()}>
      <div className="stepper">
        <button type="button" className="btn btn--ghost" onClick={() => setLots((n) => Math.max(1, n - 1))} aria-label="Fewer lots">
          −
        </button>
        <strong>{lots}</strong>
        <span className="muted">lots</span>
        <button type="button" className="btn btn--ghost" onClick={() => setLots((n) => Math.min(25, n + 1))} aria-label="More lots">
          +
        </button>
      </div>
      <span className="chip chip--active" title="Premium × lots × qty per lot">
        {capital == null ? "Capital pending" : inr(capital, { signed: false })}
      </span>
      <div className="chip-row" role="group" aria-label="Risk preset">
        {RISKS.map((r) => (
          <button key={r.id} type="button" className={`chip${risk === r.id ? " chip--active" : ""}`} onClick={() => setRisk(r.id)}>
            {r.label}
          </button>
        ))}
      </div>
      <span className="muted small">{inr(riskAmt, { signed: false })} risk</span>
    </form>
  );
}
