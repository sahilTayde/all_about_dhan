import { buildStrategyCards, todayTimeline } from "../../lib/strategyBoard.js";
import { DayPnlHero } from "../components/DayPnlHero.jsx";
import { HealthStrip } from "../components/HealthStrip.jsx";
import { Heatmap } from "../components/Heatmap.jsx";
import { MarketContext } from "../components/MarketContext.jsx";
import { OpenPositions } from "../components/OpenPositions.jsx";
import { TradePipeline } from "../components/TradePipeline.jsx";
import { TradeTimeline } from "../components/TradeTimeline.jsx";

export function TodayPage({ d, snap, clock, hold, indexing, onSelect, selectedId, health, conn }) {
  const sessionDay = snap?.board?.session_ist_date || clock?.ist?.slice(0, 10);
  const today = (snap?.days || []).find((x) => x.day === sessionDay);
  const net = today?.net ?? d?.headlineNet ?? d?.today?.net_pnl_inr ?? null;
  const tape = todayTimeline(d?.uniqueOpen, d?.uniqueClosed, sessionDay);
  return (
    <div className="desk-today" data-testid="desk-today">
      <div className="desk-today__pipe">
        <TradePipeline board={snap?.board} open={d?.uniqueOpen} closed={d?.uniqueClosed} />
      </div>
      <div className="desk-today__main">
        <DayPnlHero
          net={net}
          charges={today?.charges ?? d?.charges}
          gross={today?.gross ?? d?.uniqueGross}
          trades={today?.n ?? tape.length}
          clock={clock}
          indexing={false}
        />
        {indexing ? (
          <p className="needs-history muted small">
            <span className="indexing">Indexing history…</span> Multi-day account totals stay hidden until the log is fully read.
          </p>
        ) : null}
        <OpenPositions
          rows={d?.uniqueOpen}
          clock={clock}
          hold={hold}
          last={d?.uniqueClosed?.[0]}
          onSelect={onSelect}
          selectedId={selectedId}
        />
        <TradeTimeline rows={tape} onSelect={onSelect} selectedId={selectedId} />
        <Heatmap cards={buildStrategyCards(snap?.board, { uniqueClosed: d?.uniqueClosed, uniqueOpen: d?.uniqueOpen })} trades={d?.uniqueClosed} />
      </div>
      <aside className="desk-today__side">
        <HealthStrip rows={health} conn={conn} replay={clock?.replay} />
        <MarketContext regimes={d?.regimes} />
      </aside>
    </div>
  );
}
