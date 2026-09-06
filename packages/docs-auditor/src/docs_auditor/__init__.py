"""Docs Auditor — local files only. Never prints secrets. No web scrape."""

from docs_auditor.auditor import AuditResult, Finding, run_audit

__all__ = ["AuditResult", "Finding", "run_audit"]
