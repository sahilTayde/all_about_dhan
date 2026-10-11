import { px } from "../../lib/paperBoard.js";

const WANT = ["NIFTY", "SENSEX", "BANKNIFTY"];

function tag(r) {
  const regime = String(r?.regime || "").toUpperCase();
  if (regime === "TREND" || regime === "TRENDING") return r.direction ? `TREND ${r.direction}` : "TREND";
  if (regime === "CHOP" || regime === "CHOPPY") return "CHOP";
  if (regime === "SIDEWAYS" || regime === "RANGE") return "CONSOLIDATION";
  if (regime) return `${regime}${r.direction ? ` ${r.direction}` : ""}`;
  return null;
}

/** Spot + IV + trend tag from last_index_regime. Missing underlyings stay empty. */
export function MarketContext({ regimes }) {
  const map = regimes || {};
  const rows = WANT.map((und) => {
    const r = map[und];
    if (!r || typeof r !== "object") {
      return { und, empty: true };
    }
    return {
      und,
      empty: false,
      spot: r.itm_bin?.index ?? r.spot ?? (r.last3_closes || []).at(-1),
      iv: r.iv,
      vix: r.vix ?? r.india_vix,
      tag: tag(r),
    };
  });
  if (rows.every((r) => r.empty) && !Object.keys(map).length) {
    return (
      <section className="market-context" data-testid="market-context">
        <h2>Market</h2>
        <p className="empty-state">No tape regime on the board.</p>
      </section>
    );
  }
  return (
    <section className="market-context" data-testid="market-context">
      <h2>Market</h2>
      <div className="market-context__grid">
        {rows.map((r) =>
          r.empty ? (
            <article key={r.und} className="market-card market-card--empty">
              <strong>{r.und}</strong>
              <p className="empty-state">No print</p>
            </article>
          ) : (
            <article key={r.und} className="market-card">
              <header>
                <strong>{r.und}</strong>
                <span className="market-card__px">{px(r.spot)}</span>
              </header>
              <p className="market-card__regime">{r.tag || "—"}</p>
              <dl className="kv-grid kv-grid--2">
                <div className="kv">
                  <dt>IV</dt>
                  <dd>{r.iv == null ? "—" : Number(r.iv).toFixed(1)}</dd>
                </div>
                <div className="kv">
                  <dt>VIX</dt>
                  <dd>{r.vix == null ? "—" : Number(r.vix).toFixed(1)}</dd>
                </div>
              </dl>
            </article>
          ),
        )}
      </div>
    </section>
  );
}
