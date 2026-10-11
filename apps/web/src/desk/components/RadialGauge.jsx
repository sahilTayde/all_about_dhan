/** SVG radial for SL → LTP → target. Empty when marks are missing. */
export function RadialGauge({ progress, label = "Path" }) {
  if (!progress) {
    return (
      <div className="gauge gauge--empty" data-testid="path-gauge" aria-label={`${label} waiting`}>
        Waiting for path
      </div>
    );
  }
  const pct = Math.max(0, Math.min(100, progress.pos * 100));
  const r = 28;
  const c = 2 * Math.PI * r;
  const dash = (pct / 100) * c;
  const tone = progress.coveredPct >= 0 ? "up" : "down";
  return (
    <div className={`gauge gauge--${tone}`} data-testid="path-gauge" role="img" aria-label={`${label} ${progress.coveredPct}% to target`}>
      <svg viewBox="0 0 72 72" width="72" height="72">
        <circle className="gauge__track" cx="36" cy="36" r={r} />
        <circle
          className="gauge__arc"
          cx="36"
          cy="36"
          r={r}
          strokeDasharray={`${dash} ${c}`}
          transform="rotate(-90 36 36)"
        />
      </svg>
      <strong>{`${progress.coveredPct > 0 ? "+" : ""}${progress.coveredPct}%`}</strong>
      <span>to target</span>
    </div>
  );
}
