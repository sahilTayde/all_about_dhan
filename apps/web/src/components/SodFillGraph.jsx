import { useMemo, useState } from "react";

const COLS = [
  { id: "analyst", x: 70, title: "Analysts" },
  { id: "picker", x: 230, title: "Picker" },
  { id: "observer", x: 390, title: "Observer" },
  { id: "desk", x: 550, title: "Desk fill" },
];

function tone(vs) {
  const s = String(vs || "");
  if (s === "MATCH" || s === "FILL" || s === "ALLOW" || s === "OPEN" || s === "DONE") return "ok";
  if (s === "DISSENT" || s === "VETO") return "bad";
  if (s === "SILENT") return "mute";
  return "warn";
}

export function SodFillGraph({ room, onPick }) {
  const [sel, setSel] = useState(null);
  const nodes = room?.nodes || [];
  const byCol = useMemo(() => {
    const m = { analyst: [], picker: [], observer: [], desk: [] };
    for (const n of nodes) (m[n.col] || m.analyst).push(n);
    return m;
  }, [nodes]);

  if (!room) {
    return <p className="muted">No fill room on this ticket yet.</p>;
  }

  const picked = nodes.find((n) => n.id === sel) || null;

  function choose(n) {
    setSel(n.id);
    if (onPick) onPick(n);
  }

  return (
    <div className="sod-wrap">
      <svg className="sod-svg" viewBox="0 0 640 220" role="img" aria-label="How the paper fill was built">
        <title>SOD fill path — click a node</title>
        {COLS.slice(0, 3).map((c, i) => (
          <line
            key={c.id}
            x1={c.x + 36}
            y1="110"
            x2={COLS[i + 1].x - 36}
            y2="110"
            className="sod-edge"
          />
        ))}
        {COLS.map((c) => {
          const list = byCol[c.id] || [];
          const start = 110 - ((list.length - 1) * 28) / 2;
          return (
            <g key={c.id}>
              <text x={c.x} y="22" className="sod-col">
                {c.title}
              </text>
              {list.map((n, i) => {
                const cy = start + i * 28;
                const active = sel === n.id;
                return (
                  <g
                    key={n.id}
                    className={`sod-node sod-node--${tone(n.vs)}${active ? " is-on" : ""}`}
                    tabIndex={0}
                    role="button"
                    onClick={() => choose(n)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        choose(n);
                      }
                    }}
                  >
                    <circle cx={c.x} cy={cy} r={active ? 16 : 13} />
                    <text x={c.x} y={cy + 4} textAnchor="middle">
                      {n.side === "CE" || n.side === "PE" ? n.side : n.vs?.[0] || "·"}
                    </text>
                    <text x={c.x} y={cy + 28} textAnchor="middle" className="sod-lab">
                      {n.label}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>
      <aside className="sod-detail" aria-live="polite">
        {picked ? (
          <>
            <strong>{picked.label}</strong>
            <p>
              {picked.side} · {picked.vs}
            </p>
            <p>{picked.detail}</p>
          </>
        ) : (
          <p>Click a node. Analysts vote. Picker chooses. Observer confirms. Desk paper-fills one ticket.</p>
        )}
        {room.placed ? (
          <p className="desk-sub">
            Paper fill {room.placed.index} {room.placed.side} {room.placed.strike} @ {room.placed.premium} ·{" "}
            {room.placed.when?.replace("T", " ").slice(0, 16)} · not a broker order
          </p>
        ) : null}
      </aside>
    </div>
  );
}

export function WatcherStrip({ watchers }) {
  if (!watchers?.length) return null;
  return (
    <ul className="watch-strip" aria-label="Who is watching this ticket">
      {watchers.map((w) => (
        <li key={`${w.who}-${w.type}`} className={`watch-chip watch-chip--${tone(w.type)}`}>
          <strong>{w.who}</strong>
          <span>{w.signal}</span>
          <em>{w.type}</em>
        </li>
      ))}
    </ul>
  );
}
