"""News adapters: prefer Dhan (if API) then Moneycontrol via desk_intel RSS.

Never invent CNBC/StockTwits. Mark DATA_INSUFFICIENT when unwired.
Moneycontrol path uses existing workspace RSS (not HTML scrape). Layer:
fetched headlines = SOURCE_FACT candidates; interpretation stays HYPOTHESIS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from trading_agents_india.fixtures import NewsItem


@dataclass
class NewsBundle:
    items: list[NewsItem] = field(default_factory=list)
    sources_tried: list[str] = field(default_factory=list)
    data_gaps: list[str] = field(default_factory=list)
    layer_note: str = (
        "Headlines from wired feeds are SOURCE_FACT candidates; "
        "lean/hold interpretation remains HYPOTHESIS."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [
                {
                    "headline": n.headline,
                    "source_url": n.source_url,
                    "tags": n.tags,
                    "risk_bias": n.risk_bias,
                    "summary": n.summary,
                }
                for n in self.items
            ],
            "sources_tried": list(self.sources_tried),
            "data_gaps": list(self.data_gaps),
            "layer_note": self.layer_note,
        }


def try_dhan_news() -> NewsBundle:
    """Probe for a DhanHQ news API in our client. Honest DI if absent."""
    bundle = NewsBundle(sources_tried=["dhan_client.news"])
    try:
        import dhan_client  # type: ignore

        news_fn = getattr(dhan_client, "news", None)
        client_news = None
        if news_fn is None:
            # Look for submodule or Client attribute patterns without calling live.
            try:
                from dhan_client import client as _c  # type: ignore

                client_news = getattr(_c, "NewsClient", None) or getattr(
                    getattr(_c, "DhanClient", object), "news", None
                )
            except Exception:
                client_news = None
        if news_fn is None and client_news is None:
            bundle.data_gaps.append(
                "DATA_INSUFFICIENT: no DhanHQ news API surface in dhan_client "
                "(quotes/chain/charts only in this skeleton)"
            )
            return bundle
        bundle.data_gaps.append(
            "DATA_INSUFFICIENT: Dhan news surface detected by name but not "
            "invoked in paper loop (no invented headlines)"
        )
        return bundle
    except Exception:
        bundle.data_gaps.append(
            "DATA_INSUFFICIENT: dhan_client not importable — Dhan news skipped"
        )
        return bundle


def try_moneycontrol_via_desk(*, offline: bool = True) -> NewsBundle:
    """Use desk_intel RSS ingest (Moneycontrol URLs from workspace.yaml).

    Prefer offline/fixtures unless caller opts into live RSS later.
    Labeled: RSS path is VERIFY IF STABLE in MASTER_REQUIREMENTS — not scrape.
    """
    bundle = NewsBundle(sources_tried=["desk_intel.news_ingest / moneycontrol RSS"])
    try:
        from desk_intel.news_ingest import ingest_news  # type: ignore
        from desk_intel.workspace import load_desk_workspace  # type: ignore
    except Exception:
        bundle.data_gaps.append(
            "DATA_INSUFFICIENT: desk_intel not importable — Moneycontrol RSS unwired here"
        )
        return bundle

    try:
        cfg = load_desk_workspace()
        events = ingest_news(cfg, offline=offline, allow_fixtures=True)
    except Exception as exc:  # noqa: BLE001
        bundle.data_gaps.append(
            f"DATA_INSUFFICIENT: desk_intel Moneycontrol ingest failed ({type(exc).__name__})"
        )
        return bundle

    for ev in events[:8]:
        url = (
            getattr(ev, "cited_url", "")
            or getattr(ev, "source_url", "")
            or "https://www.moneycontrol.com/"
        )
        bundle.items.append(
            NewsItem(
                headline=getattr(ev, "headline", "") or getattr(ev, "event", "news"),
                source_url=url,
                tags=list(getattr(ev, "tags", []) or []) + ["MONEYCONTROL_OR_DESK_RSS"],
                risk_bias=getattr(ev, "risk_bias", "MIXED") or "MIXED",
                summary=getattr(ev, "summary", "") or "",
            )
        )
    if not bundle.items:
        bundle.data_gaps.append(
            "DATA_INSUFFICIENT: desk_intel returned zero news events "
            "(Moneycontrol RSS VERIFY IF STABLE)"
        )
    return bundle


def gather_news(*, prefer_live_rss: bool = False) -> NewsBundle:
    """Priority: Dhan (if API) → Moneycontrol/desk RSS → DI."""
    merged = NewsBundle()
    dhan = try_dhan_news()
    merged.sources_tried.extend(dhan.sources_tried)
    merged.data_gaps.extend(dhan.data_gaps)
    merged.items.extend(dhan.items)

    mc = try_moneycontrol_via_desk(offline=not prefer_live_rss)
    merged.sources_tried.extend(mc.sources_tried)
    merged.data_gaps.extend(mc.data_gaps)
    # Prefer Dhan items if any; else Moneycontrol/desk.
    if not merged.items:
        merged.items.extend(mc.items)
    elif mc.items:
        # Corroboration only — append distinct headlines as HYPOTHESIS context
        seen = {i.headline for i in merged.items}
        for item in mc.items:
            if item.headline not in seen:
                merged.items.append(item)

    if not merged.items:
        merged.data_gaps.append(
            "DATA_INSUFFICIENT: no Dhan or Moneycontrol headlines available — "
            "continue without news-derived edge"
        )
    # De-dupe gaps
    merged.data_gaps = list(dict.fromkeys(merged.data_gaps))
    return merged
