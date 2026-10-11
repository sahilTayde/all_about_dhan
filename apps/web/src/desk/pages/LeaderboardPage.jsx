import { useMemo, useState } from "react";
import { HealthStrip } from "../components/HealthStrip.jsx";
import { StrategyCard } from "../components/StrategyCard.jsx";
import { SORT_KEYS, buildStrategyCards, matchesSlot, sortStrategyCards } from "../../lib/strategyBoard.js";

const LABELS = { net: "Net ₹", trades: "Trades", win: "Win %", dd: "Max DD", name: "Name" };

export function LeaderboardPage({ board, d, health, conn, onOpenCard }) {
  const [sort, setSort] = useState("net");
  const [dir, setDir] = useState("desc");
  const cards = useMemo(
    () =>
      sortStrategyCards(
        buildStrategyCards(board, { uniqueClosed: d?.uniqueClosed, uniqueOpen: d?.uniqueOpen }),
        sort,
        dir,
      ),
    [board, d, sort, dir],
  );

  function pick(key) {
    if (key === sort) setDir((d) => (d === "desc" ? "asc" : "desc"));
    else {
      setSort(key);
      setDir(key === "name" ? "asc" : "desc");
    }
  }

  return (
    <div className="desk-board" data-testid="desk-leaderboard">
      <header className="desk-board__head">
        <div>
          <h2>Paper books</h2>
          <p className="muted">Five registry slots + shadow. Readable names; id is the subtitle. NO_PROMOTE.</p>
        </div>
        <div className="sort-bar" role="group" aria-label="Sort books">
          {SORT_KEYS.map((key) => (
            <button
              key={key}
              type="button"
              className={`chip${sort === key ? " chip--active" : ""}`}
              aria-pressed={sort === key}
              onClick={() => pick(key)}
            >
              {LABELS[key]}
              {sort === key ? (dir === "desc" ? " ↓" : " ↑") : ""}
            </button>
          ))}
        </div>
      </header>
      <HealthStrip rows={health} conn={conn} />
      {!cards.length ? (
        <p className="empty-state" data-testid="leaderboard-empty">
          No paper books on the board.
        </p>
      ) : (
        <div className="slot-grid">
          {cards.map((card) => (
            <StrategyCard
              key={card.id}
              card={card}
              onOpen={
                onOpenCard
                  ? () => {
                      const latest = [...(d?.uniqueOpen || []), ...(d?.uniqueClosed || [])].find((t) =>
                        matchesSlot(t, card.bookId, card.shadow),
                      );
                      if (latest) onOpenCard(latest);
                    }
                  : undefined
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
