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
        <span className="source-pill" title="Data is mock until an API is wired">
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
