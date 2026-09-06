const SIDE_COPY = {
  BUY_CE: { action: "BUY", option: "CE", hint: "Call buy — placeholder, not a live signal" },
  BUY_PE: { action: "BUY", option: "PE", hint: "Put buy — placeholder, not a live signal" },
};

export function SignalBadge({ side }) {
  const copy = SIDE_COPY[side] || {
    action: "—",
    option: "?",
    hint: "Unknown side",
  };
  const kind = side === "BUY_PE" ? "pe" : "ce";

  return (
    <section className="panel" aria-labelledby="signal-heading">
      <h2 id="signal-heading">Signal</h2>
      <div className={`signal-badge signal-badge--${kind}`}>
        <span className="signal-badge__action">{copy.action}</span>
        <span className="signal-badge__option">{copy.option}</span>
      </div>
      <p className="muted">{copy.hint}</p>
      {/* TODO(strategy): replace placeholder side once RESEARCH_READY_FOR_PROGRAMMING and a spec exists. */}
    </section>
  );
}
