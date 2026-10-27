import { useEffect, useRef } from "react";
import { ColorType, CrosshairMode, LineStyle, createChart } from "lightweight-charts";
import { addMin, exitRule, hhmm, num, strikeOf } from "../lib/deskModel.js";
import { toCandles } from "../lib/ltpTape.js";

const IST = 19800;
const C = { up: "#26c281", down: "#f0524f", grid: "rgba(255,255,255,.05)", text: "#8b95a1", entry: "#4c9aff", exit: "#e8b04b" };

function hmToTs(t, hm) {
  // HH:MM IST on the trade's day -> unix seconds
  const m = String(hm || "").match(/^(\d{2}):(\d{2})$/);
  if (!m || t?.opened_ts == null) return null;
  const day0 = Math.floor((Number(t.opened_ts) + IST) / 86400) * 86400 - IST;
  return day0 + Number(m[1]) * 3600 + Number(m[2]) * 60;
}

/** Big premium chart for one trade: 1-min candles from real prints, entry and exit lines and markers. */
export function PremiumChart({ trade, prints, height = 380 }) {
  const ref = useRef(null);
  const candles = toCandles(prints);
  const key = `${trade?.trade_id}|${candles.length}|${candles.at(-1)?.close}|${trade?.exit}`;

  useEffect(() => {
    if (!ref.current || !trade || candles.length === 0) return undefined;
    const chart = createChart(ref.current, {
      height,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: C.text, fontSize: 11 },
      grid: { vertLines: { color: C.grid }, horzLines: { color: C.grid } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "rgba(255,255,255,.08)", scaleMargins: { top: 0.15, bottom: 0.15 } },
      timeScale: { borderColor: "rgba(255,255,255,.08)", timeVisible: true, secondsVisible: false, rightOffset: 4 },
    });
    const s = chart.addCandlestickSeries({ upColor: C.up, downColor: C.down, borderVisible: false, wickUpColor: C.up, wickDownColor: C.down });
    s.setData(candles.map((c) => ({ ...c, time: c.time + IST })));
    const entry = num(trade.entry);
    if (entry != null) s.createPriceLine({ price: entry, color: C.entry, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "Buy" });
    if (num(trade.exit) != null) s.createPriceLine({ price: num(trade.exit), color: C.exit, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "Exit" });
    if (num(trade.stop) != null) s.createPriceLine({ price: num(trade.stop), color: C.down, lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: true, title: "Stop" });
    if (num(trade.target) != null) s.createPriceLine({ price: num(trade.target), color: C.up, lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: true, title: "Target" });
    const markers = [];
    const snap = (ts) => Math.floor(ts / 60) * 60 + IST;
    if (trade.opened_ts != null) markers.push({ time: snap(trade.opened_ts), position: "belowBar", color: C.entry, shape: "arrowUp", text: `Buy ${entry ?? ""}` });
    if (trade.closed_ts != null) markers.push({ time: snap(trade.closed_ts), position: "aboveBar", color: C.exit, shape: "arrowDown", text: `Exit ${num(trade.exit) ?? ""}` });
    const valid = new Set(candles.map((c) => c.time + IST));
    s.setMarkers(markers.filter((m) => valid.has(m.time)).sort((a, b) => a.time - b.time));
    const rule = exitRule(trade);
    const exitTs = rule.kind === "time" ? hmToTs(trade, rule.at) : null;
    const exitTime = exitTs ? Math.floor(exitTs / 60) * 60 + IST : null;
    const lastTime = candles.length ? candles[candles.length - 1].time + IST : null;
    // whitespace point so the time axis reaches the planned exit minute; only if it is
    // after the last candle (a late exit is in the past and update() throws on older times)
    if (exitTime && trade.closed_ts == null && (lastTime == null || exitTime > lastTime)) {
      s.update({ time: exitTime });
    }
    chart.timeScale().fitContent();
    const ro = new ResizeObserver(() => chart.applyOptions({ width: ref.current?.clientWidth || 600 }));
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [key, height]);

  if (!trade) return <div className="empty">No trade to chart yet today.</div>;
  const rule = exitRule(trade);
  return (
    <div className="pchart">
      <div className="pchart__legend">
        <span className="sym">{trade.underlying} {strikeOf(trade) ?? "—"} {trade.side}</span>
        <span className="muted">Premium · 1-min</span>
        <span><i className="sw sw--entry" /> Buy {num(trade.entry) ?? "—"} at {hhmm(trade.opened_ist) || trade.entry_min || "—"}</span>
        {trade.closed_ts != null ? <span><i className="sw sw--exit" /> Exit {num(trade.exit) ?? "—"} at {hhmm(trade.closed_ist) || "—"}</span> : <span><i className="sw sw--exit" /> {rule.text}</span>}
      </div>
      {candles.length ? <div ref={ref} className="pchart__canvas" style={{ height }} /> : <div className="empty" style={{ height }}>No prices recorded for this trade yet.</div>}
      <p className="fine">Built only from real prints: the fill prices plus every live price the feed sent while this page was open. The API has no candle history, so gaps stay gaps.</p>
    </div>
  );
}

export { addMin };
