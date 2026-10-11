import { useMemo, useState } from "react";
import { StrategyCard } from "../components/StrategyCard.jsx";
import { SORT_KEYS, buildStrategyCards, sortStrategyCards } from "../../lib/strategyBoard.js";

const LABELS = { net: "Net ₹", trades: "Trades", win: "Win %", dd: "Max DD", name: "Name" };

export function LeaderboardPage({ board, d, onOpenCard }) {
  const [sort, setSort] = useState("net");
  const [dir, setDir] = useState("desc");
  const cards = useMemo(
    () => sortStrategyCards(buildStrategyCards(board, { uniqueClosed: d?.closed, uniqueOpen: d?.open }), sort, dir),
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
          <p className="muted">Five slots + shadow variants when the tape has them. Sortable. NO_PROMOTE.</p>
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
                      const latest = [...(d?.open || []), ...(d?.closed || [])].find((t) => {
                        const books = t.books?.length ? t.books : [t.book_id];
                        return books.includes(card.bookId) && Boolean(t.shadow) === card.shadow;
                      });
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
