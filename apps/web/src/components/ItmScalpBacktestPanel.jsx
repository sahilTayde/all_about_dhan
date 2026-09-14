import { useEffect, useState } from "react";

const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

async function fetchItmScalp() {
  const url = API_URL
    ? `${API_URL}/paper/backtests/itm-scalp`
    : "/mock/itm_scalp_backtest.json";
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Could not load ITM scalp backtest (${res.status})`);
  return res.json();
}

function inr(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  const sign = v > 0 ? "+" : "";
  return `${sign}₹${v.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function pts(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(2)} pts`;
}

function tsIst(ts) {
  if (!ts) return "—";
  return new Date(Number(ts) * 1000).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function LegBlock({ title, diamondClass, leg }) {
  if (!leg) return null;
  const s = leg.summary || {};
  const pnlClass =
    Number(s.gross_pnl_inr) > 0
      ? "itm-scalp-pnl itm-scalp-pnl--win"
      : Number(s.gross_pnl_inr) < 0
        ? "itm-scalp-pnl itm-scalp-pnl--loss"
        : "itm-scalp-pnl";
  const best = leg.sltp_best;

  return (
    <div className={`itm-scalp-leg ${diamondClass}`}>
      <h3>
        <span className="itm-scalp-diamond" aria-hidden="true" />
        {title}
      </h3>
      {!leg.ok ? (
        <p className="error-banner">{leg.reason || "DATA_INSUFFICIENT"}</p>
      ) : (
        <>
          <p className="itm-scalp-contract">{leg.contract?.display_name}</p>
          <div className="itm-scalp-stats">
            <div>
              <span className="muted">Gross P/L (1 lot)</span>
              <strong className={pnlClass}>{inr(s.gross_pnl_inr)}</strong>
              <span className="muted">{pts(s.gross_points)}</span>
            </div>
            <div>
              <span className="muted">After cost</span>
              <strong className={pnlClass}>{inr(s.after_cost_pnl_inr)}</strong>
            </div>
            <div>
              <span className="muted">Trades</span>
              <strong>
                {s.trade_count ?? 0} · W{s.wins ?? 0} / L{s.losses ?? 0}
              </strong>
              <span className="muted">
                WR{" "}
                {s.win_rate == null
                  ? "—"
                  : `${(Number(s.win_rate) * 100).toFixed(0)}%`}
              </span>
            </div>
            <div>
              <span className="muted">Best SL/TP (grid)</span>
              <strong>
                {best
                  ? `${inr(best.after_cost_pnl_inr)} · SL ${
                      best.stop_loss_frac == null
                        ? "off"
                        : `${(best.stop_loss_frac * 100).toFixed(0)}%`
                    } / TP ${
                      best.target_frac == null
                        ? "off"
                        : `${(best.target_frac * 100).toFixed(0)}%`
                    }`
                  : "—"}
              </strong>
            </div>
          </div>
          <div className="itm-scalp-table-wrap">
            <table className="itm-scalp-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Entry</th>
                  <th>Exit</th>
                  <th>In</th>
                  <th>Out</th>
                  <th>Pts</th>
                  <th>₹</th>
                  <th>Why</th>
                </tr>
              </thead>
              <tbody>
                {(leg.trades || []).slice(0, 40).map((t, i) => (
                  <tr key={`${t.entry_ts}-${t.exit_ts}-${i}`}>
                    <td>{i + 1}</td>
                    <td>{tsIst(t.entry_ts)}</td>
                    <td>{tsIst(t.exit_ts)}</td>
                    <td>{Number(t.entry_px).toFixed(2)}</td>
                    <td>{Number(t.exit_px).toFixed(2)}</td>
                    <td className={t.points >= 0 ? "pos" : "neg"}>
                      {pts(t.points)}
                    </td>
                    <td className={t.pnl_inr >= 0 ? "pos" : "neg"}>
                      {inr(t.pnl_inr)}
                    </td>
                    <td>{t.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(leg.trades || []).length > 40 ? (
              <p className="muted">Showing first 40 of {leg.trades.length} trades.</p>
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}

export function ItmScalpBacktestPanel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchItmScalp()
      .then((row) => {
        if (!cancelled) setData(row);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <section className="panel itm-scalp-panel" aria-labelledby="itm-scalp-title">
        <h2 id="itm-scalp-title">ITM option scalp backtest</h2>
        <p className="error-banner">{error}</p>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="panel itm-scalp-panel" aria-labelledby="itm-scalp-title">
        <h2 id="itm-scalp-title">ITM option scalp backtest</h2>
        <p className="muted">Loading paper backtest…</p>
      </section>
    );
  }

  // Legacy single-leg shape fallback
  const legs = data.legs || null;
  const s = data.summary || {};
  const pe = legs?.PE_yellow;
  const ce = legs?.CE_blue;
  const diamonds = data.diamonds;

  return (
    <section className="panel itm-scalp-panel" aria-labelledby="itm-scalp-title">
      <h2 id="itm-scalp-title">ITM option scalp backtest</h2>
      <p className="muted">
        {data.mix_id || "MIX-ITM-OPT-SCALP"} · PAPER · {data.promotion || "NO_PROMOTE"} ·{" "}
        {data.verdict || "UNVALIDATED"}
      </p>
      {data.fix_note ? <p className="itm-scalp-fix">{data.fix_note}</p> : null}
      {data.params ? (
        <p className="itm-scalp-contract">
          MA={data.params.ma_mode} · POC={data.params.poc_mode} · fill={data.params.fill_mode} ·
          RSI≥{data.params.rsi_entry_th} exit&lt;{data.params.rsi_exit_th} · SL{" "}
          {data.params.stop_loss_frac == null
            ? "off"
            : `${(data.params.stop_loss_frac * 100).toFixed(0)}%`}{" "}
          / TP{" "}
          {data.params.target_frac == null
            ? "off"
            : `${(data.params.target_frac * 100).toFixed(0)}%`}
        </p>
      ) : null}

      {legs ? (
        <>
          <div className="itm-scalp-stats" role="group" aria-label="Combined P and L">
            <div>
              <span className="muted">Combined gross</span>
              <strong
                className={
                  Number(s.combined_gross_pnl_inr) >= 0
                    ? "itm-scalp-pnl itm-scalp-pnl--win"
                    : "itm-scalp-pnl itm-scalp-pnl--loss"
                }
              >
                {inr(s.combined_gross_pnl_inr)}
              </strong>
            </div>
            <div>
              <span className="muted">Combined after cost</span>
              <strong
                className={
                  Number(s.combined_after_cost_pnl_inr) >= 0
                    ? "itm-scalp-pnl itm-scalp-pnl--win"
                    : "itm-scalp-pnl itm-scalp-pnl--loss"
                }
              >
                {inr(s.combined_after_cost_pnl_inr)}
              </strong>
            </div>
            <div>
              <span className="muted">Yellow PE</span>
              <strong>{inr(s.pe_gross_pnl_inr)}</strong>
            </div>
            <div>
              <span className="muted">Blue CE</span>
              <strong>{inr(s.ce_gross_pnl_inr)}</strong>
            </div>
          </div>

          {diamonds ? (
            <p className="muted">
              Diamond session overlap (want low if inverse):{" "}
              <strong>{diamonds.overlap_count}</strong>
              {diamonds.overlap_sessions?.length
                ? ` → ${diamonds.overlap_sessions.join(", ")}`
                : " → none"}
            </p>
          ) : null}

          <div className="itm-scalp-legs">
            <LegBlock
              title="Yellow diamond · 23500 PUT"
              diamondClass="itm-scalp-leg--yellow"
              leg={pe}
            />
            <LegBlock
              title="Blue diamond · 23200 CALL"
              diamondClass="itm-scalp-leg--blue"
              leg={ce}
            />
          </div>
        </>
      ) : (
        <p className="muted">Legacy single-leg result — re-run itm-scalp for PE+CE.</p>
      )}

      <ul className="itm-scalp-honesty">
        {(data.api_honesty || []).concat(data.honesty || []).map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </section>
  );
}
