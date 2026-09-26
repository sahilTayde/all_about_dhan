import { useEffect, useMemo, useRef, useState } from "react";
import { ColorType, createChart } from "lightweight-charts";
import { inr, lossByStage, modelScores, moneyClass, periodBuckets } from "../lib/paperBoard.js";

const UP = "#3dcc8c";
const DOWN = "#e06b74";
const IST_S = 19800; // lightweight-charts renders UTC; shift epoch seconds so the axis reads IST

const BASE = {
  autoSize: true,
  layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#8b97a5", fontSize: 11 },
  grid: { vertLines: { color: "rgba(42,51,61,0.45)" }, horzLines: { color: "rgba(42,51,61,0.45)" } },
  rightPriceScale: { borderColor: "#2a333d" },
  leftPriceScale: { borderColor: "#2a333d" },
  timeScale: { borderColor: "#2a333d" },
  handleScroll: false,
  handleScale: false,
};

/** series: [{ kind: "line" | "histogram", data, color, scale?: "left" }] */
function TimeChart({ series, height = 180, timeVisible = false, label }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return undefined;
    const chart = createChart(ref.current, {
      ...BASE,
      leftPriceScale: { ...BASE.leftPriceScale, visible: series.some((s) => s.scale === "left") },
      timeScale: { ...BASE.timeScale, timeVisible },
    });
    for (const s of series) {
      const opts = {
        color: s.color,
        priceScaleId: s.scale || "right",
        priceLineVisible: false,
        lastValueVisible: true,
        priceFormat: { type: "price", precision: 0, minMove: 1 },
      };
      const api = s.kind === "histogram" ? chart.addHistogramSeries(opts) : chart.addLineSeries({ ...opts, lineWidth: 2 });
      api.setData(s.data);
    }
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [series, timeVisible]);
  return <div ref={ref} className="chart-box" style={{ height }} role="img" aria-label={label} />;
}

function Empty({ children = "No recorded days yet." }) {
  return <p className="muted chart-empty">{children}</p>;
}

function Tabs({ value, onChange, options }) {
  return (
    <div className="seg" role="tablist">
      {options.map(([v, l]) => (
        <button key={v} type="button" role="tab" aria-selected={value === v} className={value === v ? "is-on" : ""} onClick={() => onChange(v)}>
          {l}
        </button>
      ))}
    </div>
  );
}

export function CumulativeChart({ days, todayTrades }) {
  const byDay = useMemo(() => {
    let run = 0;
    return periodBuckets(days, "D").map((b) => ({ time: b.time, value: Math.round((run += b.net)) }));
  }, [days]);
  const intraday = useMemo(() => {
    let run = 0;
    const seen = new Set();
    return [...(todayTrades || [])]
      .filter((t) => t.realized_pnl_inr != null && (t.closed_ts || t.last_updated_ts))
      .map((t) => ({ ts: Number(t.closed_ts || t.last_updated_ts), v: Number(t.realized_pnl_inr) }))
      .sort((a, b) => a.ts - b.ts)
      .filter((p) => !seen.has(p.ts) && seen.add(p.ts))
      .map((p) => ({ time: p.ts + IST_S, value: Math.round((run += p.v)) }));
  }, [todayTrades]);
  const [mode, setMode] = useState(null);
  const pick = mode || (byDay.length > 1 ? "D" : "I");
  const data = pick === "D" ? byDay : intraday;
  const last = data.at(-1)?.value;
  const series = useMemo(() => [{ kind: "line", data, color: (last ?? 0) >= 0 ? UP : DOWN }], [data, last]);
  return (
    <section className="panel chart-panel">
      <div className="panel__head">
        <h2>Cumulative net P&L</h2>
        <Tabs value={pick} onChange={setMode} options={[["I", "Today"], ["D", "All days"]]} />
      </div>
      <p className={`chart-headline ${moneyClass(last)}`}>{inr(last)}</p>
      {data.length ? <TimeChart series={series} timeVisible={pick === "I"} label="Cumulative net P&L" /> : <Empty />}
    </section>
  );
}

