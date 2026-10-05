import { buildJourney, motionAllowed } from "../lib/customerJourney.js";

function Sparkline({ spark, path, motion }) {
  if (!spark.d) {
    return (
      <div className="journey-spark journey-spark--empty" data-testid="journey-spark">
        <p>No last-known paper path. Not a live price.</p>
      </div>
    );
  }
  const last = spark.dots[spark.dots.length - 1];
  const first = spark.dots[0];
  return (
    <div className="journey-spark" data-testid="journey-spark" data-source={path.source}>
      <svg
        viewBox={`0 0 ${spark.width} ${spark.height}`}
        role="img"
        aria-label={`${path.source} path. Last known ${last.v}. Not a live price.`}
      >
        <defs>
          <linearGradient id="journey-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(91, 156, 255, 0.55)" />
            <stop offset="100%" stopColor="rgba(91, 156, 255, 0.04)" />
          </linearGradient>
        </defs>
        <path className="journey-spark__area" d={spark.area} fill="url(#journey-fill)" />
        <path className="journey-spark__line" d={spark.d} />
        {first ? <circle className="journey-spark__dot journey-spark__dot--start" cx={first.x} cy={first.y} r="3.2" /> : null}
        {last ? (
          <g className={motion ? "journey-spark__now" : ""}>
            <circle className="journey-spark__pulse" cx={last.x} cy={last.y} r="8" />
            <circle className="journey-spark__dot journey-spark__dot--now" cx={last.x} cy={last.y} r="4" />
          </g>
        ) : null}
      </svg>
      <p className="journey-spark__caption">
        {path.source} · last known {last.v.toLocaleString("en-IN")}
        {path.unit ? ` ${path.unit === "OPTION_PREMIUM" ? "premium" : "index"}` : ""}
        . Not a live price.
      </p>
    </div>
  );
}

export function TradeJourney({ view, journal, reduceMotion }) {
  const journey = buildJourney(view, journal);
  const motion = reduceMotion === true ? false : reduceMotion === false ? true : motionAllowed();

  return (
    <section
      className={`trade-journey ${motion ? "trade-journey--motion" : "trade-journey--still"}`}
      data-testid="trade-journey"
      data-phase={journey.phase}
      aria-labelledby="trade-journey-heading"
    >
      <header className="trade-journey__head">
        <div>
          <h2 id="trade-journey-heading">Trade journey</h2>
          <p>Signal → entry → hold → exit</p>
        </div>
        <span className={`journey-phase journey-phase--${journey.phase.toLowerCase()}`}>{journey.phase}</span>
      </header>

      <ol className="journey-rail" data-testid="journey-rail">
        {journey.steps.map((step, i) => (
          <li key={step.id} className={`journey-step journey-step--${step.state}`} data-step={step.id}>
            {i > 0 ? <span className="journey-step__wire" aria-hidden="true" /> : null}
            <span className="journey-step__node" aria-hidden="true" />
            <span className="journey-step__label" aria-current={step.state === "active" ? "step" : undefined}>
              {step.label}
            </span>
          </li>
        ))}
      </ol>

      <ul className="journey-chips" data-testid="journey-chips" aria-label="Status chips">
        {journey.chips.map((chip) => (
          <li key={chip.id} className={`journey-chip journey-chip--${chip.tone}`}>
            {chip.label}
          </li>
        ))}
      </ul>

      <Sparkline spark={journey.spark} path={journey.path} motion={motion} />
    </section>
  );
}
