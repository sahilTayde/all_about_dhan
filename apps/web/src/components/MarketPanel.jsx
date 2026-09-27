import { px } from "../lib/paperBoard.js";

const f2 = (n) => (n == null || !Number.isFinite(Number(n)) ? "—" : Number(n).toFixed(2));
const pct = (n) => (n == null || !Number.isFinite(Number(n)) ? "—" : `${(Number(n) * 100).toFixed(3)}%`);

/** Current Market (§49) from the board's last index regime. Global context is not in the data, so it is not shown. */
export function MarketPanel({ regimes }) {
  const list = Object.entries(regimes || {}).filter(([, r]) => r && typeof r === "object");
  if (!list.length) return null;
  return (
    <section className="panel market-panel">
      <div className="panel__head">
        <h2>Current market</h2>
        <span className="muted small">last tape tick · paper</span>
      </div>
      <div className="market-grid">
        {list.map(([und, r]) => {
          const index = r.itm_bin?.index ?? (r.last3_closes || []).at(-1);
          const sr = r.sr_near;
          return (
            <article key={und} className="market-card">
              <header>
                <strong>{und}</strong>
                <span className="market-card__px">{px(index)}</span>
              </header>
              <p className={`market-card__regime dir--${String(r.direction || "").toLowerCase()}`}>
                {r.regime || "—"} {r.direction || ""} <span className="muted">ER {f2(r.er)}</span>
              </p>
              <dl className="kv-grid kv-grid--3">
                <div className="kv">
                  <dt>Realized vol</dt>
                  <dd>{pct(r.realized_vol)}</dd>
                </div>
                <div className="kv">
                  <dt>IV</dt>
                  <dd>{f2(r.iv)}</dd>
                </div>
                <div className="kv">
                  <dt>Range/ATR</dt>
                  <dd>{f2(r.range_over_atr)}</dd>
                </div>
                <div className="kv">
                  <dt>VWAP</dt>
                  <dd>{px(r.vwap)}</dd>
                </div>
                <div className="kv">
                  <dt>EMA{r.ema_len ? ` ${r.ema_len}` : ""}</dt>
                  <dd>{px(r.ema)}</dd>
                </div>
                <div className="kv">
                  <dt>{sr?.name ? `Near ${sr.name}` : "POC"}</dt>
                  <dd>{sr?.px != null ? `${px(sr.px)} ${sr.kind || ""}` : px(r.proxy_poc)}</dd>
                </div>
              </dl>
            </article>
          );
        })}
      </div>
    </section>
  );
}
