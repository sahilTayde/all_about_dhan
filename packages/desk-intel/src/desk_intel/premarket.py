"""PRE_MARKET tape: GIFT/SGX, pre-open, US close / Asia.

RSS is fetched. kind=verify/todo is documented only — no HTML scrape for quotes.
No invented Dhan endpoints.
"""

from __future__ import annotations

import logging
from config.load import NewsSource, WorkspaceConfig
from desk_intel.fixtures import (
    fixture_gift_prints,
    fixture_global_prints,
    fixture_preopen_prints,
)
from desk_intel.news_ingest import aggregate_news_bias, ingest_source
from desk_intel.schema import COMPLIANCE_NOTE, NewsEvent, PremarketBrief, TapePrint
from desk_intel.time_ist import now_ist_iso

log = logging.getLogger("desk_intel.premarket")


def _verify_row(source: NewsSource, bucket: str) -> TapePrint:
    return TapePrint(
        id=source.id,
        bucket=bucket,
        status="VERIFY" if source.kind in ("verify", "official") else "TODO",
        headline=f"{source.id}: documented URL only — no HTML quote scrape",
        source_url=source.url,
        note=source.note or "VERIFY/TODO. Not a DhanHQ endpoint.",
        tags=list(source.tags),
        layer="HYPOTHESIS",
    )


def _rss_to_prints(source: NewsSource, events: list[NewsEvent], bucket: str) -> list[TapePrint]:
    if not events:
        row = _verify_row(source, bucket)
        row.status = "DATA_INSUFFICIENT"
        row.headline = f"{source.id}: RSS empty or not XML — DATA_INSUFFICIENT"
        return [row]
    out: list[TapePrint] = []
    for event in events[:5]:
        out.append(
            TapePrint(
                id=f"{source.id}:{event.event}",
                bucket=bucket,
                status="RSS",
                headline=event.headline,
                source_url=event.cited_url or source.url,
                note=f"risk_bias={event.risk_bias}. Surprise {event.surprise_note}.",
                tags=list(event.tags) + list(source.tags),
            )
        )
    return out


def ingest_tape_bucket(
    sources: list[NewsSource],
    cfg: WorkspaceConfig,
    bucket: str,
    *,
    offline: bool,
) -> list[TapePrint]:
    if offline:
        if bucket == "gift_nifty":
            return fixture_gift_prints()
        if bucket == "pre_open":
            return fixture_preopen_prints()
        if bucket.startswith("global"):
            return fixture_global_prints()
        return []

    prints: list[TapePrint] = []
    for source in sources:
        if not source.enabled:
            continue
        if source.kind == "rss":
            events = ingest_source(source, cfg.desk_intel)
            prints.extend(_rss_to_prints(source, events, bucket))
        else:
            prints.append(_verify_row(source, bucket))
            log.info("tape %s id=%s kind=%s — VERIFY/TODO, not scraped", bucket, source.id, source.kind)
    if not prints:
        log.warning("no tape rows for %s — fixtures", bucket)
        return ingest_tape_bucket(sources, cfg, bucket, offline=True)
    return prints


def regime_note(events: list[NewsEvent], tape: list[TapePrint]) -> str:
    bias = aggregate_news_bias(events)
    gift = next((t for t in tape if t.bucket == "gift_nifty" and t.level is not None), None)
    bits = [
        f"news_regime={bias} (keyword HYPOTHESIS; surprise mostly UNKNOWN)",
        "Dhan chain snapshot is separate (token or fixture).",
    ]
    if gift:
        bits.append(f"GIFT/SGX: {gift.vs_cash_note or gift.headline} [{gift.status}]")
    else:
        bits.append("GIFT/SGX: DATA_INSUFFICIENT unless a public RSS/API is verified")
    missing_pre = not any(t.bucket == "pre_open" for t in tape)
    if missing_pre:
        bits.append("pre-open: no public grid — VERIFY NSE circular; no Dhan REST")
    bits.append("Education ≠ advice. Regime note is not a ticket.")
    return " | ".join(bits)


def gather_premarket(
    cfg: WorkspaceConfig,
    events: list[NewsEvent],
    *,
    offline: bool,
) -> PremarketBrief:
    tape: list[TapePrint] = []
    tape.extend(ingest_tape_bucket(cfg.gift_sources, cfg, "gift_nifty", offline=offline))
    tape.extend(ingest_tape_bucket(cfg.pre_open_sources, cfg, "pre_open", offline=offline))
    tape.extend(ingest_tape_bucket(cfg.global_tape_sources, cfg, "global_us", offline=offline))

    missing: list[str] = []
    if not any(t.bucket == "gift_nifty" and t.status in ("RSS", "FIXTURE") for t in tape):
        missing.append("GIFT_NIFTY_LIVE_QUOTE")
    if not any(t.bucket == "sgx" and t.status == "RSS" for t in tape):
        missing.append("SGX_PUBLIC_FEED")
    if not any(t.bucket == "pre_open" and t.status == "RSS" for t in tape):
        missing.append("NSE_PREOPEN_API")

    job = cfg.jobs.pre_market
    return PremarketBrief(
        as_of_ist=now_ist_iso(),
        job="PRE_MARKET",
        before_ist=job.before_ist or "09:15",
        news_count=len(events),
        tape=tape,
        regime_note=regime_note(events, tape),
        missing=missing,
        compliance=COMPLIANCE_NOTE,
    )
