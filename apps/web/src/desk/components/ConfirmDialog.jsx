export function ConfirmDialog({ title, body, confirmLabel = "Confirm", onConfirm, onClose, danger }) {
  if (!title) return null;
  return (
    <div className="confirm-root" data-testid="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
      <button type="button" className="drawer-scrim" aria-label="Cancel" onClick={onClose} />
      <div className="confirm-card">
        <h3 id="confirm-title">{title}</h3>
        <p className="muted">{body}</p>
        <div className="btn-row">
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className={`btn ${danger ? "btn--danger" : "btn--primary"}`} onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
