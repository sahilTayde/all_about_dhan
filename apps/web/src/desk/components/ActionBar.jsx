import { useState } from "react";
import { ConfirmDialog } from "./ConfirmDialog.jsx";

function Icon({ d }) {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <path fill="currentColor" d={d} />
    </svg>
  );
}

const I = {
  pause: "M6 5h4v14H6zm8 0h4v14h-4z",
  exit: "M6 6h12v2H6zm0 5h12v2H6zm0 5h8v2H6z",
  review: "M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z",
  refresh: "M12 6V3L8 7l4 4V8c2.8 0 5 2.2 5 5a5 5 0 1 1-5-5z",
  csv: "M5 3h14v18H5zm4 4v2h6V7zm0 4v2h6v-2zm0 4v2h6v-2z",
  bell: "M12 22a2 2 0 0 0 2-2H10a2 2 0 0 0 2 2zm6-6V11a6 6 0 1 0-12 0v5L4 17v1h16v-1z",
};

export function ActionBar({ onRefresh, onCsv, alertsOn, onToggleAlerts, onPause, onExit, onReview }) {
  const [ask, setAsk] = useState(null);
  const go = (id, fn, title, body, danger) => {
    if (!fn) return;
    setAsk({ id, fn, title, body, danger, label: title });
  };
  return (
    <div className="action-bar" data-testid="action-bar">
      <button type="button" className="btn btn--ghost" onClick={onRefresh}>
        <Icon d={I.refresh} /> Refresh
      </button>
      <button type="button" className="btn btn--ghost" onClick={onCsv}>
        <Icon d={I.csv} /> Download CSV
      </button>
      <button type="button" className={`btn ${alertsOn ? "btn--primary" : "btn--ghost"}`} onClick={onToggleAlerts} aria-pressed={Boolean(alertsOn)}>
        <Icon d={I.bell} /> {alertsOn ? "Alerts on" : "Toggle alerts"}
      </button>
      <button
        type="button"
        className="btn btn--secondary"
        onClick={() => go("pause", onPause, "Pause this paper slot?", "New paper fills on this slot stay closed until you resume. Not a live order.", false)}
      >
        <Icon d={I.pause} /> Pause slot
      </button>
      <button
        type="button"
        className="btn btn--danger"
        onClick={() => go("exit", onExit, "Exit paper fill?", "Books a paper exit on the open ticket. Orders stay refused.", true)}
      >
        <Icon d={I.exit} /> Exit (paper)
      </button>
      <button
        type="button"
        className="btn btn--secondary"
        onClick={() => go("review", onReview, "Mark reviewed?", "Desk note only. Does not promote the book.", false)}
      >
        <Icon d={I.review} /> Mark reviewed
      </button>
      <ConfirmDialog
        title={ask?.title}
        body={ask?.body}
        confirmLabel={ask?.label}
        danger={ask?.danger}
        onClose={() => setAsk(null)}
        onConfirm={() => {
          ask?.fn?.();
          setAsk(null);
        }}
      />
    </div>
  );
}
