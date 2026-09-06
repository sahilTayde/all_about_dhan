"""Park unrelated pending/blocked videos for a later pass. Never deletes catalog rows."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .discovery import VideoRecord

AUDIT_PENDING_IDS = (
    "BTe6ekvvDHk",
    "EVk_Wa_1cm0",
    "_byuht38r5s",
    "4TT8IV5S1_A",
    "8h9SYvQWKMA",
    "DzT_681GThA",
    "5x6bYmCB0Gw",
    "_exmJYgFwFA",
)
AUDIT_IP_BLOCKED_IDS = (
    "pBQ1oVDVe3M",
    "G31RFueZLvk",
    "eApl0SfVBBY",
    "mPKASwm6Oqk",
    "pUg_7sPauQA",
    "dEvF8biE02M",
)
AUDIT_DISABLED_IDS = (
    "2aSkJT-IbqI",
    "-wRCKyORglc",
)
AUDIT_QUEUE_IDS = AUDIT_PENDING_IDS + AUDIT_IP_BLOCKED_IDS + AUDIT_DISABLED_IDS

# Explicit decisions for the Stage-1 pending + IP-blocked audit set.
PARK_REASONS: dict[str, str] = {
    "BTe6ekvvDHk": (
        "Gold Vault product (buy gold/silver on exchange); not NIFTY/SENSEX/"
        "BANKNIFTY options, strategy builder, indicators, or price action."
    ),
    "5x6bYmCB0Gw": (
        "Super Order app tutorial (place entry/target/stop in one order). "
        "Promo/product walkthrough, not a trading strategy."
    ),
    "2aSkJT-IbqI": (
        "LOW brand film (Dhan Ki Bhasha). Captions disabled. Not F&O strategy."
    ),
    "-wRCKyORglc": (
        "Diwali aarti / Muhurat Trading celebration. Captions disabled. "
        "Not options/strategy/indicators."
    ),
}

KEEP_REASONS: dict[str, str] = {
    "EVk_Wa_1cm0": "HIGH Darvas Box price-action / breakout strategy.",
    "_byuht38r5s": "HIGH intraday strategy + screener (transferable TA).",
    "4TT8IV5S1_A": "HIGH buy-the-dip / pullback strategy (price action).",
    "8h9SYvQWKMA": "HIGH Dhan Charts walkthrough (charting tools used for F&O analysis).",
    "DzT_681GThA": "HIGH order-flow / footprint / cumulative-delta strategy.",
    "_exmJYgFwFA": "HIGH option-selling masterclass.",
    "pBQ1oVDVe3M": "HIGH breakout strategy with confirmations.",
    "G31RFueZLvk": "HIGH BTST masterclass (RSI/risk; transferable).",
    "eApl0SfVBBY": "HIGH Dhan custom/advanced indicators how-to.",
    "mPKASwm6Oqk": "HIGH scalping indicators.",
    "pUg_7sPauQA": "HIGH VWAP scalping rules.",
    "dEvF8biE02M": "HIGH swing / multi-year breakout strategy.",
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def classify_park(video: VideoRecord) -> Optional[str]:
    """Return a park reason, or None to keep/retry now."""
    if video.video_id in PARK_REASONS:
        return PARK_REASONS[video.video_id]
    if video.stock_tag in ("STOCK_ONLY", "EXCLUDED_STOCK_ONLY"):
        return f"stock_tag={video.stock_tag}; Phase-1 is index options."
    if video.relevance_band == "LOW":
        return "LOW relevance (investing/promo/unrelated to F&O strategy)."
    if video.video_id in KEEP_REASONS:
        return None
    band = (video.relevance_band or "").upper()
    if band in ("HIGH", "MEDIUM"):
        return None
    return "Not HIGH/MEDIUM F&O/strategy/indicator/price-action."


def audit_queue(videos: list[VideoRecord]) -> list[VideoRecord]:
    wanted = set(AUDIT_QUEUE_IDS)
    by_id = {v.video_id: v for v in videos}
    return [by_id[vid] for vid in AUDIT_QUEUE_IDS if vid in wanted and vid in by_id]


def split_park(
    videos: list[VideoRecord],
) -> tuple[list[VideoRecord], list[VideoRecord]]:
    keep: list[VideoRecord] = []
    parked: list[VideoRecord] = []
    for video in videos:
        reason = classify_park(video)
        if reason:
            video.parked_reason = reason
            parked.append(video)
        else:
            video.parked_reason = None
            keep.append(video)
    return keep, parked


def write_parked_folder(
    parked_dir: Path,
    parked: list[VideoRecord],
) -> Path:
    parked_dir.mkdir(parents=True, exist_ok=True)
    retrieved = _now()
    readme_lines = [
        "# Parked for tomorrow",
        "",
        "These pending / caption-blocked videos are **not** Phase-1 F&O strategy "
        "sources (NIFTY / SENSEX / BANKNIFTY index options, strategy builder, "
        "indicators, price action, option buying). Catalog rows were **not** deleted.",
        "",
        f"Parked at: `{retrieved}`",
        "",
        "| video_id | title | status | relevance | reason |",
        "|---|---|---|---|---|",
    ]
    for video in parked:
        reason = video.parked_reason or "UNKNOWN"
        title = (video.title or "").replace("|", "/")
        readme_lines.append(
            f"| `{video.video_id}` | {title} | {video.status} | "
            f"{video.relevance_band or ''} | {reason} |"
        )
        pointer = {
            "video_id": video.video_id,
            "title": video.title,
            "url": video.url,
            "status": video.status,
            "relevance_band": video.relevance_band,
            "stock_tag": video.stock_tag,
            "topic_tags": video.topic_tags,
            "reason_parked": reason,
            "parked_at": retrieved,
            "catalog_row_kept": True,
            "retry_tomorrow": True,
            "pointer": f"data/youtube/video_catalog.json videos[] video_id={video.video_id}",
        }
        (parked_dir / f"{video.video_id}.json").write_text(
            json.dumps(pointer, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    readme_lines.extend(
        [
            "",
            "Do not extract claims from these until they are un-parked and have "
            "`TRANSCRIPT_VERIFIED` captions.",
            "",
        ]
    )
    readme_path = parked_dir / "README.md"
    readme_path.write_text("\n".join(readme_lines), encoding="utf-8")
    return readme_path
