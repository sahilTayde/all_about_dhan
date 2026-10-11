const LINE_STROKE = { entry: "#8fb4d9", stop: "#e0a0a8", target: "#8fd4b2" };

/** Tiny SVG premium path from recorded marks. Empty when fewer than two points. */
export function PremiumSpark({ points, lines = [], width = 140, height = 44, label = "Premium" }) {
  if (!points?.length || points.length < 2) {
    return (
      <div className="spark spark--empty" data-testid="premium-spark" aria-label={`${label} empty`}>
        No premium path
      </div>
    );
  }
  const ys = [...points.map((p) => p.value ?? p.v), ...lines.map((l) => l.value).filter((v) => Number.isFinite(v))];
  const min = Math.min(...ys);
  const max = Math.max(...ys);
  const span = max - min || 1;
  const yOf = (v) => height - 3 - ((v - min) / span) * (height - 6);
  const step = (width - 4) / (points.length - 1);
  const pts = points
    .map((p, i) => {
      const yv = p.value ?? p.v;
      const x = 2 + i * step;
      return `${x.toFixed(1)},${yOf(yv).toFixed(1)}`;
    })
    .join(" ");
  const first = points[0].value ?? points[0].v;
  const last = points[points.length - 1].value ?? points[points.length - 1].v;
  const tone = last > first ? "up" : last < first ? "down" : "flat";
  return (
    <svg
      className={`spark spark--${tone}`}
      data-testid="premium-spark"
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      role="img"
      aria-label={`${label} spark`}
    >
      {lines
        .filter((l) => Number.isFinite(l.value))
        .map((l) => (
          <line
            key={l.id || l.label}
            x1="2"
            x2={width - 2}
            y1={yOf(l.value)}
            y2={yOf(l.value)}
            stroke={LINE_STROKE[l.id] || "#6a7686"}
            strokeDasharray="3 3"
            strokeWidth="1"
          />
        ))}
      <polyline fill="none" stroke="currentColor" strokeWidth="1.6" points={pts} />
    </svg>
  );
}

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
