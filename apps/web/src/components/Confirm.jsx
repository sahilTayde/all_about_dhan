import { useState } from "react";

/** Button that asks before doing anything. */
export function ConfirmButton({ label, title, body, onConfirm, danger = false, testid }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" className={`chip-btn${danger ? " chip-btn--danger" : ""}`} data-testid={testid} onClick={() => setOpen(true)}>
        {label}
      </button>
      {open ? (
        <div className="confirm-backdrop" role="dialog" aria-modal="true" aria-label={title}>
          <div className="confirm-box">
            <h3>{title}</h3>
            <p className="muted">{body}</p>
            <div className="confirm-actions">
              <button type="button" className="chip-btn" onClick={() => setOpen(false)}>Cancel</button>
              <button type="button" className={`chip-btn${danger ? " chip-btn--danger" : " is-on"}`} onClick={() => { setOpen(false); onConfirm?.(); }}>
                Yes, {label.toLowerCase()}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
