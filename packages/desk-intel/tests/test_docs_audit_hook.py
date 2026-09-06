"""Docs Auditor hook: public payload only, no secrets."""

from desk_intel.docs_audit import attach_docs_audit
from desk_intel.workspace import load_desk_workspace


def test_attach_docs_audit_returns_public_dict() -> None:
    cfg = load_desk_workspace()
    payload = attach_docs_audit(cfg.repo_root, write=False)
    assert "ok" in payload
    assert "finding_count" in payload
    assert "checks_run" in payload
    assert "compliance" in payload
    blob = str(payload)
    assert "ACCESS_TOKEN=" not in blob
    assert "YOUTUBE_API_KEY=" not in blob