export function PeriodChart({ days }) {
  const [period, setPeriod] = useState("D");
  const buckets = useMemo(() => periodBuckets(days, period), [days, period]);
  const series = useMemo(
    () => [
      { kind: "histogram", data: buckets.map((b) => ({ time: b.time, value: Math.round(b.net), color: b.net >= 0 ? UP : DOWN })) },
      { kind: "line", scale: "left", color: "#c9a227", data: buckets.filter((b) => b.wr != null).map((b) => ({ time: b.time, value: b.wr })) },
    ],
    [buckets],
  );
  const last = buckets.at(-1);
  return (
    <section className="panel chart-panel">
      <div className="panel__head">
        <h2>P&L and win rate</h2>
        <Tabs value={period} onChange={setPeriod} options={[["D", "Daily"], ["W", "Weekly"], ["M", "Monthly"]]} />
      </div>
      <p className="chart-legend">
        <span className="lg lg--bar">net ₹ (right)</span> <span className="lg lg--line">win % (left)</span>
        {last ? (
          <span className="muted">
            latest {last.time}: <b className={moneyClass(last.net)}>{inr(last.net)}</b> · {last.wr ?? "—"}% of {last.n}
          </span>
        ) : null}
      </p>
      {buckets.length ? <TimeChart series={series} label="Net P&L bars and win rate line per period" /> : <Empty />}
    </section>
  );
}

export function TradesPerDay({ days }) {
  const series = useMemo(
    () => [{ kind: "histogram", color: "#5b9cff", data: periodBuckets(days, "D").map((b) => ({ time: b.time, value: b.n })) }],
    [days],
  );
  return (
    <section className="panel chart-panel">
      <div className="panel__head">
        <h2>Trades per day</h2>
        <span className="muted small">unique fills</span>
      </div>
      {days?.length ? <TimeChart series={series} height={150} label="Trades per day" /> : <Empty />}
    </section>
  );
}

function Spark({ values }) {
  const pts = values.map((v, i) => (v == null ? null : [i, v])).filter(Boolean);
  if (pts.length < 2) return <span className="muted small">—</span>;
  const w = 80;
  const h = 22;
  const x = (i) => (i / (values.length - 1)) * w;
  const y = (v) => h - (v / 100) * h;
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} width={w} height={h} aria-hidden="true">
      <polyline points={pts.map(([i, v]) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ")} />
    </svg>
  );
}

export function ModelScores({ days }) {
  const rows = useMemo(() => modelScores(days), [days]);
  return (
    <section className="panel">
      <div className="panel__head">
        <h2>Models · win rate and trend</h2>
        <span className="muted small">per book, all recorded days · not a promote</span>
      </div>
      {rows.length ? (
        <div className="table-scroll">
          <table className="book-table compact-table">
            <thead>
              <tr>
                <th>Model / book</th>
                <th className="num">Fills</th>
                <th className="num">Win %</th>
                <th>Win % bar</th>
                <th className="num">Net ₹</th>
                <th>Trend (win % by day)</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((m) => (
                <tr key={m.book}>
                  <td>{m.book}</td>
                  <td className="num">{m.n}</td>
                  <td className="num">{m.wr == null ? "—" : `${m.wr}%`}</td>
                  <td>
                    <span className="meter">
                      <i style={{ width: `${m.wr ?? 0}%` }} />
                    </span>
                  </td>
                  <td className={`num ${moneyClass(m.net)}`}>{inr(m.net)}</td>
                  <td>
                    <Spark values={m.trend} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty />
      )}
    </section>
  );
}

export function LossByStage({ days, exam }) {
  const rows = useMemo(() => lossByStage(days), [days]);
  const rooms = useMemo(() => {
    const map = new Map();
    for (const d of exam?.days || []) {
      for (const sp of d.spills || []) {
        if (sp.pnl_inr == null) continue;
        map.set(sp.room || "?", (map.get(sp.room || "?") || 0) + Number(sp.pnl_inr));
      }
    }
    return [...map.entries()].filter(([, v]) => v < 0).sort((a, b) => a[1] - b[1]);
  }, [exam]);
  const worst = Math.min(...rows.map((r) => r.net), ...rooms.map(([, v]) => v), -1);
  return (
    <section className="panel">
      <div className="panel__head">
        <h2>Loss by stage</h2>
        <span className="muted small">which step loses money</span>
      </div>
      {rows.length ? (
        <ul className="stage-bars">
          {rows.map((r) => (
            <li key={r.stage}>
              <span>{r.stage}</span>
              <span className="stage-bars__bar">
                <i style={{ width: `${(r.net / worst) * 100}%` }} />
              </span>
              <b className="is-down">{inr(r.net)}</b>
              <em className="muted small">{r.n == null ? "" : `${r.n} trades`}</em>
            </li>
          ))}
        </ul>
      ) : (
        <Empty>No losing exits recorded.</Empty>
      )}
      {rooms.length ? (
        <>
          <h3>Honesty exam · spill by room</h3>
          <ul className="stage-bars">
            {rooms.map(([room, v]) => (
              <li key={room}>
                <span>{room}</span>
                <span className="stage-bars__bar">
                  <i style={{ width: `${(v / worst) * 100}%` }} />
                </span>
                <b className="is-down">{inr(v)}</b>
                <em />
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
