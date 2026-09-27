import { useMemo, useState } from "react";
import { AccountPanel } from "./components/AccountPanel.jsx";
import { AlertBar } from "./components/AlertBar.jsx";
import { AppNav } from "./components/AppNav.jsx";
import { CurrentTrade, HumanManage } from "./components/CurrentTrade.jsx";
import { DecisionTrace } from "./components/DecisionTrace.jsx";
import { Disclaimer } from "./components/Disclaimer.jsx";
import { Header, OfflineBanner } from "./components/Header.jsx";
import { IstMarketClock } from "./components/IstMarketClock.jsx";
import { MarketPanel } from "./components/MarketPanel.jsx";
import { SpillLedger } from "./components/SpillLedger.jsx";
import { TradeHistory } from "./components/TradeHistory.jsx";
import { useFeed } from "./lib/feed.js";
import { boardClock, boardSource, derivePaperBoard, holdReason, postHumanOverride } from "./lib/paperBoard.js";

export function InternalDesk() {
  const { snap, conn, latencyMs } = useFeed();
  const [busy, setBusy] = useState(false);
  const [humanMsg, setHumanMsg] = useState("");
  const [picked, setPicked] = useState(null);

  const board = snap?.board || null;
  const d = useMemo(() => derivePaperBoard(board, null), [board]);
  const clock = boardClock(board);
  const offline = Boolean(snap?.offline);
  const current = d?.current;
  const indexNow = current ? d?.regimes?.[current.underlying]?.itm_bin?.index ?? null : null;
  const fresh = picked && [...(d?.uniqueOpen || []), ...(d?.uniqueClosed || [])].find((t) => t.trade_id === picked.trade_id);
  const traceRow = fresh || picked || current || d?.uniqueClosed?.[0];
  const traceId = traceRow?.trade_id || null;
  const today = (snap?.days || []).find((x) => x.day === (board?.session_ist_date || clock.ist?.slice(0, 10)));

  async function human(body, okMsg) {
    setHumanMsg("");
    setBusy(true);
    try {
      const res = await postHumanOverride(body);
      setHumanMsg(res?.ok === false ? res.note || res.error || "Refused" : okMsg);
    } catch (err) {
      setHumanMsg(err.message || String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell shell--internal">
      <AppNav current="/desk" />
      <Header
        title="Desk"
        kicker="Revalidate the ticket"
        sub="Live ticket, path, decision trace and every trade. PAPER only."
        sourceLabel={boardSource(board, clock, offline)}
      />
      <div className="desk-refresh">
        <p className="desk-sub" title={clock.writtenIst ? `Board written ${clock.writtenIst}` : undefined}>
          Tape as of {clock.label}
          {offline ? " · static mock (API offline)" : clock.replay ? " · replay of a past session" : ""} · {conn === "live" ? "live push" : conn}
          {latencyMs != null ? ` · update ${latencyMs} ms` : ""}
        </p>
        <IstMarketClock />
      </div>
      {offline ? <OfflineBanner /> : null}
      <AlertBar alerts={snap?.alerts} conn={conn} />

      {!d ? (
        <p className="muted">Loading desk…</p>
      ) : (
        <div className="grid">
          <div className="span-8">
            <CurrentTrade t={current} last={d.uniqueClosed[0]} clock={clock} hold={current ? null : holdReason(board, snap?.founder_book, snap?.risk_halt)} indexNow={indexNow}>
              {current ? (
                <>
                  <HumanManage
                    current={current}
                    busy={busy}
                    onCancel={() =>
                      human(
                        { action: "CANCEL", trade_id: current.trade_id, underlying: current.underlying, side: current.side },
                        "Human cancel sent for the unfilled paper limit. No live broker order.",
                      )
                    }
                    onSetLevels={({ target, stop }) =>
                      human(
                        {
                          action: "SET_LEVELS",
                          trade_id: current.trade_id,
                          underlying: current.underlying,
                          side: current.side,
                          target,
                          stop,
                        },
                        `Paper target ${Number(target).toFixed(2)} / stop ${Number(stop).toFixed(2)} queued. Applies on next paper tick. No flatten. No live broker order.`,
                      )
                    }
                  />
                  {humanMsg ? <p className="muted">{humanMsg}</p> : null}
                </>
              ) : null}
            </CurrentTrade>
          </div>
          <div className="span-4 stack">
            <AccountPanel account={snap?.account} today={today} founderBook={snap?.founder_book} />
            <MarketPanel regimes={d.regimes} />
          </div>
          <div className="span-12">
            <DecisionTrace
              refreshKey={traceRow?.last_updated_ts}
              tradeId={traceId}
              label={traceRow ? `${traceRow.underlying} ${traceRow.side} ${traceRow.atm_strike ?? ""} · ${String(traceRow.opened_ist || "").slice(11, 19)}` : null}
            />
          </div>
          <section className="panel span-12">
            <h2>Trade history</h2>
            <TradeHistory
              rows={[...(d.uniqueOpen || []), ...d.uniqueClosed]}
              days={snap?.days}
              liveDay={board?.session_ist_date}
              clock={clock}
              onSelect={setPicked}
              selectedId={traceId}
            />
          </section>
          <div className="span-12">
            <SpillLedger exam={snap?.exam} />
          </div>
        </div>
      )}
      <Disclaimer />
    </div>
  );
}
