import { useEffect, useRef } from "react";
import { createChart, ColorType } from "lightweight-charts";
import { num } from "../lib/deskModel.js";

const IST_OFFSET = 19800; // show IST on the time axis

/**
 * Running ₹ P&L after charges, built from closed trades (closed_ts, realized_pnl_inr),
 * with an entry marker at each opened_ts and an exit marker at each closed_ts.
 */
export function PnlChart({ trades, height = 260, title = "Running P&L today (after charges)" }) {
  const ref = useRef(null);
  const rows = (trades || [])
    .filter((t) => num(t.closed_ts) != null && num(t.realized_pnl_inr) != null)
    .sort((a, b) => a.closed_ts - b.closed_ts)
    // one fill booked under two strategies (same leg, same times) counts once, like the day total
    .filter((t, i, all) => all.findIndex((o) => o.underlying === t.underlying && o.side === t.side && o.opened_ts === t.opened_ts && o.closed_ts === t.closed_ts) === i);

  useEffect(() => {
    if (!ref.current || rows.length === 0) return undefined;
    const chart = createChart(ref.current, {
      height,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#9aa7b4" },
      grid: { vertLines: { color: "rgba(42,51,61,.5)" }, horzLines: { color: "rgba(42,51,61,.5)" } },
      rightPriceScale: { borderColor: "#2a333d" },
      timeScale: { borderColor: "#2a333d", timeVisible: true, secondsVisible: false },
      localization: { priceFormatter: (p) => `${p < 0 ? "−" : ""}₹${Math.abs(Math.round(p)).toLocaleString("en-IN")}` },
      handleScroll: false,
      handleScale: false,
    });
    const series = chart.addBaselineSeries({
      baseValue: { type: "price", price: 0 },
      topLineColor: "#3ecf8e",
      bottomLineColor: "#ff6b6b",
      topFillColor1: "rgba(62,207,142,.25)",
      bottomFillColor2: "rgba(255,107,107,.25)",
      lineWidth: 2,
    });
    const pts = new Map();
    const first = Math.min(...rows.map((t) => num(t.opened_ts) ?? t.closed_ts));
    pts.set(first + IST_OFFSET - 60, 0);
    let run = 0;
    for (const t of rows) {
      run += Number(t.realized_pnl_inr);
      pts.set(Number(t.closed_ts) + IST_OFFSET, run);
    }
    const data = [...pts.entries()].sort((a, b) => a[0] - b[0]).map(([time, value]) => ({ time, value }));
    series.setData(data);
    const markers = [];
    for (const t of rows) {
      const label = `${t.underlying || ""} ${t.side || ""}`.trim();
      if (num(t.opened_ts) != null) {
        // snap entry to the nearest series point at or before it
        const at = Number(t.opened_ts) + IST_OFFSET;
        const snap = data.filter((p) => p.time <= at).pop() || data[0];
        markers.push({ time: snap.time, position: "belowBar", color: "#5aa9ff", shape: "arrowUp", text: `in ${label}` });
      }
      const win = Number(t.realized_pnl_inr) >= 0;
      markers.push({ time: Number(t.closed_ts) + IST_OFFSET, position: win ? "aboveBar" : "belowBar", color: win ? "#3ecf8e" : "#ff6b6b", shape: "circle", text: "out" });
    }
    const seen = new Set();
    series.setMarkers(markers.sort((a, b) => a.time - b.time).filter((m) => { const k = `${m.time}|${m.text}`; if (seen.has(k)) return false; seen.add(k); return true; }));
    chart.timeScale().fitContent();
    const ro = new ResizeObserver(() => chart.applyOptions({ width: ref.current?.clientWidth || 600 }));
    ro.observe(ref.current);
    return () => { ro.disconnect(); chart.remove(); };
  }, [JSON.stringify(rows.map((t) => [t.trade_id, t.closed_ts, t.realized_pnl_inr])), height]);

  return (
    <section className="card" data-testid="pnl-chart">
      <header className="card__head"><h2>{title}</h2><span className="muted small">blue ▲ = entry · dot = exit</span></header>
      {rows.length ? <div ref={ref} className="pnl-chart" /> : <p className="muted">No closed trades yet today.</p>}
    </section>
  );
}
