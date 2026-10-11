import { DayPnlHero } from "../components/DayPnlHero.jsx";
import { MarketContext } from "../components/MarketContext.jsx";
import { OpenPositions } from "../components/OpenPositions.jsx";
import { TradeTimeline } from "../components/TradeTimeline.jsx";
import { todayTimeline } from "../../lib/strategyBoard.js";

export function TodayPage({ d, snap, clock, hold, indexing, onSelect, selectedId }) {
  const sessionDay = snap?.board?.session_ist_date || clock?.ist?.slice(0, 10);
  const today = (snap?.days || []).find((x) => x.day === sessionDay);
  const net = today?.net ?? d?.headlineNet ?? d?.today?.net_pnl_inr ?? null;
  const tape = todayTimeline(d?.uniqueOpen, d?.uniqueClosed, sessionDay);
  return (
    <div className="desk-today grid" data-testid="desk-today">
      <div className="span-8">
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
      </div>
      <div className="span-4 stack">
        <MarketContext regimes={d?.regimes} />
      </div>
    </div>
  );
}
