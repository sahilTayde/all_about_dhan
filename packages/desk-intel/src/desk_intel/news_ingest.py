"""Economic headlines via RSS / official feeds. No HTML scrape as the only path.

Sources live in config/workspace.yaml ``sources.news[]`` (customer-editable).
Surprise vs consensus is UNKNOWN unless a calendar adapter is filled in later.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Iterable, Optional
from xml.etree.ElementTree import Element

import httpx

from config.load import DeskIntelSettings, NewsSource, WorkspaceConfig
from desk_intel.fixtures import FIXTURE_NEWS
from desk_intel.schema import NewsEvent, RiskBias
from desk_intel.time_ist import now_ist_iso, parse_rss_datetime, to_ist, within_hours

log = logging.getLogger("desk_intel.news")

USER_AGENT = "all_about_dhan-desk-intel/0.1 (research; education-not-advice)"

_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

# Fallback if yaml keywords are empty. ROOM TO EDIT — prefer workspace.yaml.
_DEFAULT_KEYWORDS = {
    "macro_event": [
        "gdp", "pmi", "cpi", "wpi", "iip", "rbi", "mpc", "repo", "fomc", "fed",
        "nfp", "payroll", "crude", "oil", "brent", "wti", "usdinr", "rupee",
        "dollar", "inflation", "hawkish", "dovish", "rate hike", "rate cut",
        "mospi", "budget", "fiscal",
    ],
    "risk_off": [
        "hawkish", "rate hike", "inflation surge", "cpi hot", "war",
        "geopolitical", "default", "crash", "selloff", "risk-off",
        "crude spike", "crude jumps", "oil jumps", "rupee falls", "rupee slides",
        "dollar surge", "tighten",
    ],
    "risk_on": [
        "dovish", "rate cut", "stimulus", "gdp beat", "pmi expansion",
        "ceasefire", "risk-on", "crude falls", "oil drops", "rupee gains",
        "inflation cools",
    ],
    "no_trade": [
        "circuit", "trading halt", "result day", "unknown print", "data delayed",
    ],
}


class CalendarPlaceholder:
    """Wire an economic-calendar API later (consensus vs print).

    RSS items almost never include surprise. Return None / UNKNOWN.
    ROOM TO EDIT.
    """

    def surprise_vs_consensus(self, headline: str) -> Optional[float]:
        _ = headline
        return None


def _kw_map(settings: DeskIntelSettings) -> dict[str, list[str]]:
    merged = {k: [x.lower() for x in v] for k, v in _DEFAULT_KEYWORDS.items()}
    for key, values in (settings.keywords or {}).items():
        merged[key] = [str(v).lower() for v in values]
    return merged


def _hits(text: str, needles: Iterable[str]) -> list[str]:
    blob = (text or "").lower()
    return [n for n in needles if n and n in blob]


def classify_headline(
    headline: str,
    summary: str,
    settings: DeskIntelSettings,
    source_tags: Optional[list[str]] = None,
) -> tuple[RiskBias, list[str], list[str]]:
    """Keyword map → risk_bias. HYPOTHESIS, not a model.

    Crude 90→95 style oil-up language → RISK_OFF hypothesis for energy/INR,
    never an automatic PE.
    """
    blob = f"{headline} {summary}"
    kws = _kw_map(settings)
    tags = list(source_tags or [])
    hits = _hits(blob, kws.get("macro_event") or [])
    if hits and "MACRO_EVENT" not in tags:
        tags.append("MACRO_EVENT")
    no_trade = _hits(blob, kws.get("no_trade") or [])
    off_hits = _hits(blob, kws.get("risk_off") or [])
    on_hits = _hits(blob, kws.get("risk_on") or [])
    keywords = sorted(set(hits + off_hits + on_hits + no_trade))
    if no_trade:
        return "NO_TRADE", tags, keywords
    if off_hits and on_hits:
        return "MIXED", tags, keywords
    if off_hits:
        return "RISK_OFF", tags, keywords
    if on_hits:
        return "RISK_ON", tags, keywords
    if hits:
        return "MIXED", tags, keywords
    return "MIXED", tags, keywords


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _child_text(el: Element, *names: str) -> str:
    for child in list(el):
        if _local(child.tag).lower() in {n.lower() for n in names}:
            return (child.text or "").strip()
    return ""


def _link_href(el: Element) -> str:
    for child in list(el):
        if _local(child.tag).lower() == "link":
            href = child.attrib.get("href") or (child.text or "").strip()
            if href:
                return href
    return ""


def parse_feed_xml(xml_text: str) -> list[dict[str, str]]:
    """RSS 2.0 or Atom. Returns dicts with title, link, published, summary."""
    xml_text = (xml_text or "").lstrip()
    if not xml_text or xml_text[:1] != "<":
        raise ValueError("response is not XML")
    # HTML landing pages are not feeds.
    head = xml_text[:200].lower()
    if "<html" in head or "<!doctype html" in head:
        raise ValueError("HTML page, not RSS/Atom")
    root = ET.fromstring(xml_text)
    items: list[dict[str, str]] = []
    root_name = _local(root.tag).lower()
    if root_name == "rss" or root.find("channel") is not None:
        channel = root.find("channel") if root_name == "rss" else root
        if channel is None:
            channel = root
        for item in channel.findall("item"):
            items.append(
                {
                    "title": _child_text(item, "title"),
                    "link": _child_text(item, "link") or _link_href(item),
                    "published": _child_text(item, "pubDate", "date", "published"),
                    "summary": _child_text(item, "description", "summary"),
                }
            )
        return items
    # Atom
    entries = root.findall("atom:entry", _ATOM_NS) or [
        e for e in root if _local(e.tag).lower() == "entry"
    ]
    for entry in entries:
        items.append(
            {
                "title": _child_text(entry, "title"),
                "link": _link_href(entry) or _child_text(entry, "id"),
                "published": _child_text(entry, "updated", "published"),
                "summary": _child_text(entry, "summary", "content"),
            }
        )
    return items


def _fetch_url(url: str, timeout: float = 12.0) -> str:
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"},
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def ingest_source(
    source: NewsSource,
    settings: DeskIntelSettings,
    *,
    calendar: Optional[CalendarPlaceholder] = None,
) -> list[NewsEvent]:
    if not source.enabled or not source.url:
        return []
    calendar = calendar or CalendarPlaceholder()
    try:
        body = _fetch_url(source.url)
        rows = parse_feed_xml(body)
    except Exception as exc:
        log.warning("news feed skipped id=%s kind=%s err=%s", source.id, source.kind, type(exc).__name__)
        return []

    events: list[NewsEvent] = []
    lookback = settings.news_lookback_hours
    for row in rows:
        title = (row.get("title") or "").strip()
        if not title:
            continue
        published = parse_rss_datetime(row.get("published") or "")
        if published is not None:
            published = to_ist(published)
        if not within_hours(published, lookback):
            continue
        summary = (row.get("summary") or "")[:500]
        bias, tags, keywords = classify_headline(
            title, summary, settings, list(source.tags)
        )
        link = (row.get("link") or source.url).strip()
        surprise = calendar.surprise_vs_consensus(title)
        events.append(
            NewsEvent(
                event=keywords[0].upper() if keywords else "HEADLINE",
                time_ist=published.replace(microsecond=0).isoformat()
                if published
                else now_ist_iso(),
                source_id=source.id,
                source_url=source.url,
                headline=title,
                tags=tags,
                risk_bias=bias,
                surprise_vs_consensus=surprise,
                surprise_note=(
                    "UNKNOWN — RSS/official feeds usually have no consensus print"
                    if surprise is None
                    else "calendar adapter provided a numeric surprise"
                ),
                keywords_hit=keywords,
                cited_url=link,
                summary=summary,
                layer="HYPOTHESIS",
            )
        )
    return events


def ingest_news(
    cfg: WorkspaceConfig,
    *,
    offline: bool = False,
    allow_fixtures: bool = True,
) -> list[NewsEvent]:
    settings = cfg.desk_intel
    if offline:
        log.info("news ingest offline — using fixtures")
        return list(FIXTURE_NEWS)

    events: list[NewsEvent] = []
    for source in cfg.news_sources:
        events.extend(ingest_source(source, settings))

    if not events and allow_fixtures:
        log.warning("no live RSS items — falling back to fixtures (DATA_INSUFFICIENT)")
        return list(FIXTURE_NEWS)
    return events


def aggregate_news_bias(events: list[NewsEvent]) -> RiskBias:
    if not events:
        return "MIXED"
    if any(e.risk_bias == "NO_TRADE" for e in events):
        return "NO_TRADE"
    off_n = sum(1 for e in events if e.risk_bias == "RISK_OFF")
    on_n = sum(1 for e in events if e.risk_bias == "RISK_ON")
    if off_n and on_n:
        return "MIXED"
    if off_n > on_n:
        return "RISK_OFF"
    if on_n > off_n:
        return "RISK_ON"
    return "MIXED"
