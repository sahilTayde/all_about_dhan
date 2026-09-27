import { useCallback, useEffect, useState } from "react";
import { confirmToken, describeArgs, fetchControls, parseWindows, sendControl, windowsText } from "../lib/founderControls.js";

const POLL_MS = 5000;
const KIND_LABEL = {
  START: "Start trading",
  STOP: "Stop trading",
  PAUSE: "Pause entries",
  BLOCK_WINDOWS: "Blocked windows",
  CUT_LOSS: "Cut loss now",
  GO_T2: "Go for T2",
  SET_LOTS: "Lots",
  KILL: "Kill switch",
  REARM: "Re-arm",
  INDEX: "Index",
  MIN_CAPITAL: "Min capital",
  ADD_FUNDS: "Add funds",
};

function istTime(iso) {
  return iso ? String(iso).replace("T", " ").slice(5, 19) : "—";
}

function inrText(n) {
  return n == null ? "—" : `₹${Number(n).toLocaleString("en-IN")}`;
}

/** Founder emergency controls + command history. Human commands outrank the algo. PAPER only. */
export function FounderControls({ compact = false }) {
  const [data, setData] = useState(null);
  const [offline, setOffline] = useState(null);
  const [reason, setReason] = useState("");
  const [actor, setActor] = useState(() => localStorage.getItem("founderActor") || "founder");
  const [minutes, setMinutes] = useState("15");
  const [wins, setWins] = useState("");
  const [lots, setLots] = useState("");
  const [minCap, setMinCap] = useState("");
  const [funds, setFunds] = useState("");
  const [newIndex, setNewIndex] = useState("");
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState(null);

  const load = useCallback(async (signal) => {
    try {
      const j = await fetchControls({ signal });
      setData(j);
      setOffline(null);
      return j;
    } catch (err) {
      if (err.name !== "AbortError") setOffline(err.message || String(err));
      return null;
    }
  }, []);

  useEffect(() => {
    const ac = new AbortController();
    load(ac.signal).then((j) => {
      if (j) setWins(windowsText(j.state?.blocked_windows));
    });
    const id = setInterval(() => load(ac.signal), POLL_MS);
    return () => {
      ac.abort();
      clearInterval(id);
    };
  }, [load]);

  useEffect(() => {
    localStorage.setItem("founderActor", actor);
  }, [actor]);

  async function run(path, label, args = {}, { confirmKind, tradeId, emergency } = {}) {
    let why = reason.trim();
    if (emergency) {
      const typed = window.prompt(`${label}: reason (logged with your name)`, why || "emergency");
      if (typed == null) return;
      why = typed.trim() || "emergency";
    } else if (!why) {
      setMsg({ tone: "err", text: "Type a reason first. Every command is logged with who and why." });
      return;
    }
    setBusy(path + (tradeId || ""));
    setMsg(null);
    try {
      const body = { actor: actor.trim() || "founder", reason: why, ...args };
      if (confirmKind) body.confirm_token = await confirmToken(confirmKind, tradeId);
      const ack = await sendControl(path, body);
      setMsg({ tone: "ok", text: `${label}: recorded ${ack.ts_ist.slice(11, 19)} IST · pending until the engine's next cycle.` });
      if (!emergency) setReason("");
    } catch (err) {
      setMsg({ tone: "err", text: `${label}: ${err.message || err}` });
    } finally {
      setBusy("");
      load();
    }
  }

  function kill() {
    if (!window.confirm("KILL SWITCH: flatten every open paper position at market and block all new entries until you re-arm. Continue?")) return;
    run("kill", "Kill switch", {}, { confirmKind: "KILL", emergency: true });
  }

  function rearm() {
    if (!window.confirm("Re-arm: allow new entries again (other blocks still apply). Continue?")) return;
    run("rearm", "Re-arm", {}, { confirmKind: "REARM", emergency: true });
  }

  function cutLoss(t) {
    if (!window.confirm(`Cut loss now: exit ${t.underlying} ${t.side} ${t.atm_strike ?? ""} at market?`)) return;
    run("cut-loss", "Cut loss", { trade_id: t.trade_id }, { confirmKind: "CUT_LOSS", tradeId: t.trade_id, emergency: true });
  }

  function saveWindows() {
    try {
      run("blocked-windows", "Blocked windows", { windows: parseWindows(wins) });
    } catch (err) {
      setMsg({ tone: "err", text: err.message });
    }
  }

  const st = data?.state || {};
  const known = data?.limits?.known_indices || ["NIFTY", "BANKNIFTY", "SENSEX"];
  const opens = data?.open_trades || [];
  const commands = data?.commands || [];
  const blocked = st.entries_blocked_reason;
  const b = (key) => Boolean(busy) && busy.startsWith(key);

  return (
    <section className={`panel founder-controls${compact ? " founder-controls--compact" : ""}`} aria-label="Founder controls">
      <div className="panel__head">
        <h2>Founder controls</h2>
        <span className="muted small">PAPER · human commands outrank the algo</span>
      </div>

      {offline ? <p className="desk-error">Controls API offline: {offline}. Nothing was sent.</p> : null}
      {data?.problems?.length ? (
        <p className="desk-error" role="alert">
          Command log has unreadable lines — new entries are blocked, exits still run. {data.problems.join("; ")}
        </p>
      ) : null}

      <div className="fc-status" aria-live="polite">
        <span className={`fc-pill ${st.killed ? "is-bad" : "is-ok"}`}>{st.killed ? `KILLED ${istTime(st.killed_at_ist)}` : "Kill switch armed"}</span>
        <span className={`fc-pill ${st.running === false ? "is-bad" : "is-ok"}`}>{st.running === false ? "Trading STOPPED" : "Trading ON"}</span>
        {st.paused_until_ist ? <span className="fc-pill is-warn">Paused until {st.paused_until_ist.slice(11, 16)}</span> : null}
        <span className={`fc-pill ${blocked ? "is-warn" : "is-ok"}`}>{blocked ? `New entries blocked: ${blocked}` : "New entries allowed"}</span>
        {st.lots != null ? <span className="fc-pill is-warn">Lots {st.lots}</span> : null}
      </div>

      <div className="fc-row">
        <label className="fc-field fc-grow">
          <span>Reason (required, logged)</span>
          <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="why you are doing this" maxLength={500} />
        </label>
        <label className="fc-field">
          <span>Who</span>
          <input value={actor} onChange={(e) => setActor(e.target.value)} maxLength={64} size={10} />
        </label>
      </div>

      <div className="fc-grid">
        <div className="fc-box">
          <h3>Trading</h3>
          <div className="fc-btns">
            <button type="button" className="fc-btn fc-btn--go" disabled={b("start") || st.running !== false} onClick={() => run("start", "Start trading")}>
              Start
            </button>
            <button type="button" className="fc-btn fc-btn--stop" disabled={b("stop") || st.running === false} onClick={() => run("stop", "Stop trading")}>
              Stop
            </button>
          </div>
          <div className="fc-inline">
            <label className="fc-field">
              <span>Pause new entries (min)</span>
              <input type="number" min="1" max="1440" value={minutes} onChange={(e) => setMinutes(e.target.value)} />
            </label>
            <button type="button" className="fc-btn" disabled={b("pause")} onClick={() => run("pause", "Pause", { minutes: Number(minutes) })}>
              Pause
            </button>
            <button type="button" className="fc-btn" disabled={b("pause") || !st.paused_until_ist} onClick={() => run("pause", "Resume", { minutes: 0 })}>
              Resume
            </button>
          </div>
        </div>

        <div className="fc-box">
          <h3>Blocked windows (IST)</h3>
          <div className="fc-inline">
            <label className="fc-field fc-grow">
              <span>No new entries in</span>
              <input value={wins} onChange={(e) => setWins(e.target.value)} placeholder="09:15-09:30, 14:45-15:30" />
            </label>
            <button type="button" className="fc-btn" disabled={b("blocked-windows")} onClick={saveWindows}>
              Save
            </button>
          </div>
          <p className="muted small">Now: {windowsText(st.blocked_windows) || "none"}. Empty + Save clears.</p>
        </div>

        <div className="fc-box">
          <h3>Size</h3>
          <div className="fc-inline">
            <label className="fc-field">
              <span>Lots for next fills (max {data?.limits?.max_lots ?? "—"})</span>
              <input type="number" min="1" max={data?.limits?.max_lots || undefined} value={lots} onChange={(e) => setLots(e.target.value)} />
            </label>
            <button type="button" className="fc-btn" disabled={b("lots") || !lots} onClick={() => run("lots", "Lots", { lots: Number(lots) })}>
              Set
            </button>
            <button type="button" className="fc-btn" disabled={b("lots") || st.lots == null} onClick={() => run("lots", "Lots", { lots: null })}>
              Clear
            </button>
          </div>
        </div>

        <div className="fc-box">
          <h3>Indices</h3>
          <div className="fc-btns fc-wrap">
            {known.map((n) => {
              const on = st.index_enabled?.[n];
              return (
                <button
                  key={n}
                  type="button"
                  className={`fc-chip ${on === false ? "is-off" : on === true ? "is-on" : ""}`}
                  aria-pressed={on === true}
                  disabled={b("index")}
                  title={on == null ? "No founder override: the START/STOP desk decides" : "Founder override"}
                  onClick={() => run("index", `${n} ${on === false ? "enable" : "disable"}`, { underlying: n, enabled: on === false })}
                >
                  {n} {on === false ? "OFF" : on === true ? "ON" : "auto"}
                </button>
              );
            })}
          </div>
          <div className="fc-inline">
            <label className="fc-field">
              <span>Add index</span>
              <input value={newIndex} onChange={(e) => setNewIndex(e.target.value.toUpperCase())} placeholder="FINNIFTY" size={10} />
            </label>
            <button type="button" className="fc-btn" disabled={b("index") || !newIndex} onClick={() => run("index", `${newIndex} enable`, { underlying: newIndex, enabled: true })}>
              Enable
            </button>
          </div>
        </div>

        <div className="fc-box">
          <h3>Capital</h3>
          <p className="muted small">
            Desk {inrText(data?.desk_capital_inr)} · added {inrText(st.funds_added_inr)} · min to trade {inrText(st.min_capital_inr)}
          </p>
          <div className="fc-inline">
            <label className="fc-field">
              <span>Min capital ₹</span>
              <input type="number" min="0" value={minCap} onChange={(e) => setMinCap(e.target.value)} />
            </label>
            <button type="button" className="fc-btn" disabled={b("min-capital") || minCap === ""} onClick={() => run("min-capital", "Min capital", { amount_inr: Number(minCap) })}>
              Save
            </button>
            <button type="button" className="fc-btn" disabled={b("min-capital") || st.min_capital_inr == null} onClick={() => run("min-capital", "Min capital", { amount_inr: null })}>
              Clear
            </button>
          </div>
          <div className="fc-inline">
            <label className="fc-field">
              <span>Add funds ₹</span>
              <input type="number" min="1" value={funds} onChange={(e) => setFunds(e.target.value)} />
            </label>
            <button type="button" className="fc-btn" disabled={b("add-funds") || !funds} onClick={() => run("add-funds", "Add funds", { amount_inr: Number(funds) })}>
              Add
            </button>
          </div>
        </div>

        <div className="fc-box fc-box--danger">
          <h3>Emergency</h3>
          <div className="fc-btns">
            <button type="button" className="fc-btn fc-btn--kill" disabled={b("kill")} onClick={kill}>
              KILL SWITCH
            </button>
            <button type="button" className="fc-btn" disabled={b("rearm") || !st.killed} onClick={rearm}>
              Re-arm
            </button>
          </div>
          <p className="muted small">Kill flattens every open paper position and blocks entries until re-armed. Start does not re-arm.</p>
        </div>
      </div>

      <div className="fc-box">
        <h3>Open positions</h3>
        {!opens.length ? (
          <p className="muted small">No open paper ticket on the latest board{data?.board_as_of_ist ? ` (${istTime(data.board_as_of_ist)})` : ""}.</p>
        ) : (
          <ul className="fc-opens">
            {opens.map((t) => (
              <li key={t.trade_id}>
                <span className="fc-open-name">
                  {t.underlying} {t.side} {t.atm_strike ?? ""} · {t.lots} lots · entry {t.entry ?? "—"} · now {t.last_ltp ?? "—"}
                  {t.founder_t2 ? " · going for T2" : ""}
                </span>
                <span className="fc-btns">
                  <button type="button" className="fc-btn fc-btn--stop" disabled={b("cut-loss" + t.trade_id)} onClick={() => cutLoss(t)}>
                    Cut loss now
                  </button>
                  <button type="button" className="fc-btn" disabled={b("go-t2" + t.trade_id) || t.founder_t2} onClick={() => run("go-t2", "Go for T2", { trade_id: t.trade_id }, { tradeId: t.trade_id })}>
                    Go for T2
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {msg ? (
        <p className={msg.tone === "err" ? "desk-error" : "muted"} role="status">
          {msg.text}
        </p>
      ) : null}

      <div className="fc-history">
        <h3>Command history</h3>
        {!commands.length ? (
          <p className="muted small">No founder commands yet.</p>
        ) : (
          <div className="fc-table-wrap">
            <table className="fc-table">
              <thead>
                <tr>
                  <th>When (IST)</th>
                  <th>Command</th>
                  <th>Detail</th>
                  <th>Who · why</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {commands.slice(0, compact ? 8 : 50).map((c) => (
                  <tr key={c.id}>
                    <td className="mono">{istTime(c.ts_ist)}</td>
                    <td>{KIND_LABEL[c.kind] || c.kind}</td>
                    <td className="mono small">{describeArgs(c.kind, c.args)}</td>
                    <td className="small">
                      {c.actor} · {c.reason}
                    </td>
                    <td>
                      <span className={`fc-status-badge is-${c.status}`}>{c.status}</span>
                      {c.status_reason ? <span className="small muted"> {c.status_reason}</span> : null}
                      {c.applied_ist ? <span className="small muted"> at {c.applied_ist.slice(11, 19)}</span> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
