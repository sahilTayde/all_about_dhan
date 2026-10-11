/** Tiny SVG equity spark. Empty when the book has no closed fills. */
export function EquitySpark({ curve, width = 160, height = 36, label = "Equity" }) {
  if (!curve?.length) {
    return (
      <div className="spark spark--empty" data-testid="equity-spark" aria-label={`${label} empty`}>
        No equity curve
      </div>
    );
  }
  const ys = curve.map((p) => p.v);
  const min = Math.min(0, ...ys);
  const max = Math.max(0, ...ys);
  const span = max - min || 1;
  const step = curve.length === 1 ? 0 : (width - 4) / (curve.length - 1);
  const pts = curve
    .map((p, i) => {
      const x = 2 + i * step;
      const y = height - 3 - ((p.v - min) / span) * (height - 6);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const last = curve[curve.length - 1].v;
  const tone = last > 0 ? "up" : last < 0 ? "down" : "flat";
  return (
    <svg
      className={`spark spark--${tone}`}
      data-testid="equity-spark"
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      role="img"
      aria-label={`${label} spark`}
    >
      <polyline fill="none" stroke="currentColor" strokeWidth="1.6" points={pts} />
    </svg>
  );
}
