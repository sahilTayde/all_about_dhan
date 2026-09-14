import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL;

async function fetchChampionBoard() {
  const url = API_URL
    ? `${API_URL}/paper/backtests/itm-champions`
    : "/mock/itm_champion_leaderboard.json";
  const res = await fetch(url);
  if (!res.ok) throw new Error(`champion board HTTP ${res.status}`);
  return res.json();
}

function fmtInr(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}₹${Math.round(n).toLocaleString("en-IN")}`;
}

function fmtPct(n) {
  if (n == null) return "—";
  return `${n}%`;
}

function streakLabel(kind, n) {
  if (!kind || !n) return "—";
  return `${kind}${n}`;
}

export function ItmChampionLeaderboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchChampionBoard()
      .then((j) => {
        if (!cancelled) setData(j);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <section className="panel champ-board" aria-labelledby="champ-board-title">
        <h2 id="champ-board-title">ITM champion leaderboard</h2>
        <p className="error-banner">{error}</p>
      </section>
    );
  }

  if (!data) {
    return (
      <section className="panel champ-board" aria-labelledby="champ-board-title">
        <h2 id="champ-board-title">ITM champion leaderboard</h2>
        <p className="muted">Loading paper champions…</p>
      </section>
    );
  }

  const board = data.leaderboard || [];
  const champ = data.champion_of_board;
  const next = data.next_action_items || [];

  return (
    <section className="panel champ-board" aria-labelledby="champ-board-title">
      <h2 id="champ-board-title">ITM champion leaderboard</h2>
      <p className="muted">
        PAPER only · ranks by after-cost P/L · session VWAP assumed offline, live volume Tuesday ·{" "}
        {data.orders || "orders refused"} · {data.promotion || "NO_PROMOTE"}
      </p>

      {champ ? (
        <div className="champ-crown" role="status">
          <p className="champ-crown-label">Current board leader</p>
          <p className="champ-crown-name">{champ.name}</p>
          <p className="champ-crown-meta">
            {fmtPct(champ.success_pct)} success · {fmtInr(champ.after_cost_pnl_inr)} · streak{" "}
            {streakLabel(champ.current_streak_kind, champ.current_streak)}
          </p>
        </div>
      ) : null}

      <div className="champ-table-wrap">
        <table className="champ-table">
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Strategy</th>
              <th scope="col">TF</th>
              <th scope="col">Trades</th>
              <th scope="col">W / L</th>
              <th scope="col">Success %</th>
              <th scope="col">Streak</th>
              <th scope="col">Max W</th>
              <th scope="col">P/L (1 lot)</th>
            </tr>
          </thead>
          <tbody>
            {board.map((row) => {
              const pnlClass =
                row.after_cost_pnl_inr > 0
                  ? "pos"
                  : row.after_cost_pnl_inr < 0
                    ? "neg"
                    : "";
              return (
                <tr key={row.champion_id} className={row.rank === 1 ? "champ-row--lead" : undefined}>
                  <td>{row.rank}</td>
                  <td>
                    <strong>{row.name}</strong>
                    <div className="champ-id">{row.champion_id}</div>
                  </td>
                  <td>{row.tf}</td>
                  <td>{row.trade_count}</td>
                  <td>
                    {row.wins} / {row.losses}
                  </td>
                  <td>{fmtPct(row.success_pct)}</td>
                  <td>{streakLabel(row.current_streak_kind, row.current_streak)}</td>
                  <td>{row.max_win_streak}</td>
                  <td className={pnlClass}>{fmtInr(row.after_cost_pnl_inr)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {data.vwap_mode ? <p className="champ-vwap">{data.vwap_mode}</p> : null}

      {next.length ? (
        <div className="champ-next">
          <h3>Next action items</h3>
          <ol>
            {next.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ol>
        </div>
      ) : null}

      {Array.isArray(data.honesty) ? (
        <ul className="champ-honesty">
          {data.honesty.map((h) => (
            <li key={h}>{h}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
