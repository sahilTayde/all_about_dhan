"""Optional desk-intel bridge. Fail soft with DATA_INSUFFICIENT."""

from __future__ import annotations

from typing import Any, Optional

from trading_agents_india.fixtures import MarketContext, NewsItem, fixture_contexts


def try_load_desk_context(underlying: str) -> tuple[Optional[MarketContext], list[str]]:
    """Attempt to pull latest fused bias from desk_intel if installed.

    Dry-run / missing package → caller should use fixtures.
    """
    gaps: list[str] = []
    try:
        from desk_intel.news_ingest import ingest_news  # type: ignore
        from desk_intel.workspace import load_desk_workspace  # type: ignore
    except Exception:
        gaps.append(
            "DATA_INSUFFICIENT: desk_intel not importable — using fixtures for paper loop"
        )
        return None, gaps

    try:
        cfg = load_desk_workspace()
        events = ingest_news(cfg, offline=True, allow_fixtures=True)
    except Exception as exc:  # noqa: BLE001
        gaps.append(f"DATA_INSUFFICIENT: desk_intel ingest failed ({type(exc).__name__})")
        return None, gaps

    base = fixture_contexts().get(underlying.upper())
    if base is None:
        gaps.append(f"UNKNOWN: underlying {underlying}")
        return None, gaps

    mapped: list[NewsItem] = []
    for ev in events[:8]:
        tags = list(getattr(ev, "tags", []) or [])
        # Offline desk ingest is fixture-backed — never treat as live BIG_NEWS
        # unless the event itself carries BIG_NEWS.
        tags_u = {str(t).upper() for t in tags}
        if "BIG_NEWS" not in tags_u:
            if "FIXTURE" not in tags_u:
                tags.append("FIXTURE")
            if "ROUTINE" not in tags_u:
                tags.append("ROUTINE")
        mapped.append(
            NewsItem(
                headline=getattr(ev, "headline", "") or getattr(ev, "event", "news"),
                source_url=getattr(ev, "cited_url", "")
                or getattr(ev, "source_url", "https://example.invalid/desk"),
                tags=tags,
                risk_bias=getattr(ev, "risk_bias", "MIXED") or "MIXED",
                summary=getattr(ev, "summary", "") or "",
            )
        )
    if not mapped:
        gaps.append("DATA_INSUFFICIENT: desk_intel returned zero news events")
        return base, gaps

    return (
        MarketContext(
            underlying=base.underlying,
            chain_lean=base.chain_lean,
            trend_plain=base.trend_plain + " (news overlaid from desk_intel fixtures)",
            news=mapped,
            session_kind_hint="NORMAL",  # desk fixtures ≠ live BIG_NEWS day
            sentiment_label=base.sentiment_label,
            technical_note=base.technical_note,
            data_gaps=list(base.data_gaps) + gaps,
        ),
        gaps,
    )


def paper_desk_snippet(tickets: list[dict[str, Any]]) -> dict[str, Any]:
    """Shape compatible with later /paper/signal adapter (directional only)."""
    signals = {}
    skipped = {}
    for t in tickets:
        lean = t.get("lean")
        if lean in ("BUY_CE", "BUY_PE") and not t.get("risk_veto"):
            signals[t["underlying"]] = {
                "underlying": t["underlying"],
                "side": lean,
                "stage": t.get("stage"),
                "note": "agent paper lean — execution refused",
            }
        else:
            skipped[t["underlying"]] = f"{lean} / veto={t.get('risk_veto')}"
    return {
        "meta": {"source": "trading_agents_india", "placeholder": True},
        "signals": signals,
        "skipped": skipped,
        "execution": "refused",
    }
