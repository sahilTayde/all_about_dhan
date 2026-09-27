export function DemoBadge({ what = "Static demo data from public/mock — not wired to the paper board yet" }) {
  return (
    <span className="demo-badge" title={what}>
      DEMO · mock
    </span>
  );
}

/** Static mock shown because the API is unreachable: must never pass for real paper trades. */
export function OfflineBanner() {
  return (
    <div className="offline-banner" role="alert">
      <strong>API OFFLINE · MOCK DATA</strong>
      <span>
        Every number below is the static demo board from public/mock — not your paper trades. Start the API:{" "}
        <code>./scripts/desk.sh website</code>
      </span>
    </div>
  );
}

export function Header({
  sourceLabel,
  onInfo,
  title = "Desk",
  kicker = "all_about_dhan",
  sub = "NIFTY / BANKNIFTY / SENSEX · paper · not advice",
}) {
  return (
    <header className="desk-header">
      <div>
        <p className="desk-kicker">{kicker}</p>
        <h1>{title}</h1>
        <p className="desk-sub">{sub}</p>
      </div>
      <div className="desk-header__tools">
        <span className="source-pill" title="Where this page's numbers come from">
          {sourceLabel}
        </span>
        {onInfo && (
          <button
            type="button"
            className="info-btn"
            aria-label="Open status legend"
            aria-haspopup="dialog"
            onClick={onInfo}
          >
            i
          </button>
        )}
      </div>
    </header>
  );
}
