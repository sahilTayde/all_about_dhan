import { useState } from "react";
import { CleanupCanvas } from "../CleanupCanvas.jsx";
import { ConfirmButton } from "../components/Confirm.jsx";
import { DecisionTrace } from "../components/DecisionTrace.jsx";
import { FounderControls } from "../components/FounderControls.jsx";
import { agedAlerts, strikeOf } from "../lib/deskModel.js";
import { AlertList } from "./parts.jsx";

export function OpsPage({ snap, dd, conn }) {
  const [note, setNote] = useState("");
  const [showOld, setShowOld] = useState(false);
  const all = agedAlerts(snap?.alerts);
  const fresh = agedAlerts(snap?.alerts, { maxAgeSec: 86400 });
  const rows = [...dd.open, ...[...dd.closed].sort((a, b) => (b.closed_ts || 0) - (a.closed_ts || 0))];
  const [pick, setPick] = useState(null);
  const trace = rows.find((t) => t.trade_id === pick) || rows[0];
  return (
    <div className="ops" data-testid="ops-page">
      <section className="card">
        <header className="card__head"><h2>Controls (paper)</h2></header>
        <div className="row">
          <ConfirmButton label="Pause slot" testid="pause" title="Pause this paper slot?" body="New paper fills on this slot stay closed until you resume. Not a live order." onConfirm={() => setNote("Slot paused on paper. Not a live halt.")} />
          <ConfirmButton label="Exit open trade" danger testid="exit" title="Exit the open paper trade?" body="Books a paper exit on the open ticket. Orders stay refused." onConfirm={() => setNote(dd.open[0] ? `Paper exit noted on ${dd.open[0].underlying}. Orders refused.` : "No open trade to exit.")} />
        </div>
        {note ? <p className="muted small" data-testid="ops-note">{note}</p> : null}
        <FounderControls />
      </section>
      <section className="card">
        <header className="card__head"><h2>Alerts</h2>
          <label className="muted small"><input type="checkbox" checked={showOld} onChange={(e) => setShowOld(e.target.checked)} /> show alerts older than a day ({all.length - fresh.length})</label>
        </header>
        <AlertList alerts={showOld ? all : fresh} />
      </section>
      <section className="card">
        <header className="card__head"><h2>Health</h2><span className="muted small">feed: {conn}</span></header>
        <ul className="health-list">{(snap?.health || []).map((h) => <li key={h.id}><i className={`dot dot--${h.tone}`} /> {h.name}: <span className="muted">{h.detail}</span></li>)}</ul>
      </section>
      <section className="card">
        <header className="card__head"><h2>Trade trace</h2>
          <select value={trace?.trade_id || ""} onChange={(e) => setPick(e.target.value)} aria-label="Pick a trade">
            {rows.map((t) => <option key={t.trade_id} value={t.trade_id}>{String(t.opened_ist || "").slice(11, 16)} {t.underlying} {strikeOf(t)} {t.side} · {t.book_id}</option>)}
          </select>
        </header>
        <DecisionTrace refreshKey={trace?.last_updated_ts} tradeId={trace?.trade_id} label={trace ? `${trace.underlying} ${trace.side} ${strikeOf(trace) ?? ""}` : null} />
      </section>
      <details className="card details">
        <summary>Cleanup checklist</summary>
        <CleanupCanvas embedded />
      </details>
    </div>
  );
}
