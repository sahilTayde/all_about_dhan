"""CLI: validate-key, catalog, transcripts, run, show-config, topics.

Usage (from teams/01_research/youtube):

    python -m src show-config
    python -m src validate-key
    python -m src catalog
    python -m src transcripts
    python -m src transcripts --retry-pending
    python -m src transcripts --english
    python -m src transcripts --retry-pending --english
    python -m src topics
    python -m src run

Channels: config/workspace.yaml (default enabled: @DhanHQ).
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, Optional

from .catalog_io import (
    catalog_meta_from_discovery,
    load_catalog_meta,
    merge_catalog_meta,
    read_catalog_csv,
    write_catalog,
)
from .config import (
    PLAN_SEED_VIDEO_IDS,
    Settings,
    load_settings,
)
from .discovery import VideoRecord, discover_channel
from .topics import run_topic_cluster
from .english import (
    STATUS_ENGLISH_UNAVAILABLE,
    STATUS_ENGLISH_VERIFIED,
    collect_english_many,
    hydrate_english_from_disk,
    select_english_targets,
)
from .park import audit_queue, split_park, write_parked_folder
from .popularity import rank_videos
from .relevance import apply_relevance
from .sanitize import sanitize
from .transcripts import (
    STATUS_UNAVAILABLE,
    STATUS_UNCERTAIN,
    STATUS_VERIFIED,
    collect_many,
    hydrate_catalog_from_disk,
)
from .youtube_client import YouTubeApiError, YouTubeClient

log = logging.getLogger("youtube_stage1")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


def _fix_hint(reason: str, http_status: int) -> str:
    reason_l = (reason or "").lower()
    if reason_l in ("keyinvalid", "invalid", "unknownapikey") or http_status in (400, 401):
        return (
            "The API key looks invalid. Create a new YouTube Data API v3 key in "
            "Google Cloud Console and put it in repo-root .env as YOUTUBE_API_KEY. "
            "Do not paste the key into chat."
        )
    if reason_l in ("accessnotconfigured", "servicedisabled") or "has not been used" in reason_l:
        return (
            "Enable YouTube Data API v3 on the Google Cloud project that owns this key, "
            "then retry."
        )
    if reason_l in ("quotaexceeded", "dailylimitexceeded"):
        return (
            "YouTube Data API quota is exhausted. Wait for the daily reset or request "
            "a quota increase, then retry catalog. Transcripts do not use this quota."
        )
    if reason_l in ("ratelimitexceeded", "userratelimitexceeded"):
        return "Rate limited. Wait a minute and retry."
    if reason_l in ("iprefererblocked", "forbidden", "apinotactivated"):
        return (
            "The key is restricted (IP, referrer, or API). Allow YouTube Data API v3 "
            "and this machine if you use IP restrictions."
        )
    if reason_l == "network_error" or http_status == 0:
        return "Network error reaching YouTube Data API. Check connectivity and retry."
    return (
        "Key validation failed. Confirm YouTube Data API v3 is enabled, the key is "
        "correct in repo-root .env, and quota remains. Do not paste the key into chat."
    )


def _enabled_sources(settings: Settings) -> list:
    sources = list(settings.enabled_youtube_sources or [])
    if sources:
        return sources
    # Last-resort fallback so a missing yaml list still checks the primary handle.
    from types import SimpleNamespace

    return [
        SimpleNamespace(
            id="dhanhq",
            handle=settings.channel_handle,
            url=settings.channel_url,
            playlists_url=settings.playlists_url,
            tier="TIER_1",
            origin_tag="DHAN-DERIVED",
        )
    ]


def _sources_markdown(settings: Settings, meta: Optional[dict[str, Any]] = None) -> str:
    listed = (meta or {}).get("sources") or []
    if listed:
        parts = []
        for item in listed:
            handle = item.get("handle") or ""
            url = item.get("source") or ""
            tier = item.get("tier") or ""
            origin = item.get("origin_tag") or ""
            label = f"@{handle}" if handle and not str(handle).startswith("@") else handle
            if url:
                parts.append(f"[{label}]({url}) (`{tier}` / `{origin}`)")
            else:
                parts.append(f"{label} (`{tier}` / `{origin}`)")
        return "; ".join(parts)
    parts = []
    for source in _enabled_sources(settings):
        parts.append(
            f"[{source.display_handle if hasattr(source, 'display_handle') else '@' + source.handle}]"
            f"({source.url}) (`{source.tier}` / `{source.origin_tag}`)"
        )
    return "; ".join(parts) if parts else f"[@{settings.channel_handle}]({settings.channel_url})"


def validate_key(settings: Settings) -> dict[str, Any]:
    client = YouTubeClient(
        settings.youtube_api_key, pause_seconds=settings.request_pause_seconds
    )
    sources = _enabled_sources(settings)
    per_source: list[dict[str, Any]] = []
    try:
        for source in sources:
            try:
                channel = client.channels_by_handle(source.handle)
                channel_id = channel.get("id")
                playlists = client.list_playlists(channel_id)
                per_source.append(
                    {
                        "valid": True,
                        "http_status": 200,
                        "reason": None,
                        "source_id": source.id,
                        "tier": source.tier,
                        "channel_id": channel_id,
                        "channel_name": (channel.get("snippet") or {}).get("title"),
                        "playlist_count": len(playlists),
                        "fix": None,
                    }
                )
            except YouTubeApiError as exc:
                per_source.append(
                    {
                        "valid": False,
                        "http_status": exc.http_status,
                        "reason": exc.reason,
                        "source_id": source.id,
                        "tier": source.tier,
                        "channel_id": None,
                        "channel_name": None,
                        "playlist_count": None,
                        "fix": _fix_hint(exc.reason, exc.http_status),
                        "message": sanitize(exc.message, settings.youtube_api_key),
                    }
                )
        primary = per_source[0] if per_source else {
            "valid": False,
            "http_status": 0,
            "reason": "no_enabled_sources",
            "channel_id": None,
            "channel_name": None,
            "playlist_count": None,
            "fix": "Enable at least one sources.youtube row in config/workspace.yaml.",
        }
        return {
            "valid": all(item["valid"] for item in per_source) if per_source else False,
            "http_status": primary.get("http_status"),
            "reason": None if all(item["valid"] for item in per_source) else primary.get("reason"),
            "channel_id": primary.get("channel_id"),
            "channel_name": primary.get("channel_name"),
            "playlist_count": primary.get("playlist_count"),
            "quota_units_used": client.quota_units_used,
            "fix": None if all(item.get("valid") for item in per_source) else primary.get("fix"),
            "sources": per_source,
        }
    finally:
        client.close()


def print_validation(result: dict[str, Any]) -> None:
    status = "valid" if result["valid"] else "invalid"
    print(f"key_validation: {status}")
    print(f"http_status: {result['http_status']}")
    print(f"channel_id: {result.get('channel_id') or 'n/a'}")
    print(f"playlist_count: {result.get('playlist_count') if result.get('playlist_count') is not None else 'n/a'}")
    if result.get("channel_name"):
        print(f"channel_name: {result['channel_name']}")
    for item in result.get("sources") or []:
        flag = "ok" if item.get("valid") else "fail"
        print(
            f"source: {item.get('source_id')} {flag} "
            f"tier={item.get('tier')} channel_id={item.get('channel_id') or 'n/a'}"
        )
    if not result["valid"]:
        if result.get("reason"):
            print(f"reason: {result['reason']}")
        if result.get("fix"):
            print(f"fix: {result['fix']}")


def write_external_candidates_stub(settings: Settings) -> None:
    path = settings.external_candidates_path
    path.parent.mkdir(parents=True, exist_ok=True)
    workspace = settings.workspace
    enabled = []
    disabled = []
    if workspace is not None:
        for source in workspace.youtube_sources:
            row = f"- `{source.id}` {source.display_handle} `{source.tier}` {source.url}"
            if source.enabled:
                enabled.append(row)
            else:
                disabled.append(row)
    lines = [
        "# External / PhD video candidates",
        "",
        "Channel list comes from [`config/workspace.yaml`](../../config/workspace.yaml).",
        "Enable a row (`enabled: true`) to catalog it. Disabled rows are **not** scraped.",
        "",
        "## Enabled this run",
        "",
        *(enabled or ["- (none — check workspace.yaml)"]),
        "",
        "## Disabled placeholders (`EXTERNAL_RESEARCH` until enabled)",
        "",
        *(disabled or ["- (none listed)"]),
        "",
        "Tag non-Dhan catalogs `EXTERNAL_RESEARCH`. Do not treat them as Dhan source",
        "material. Production indicator definitions remain Dhan-only while",
        f"`implementation.indicators` is `{settings.indicators_policy}`.",
        "",
        "This file is rewritten as a pointer stub. It is not a scrape of disabled channels.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def select_transcript_targets(
    videos: list[VideoRecord],
    cap: int,
    seed_ids: tuple[str, ...] = PLAN_SEED_VIDEO_IDS,
) -> list[VideoRecord]:
    by_id = {v.video_id: v for v in videos}
    selected: list[VideoRecord] = []
    seen: set[str] = set()

    def _take(video: VideoRecord) -> None:
        if video.video_id in seen:
            return
        if video.stock_tag == "EXCLUDED_STOCK_ONLY":
            return
        selected.append(video)
        seen.add(video.video_id)

    for seed in seed_ids:
        video = by_id.get(seed)
        if video:
            _take(video)

    eligible = [
        v
        for v in videos
        if v.stock_tag != "EXCLUDED_STOCK_ONLY"
    ]
    high = sorted(
        [v for v in eligible if v.relevance_band == "HIGH"],
        key=lambda v: v.popularity_rank or 10**9,
    )
    medium = sorted(
        [v for v in eligible if v.relevance_band == "MEDIUM"],
        key=lambda v: v.popularity_rank or 10**9,
    )
    for pool in (high, medium):
        for video in pool:
            if len(selected) >= cap:
                return selected
            _take(video)
    return selected[:cap]


def run_catalog(settings: Settings, client: YouTubeClient) -> tuple[list[VideoRecord], dict[str, Any]]:
    sources = _enabled_sources(settings)
    parts: list[dict[str, Any]] = []
    merged: list[VideoRecord] = []
    seen: set[str] = set()
    for source in sources:
        discovery = discover_channel(client, source)
        parts.append(catalog_meta_from_discovery(discovery))
        for video in discovery.videos:
            if video.video_id in seen:
                video.qa_flags = list(video.qa_flags) + ["DUPLICATE_VIDEO_ID"]
                continue
            seen.add(video.video_id)
            merged.append(video)
    videos = rank_videos(
        merged,
        w_views=settings.w_views,
        w_likes=settings.w_likes,
        w_comments=settings.w_comments,
        w_recency=settings.w_recency,
        half_life_days=settings.recency_half_life_days,
    )
    apply_relevance(videos)
    meta = merge_catalog_meta(parts)
    write_catalog(settings, videos, meta)
    write_external_candidates_stub(settings)
    return videos, meta


def run_transcripts(
    settings: Settings,
    videos: list[VideoRecord],
    cap: int,
) -> tuple[list[VideoRecord], dict[str, Any]]:
    hydrate_catalog_from_disk(
        videos, settings.raw_transcript_dir, settings.normalized_transcript_dir
    )
    targets = select_transcript_targets(videos, cap=cap)
    target_ids = {v.video_id for v in targets}
    for video in videos:
        if video.status == "TRANSCRIPT_PENDING" and video.video_id not in target_ids:
            video.status = "DISCOVERED"
    for video in targets:
        if video.status == "DISCOVERED":
            video.status = "TRANSCRIPT_PENDING"
    fetches, abort_reason = collect_many(
        targets,
        settings.raw_transcript_dir,
        settings.normalized_transcript_dir,
        pause_seconds=settings.transcript_pause_seconds,
    )
    stats = {
        "selected": len(targets),
        "selected_ids": [v.video_id for v in targets],
        "verified": sum(1 for f in fetches if f.status == STATUS_VERIFIED),
        "uncertain": sum(1 for f in fetches if f.status == STATUS_UNCERTAIN),
        "unavailable": sum(1 for f in fetches if f.status == STATUS_UNAVAILABLE),
        "abort_reason": abort_reason,
        "failures": [
            {"video_id": f.video_id, "reason": f.reason}
            for f in fetches
            if f.status == STATUS_UNAVAILABLE
        ],
    }
    return videos, stats


def _counts(videos: list[VideoRecord]) -> dict[str, int]:
    def n(pred) -> int:
        return sum(1 for v in videos if pred(v))

    return {
        "videos": len(videos),
        "high": n(lambda v: v.relevance_band == "HIGH"),
        "medium": n(lambda v: v.relevance_band == "MEDIUM"),
        "low": n(lambda v: v.relevance_band == "LOW"),
        "stock_only": n(lambda v: v.stock_tag == "STOCK_ONLY"),
        "excluded_stock_only": n(lambda v: v.stock_tag == "EXCLUDED_STOCK_ONLY"),
        "transcript_verified": n(lambda v: v.status == STATUS_VERIFIED),
        "transcript_uncertain": n(lambda v: v.status == STATUS_UNCERTAIN),
        "transcript_unavailable": n(lambda v: v.status == STATUS_UNAVAILABLE),
        "transcript_pending": n(lambda v: v.status == "TRANSCRIPT_PENDING"),
        "discovered": n(lambda v: v.status == "DISCOVERED"),
        "english_verified": n(lambda v: v.english_status == STATUS_ENGLISH_VERIFIED),
        "english_unavailable": n(
            lambda v: v.english_status == STATUS_ENGLISH_UNAVAILABLE
        ),
        "parked": n(lambda v: bool(v.parked_reason)),
    }


def write_run_report(
    settings: Settings,
    validation: dict[str, Any],
    videos: list[VideoRecord],
    meta: dict[str, Any],
    transcript_stats: Optional[dict[str, Any]],
    quota_units: int,
    transcript_cap: int,
    extra_notes: Optional[list[str]] = None,
) -> None:
    counts = _counts(videos)
    playlists = meta.get("playlists") or []
    named = [p for p in playlists if not p.get("is_uploads")]
    lines = [
        "# Stage 1 YouTube run report",
        "",
        f"Enabled sources (from `config/workspace.yaml`): {_sources_markdown(settings, meta)}.",
        "Disabled channels in that file were not scraped.",
        "No secrets. `YOUTUBE_API_KEY` is not recorded here.",
        "",
        "## Key validation",
        "",
        f"- Result: **{'valid' if validation.get('valid') else 'invalid'}**",
        f"- HTTP status: {validation.get('http_status')}",
        f"- Channel id: `{validation.get('channel_id') or 'n/a'}`",
        f"- Playlist count (playlists.list, not including uploads): "
        f"{validation.get('playlist_count') if validation.get('playlist_count') is not None else 'n/a'}",
        "",
        "## Discovery",
        "",
        f"- Channel name: {meta.get('channel_name') or validation.get('channel_name') or 'UNKNOWN'}",
        f"- Named playlists enumerated: {len(named)}",
        f"- Playlists including uploads playlist: {len(playlists)}",
        f"- Videos in catalog: {counts['videos']}",
        f"- Dropped playlist items (private/deleted/unavailable): "
        f"{len(meta.get('dropped_video_ids') or [])}",
        f"- YouTube Data API quota units used (approx, 1 unit/call): {quota_units}",
        "",
        "## Popularity and relevance",
        "",
        f"- Weights: views {settings.w_views}, likes {settings.w_likes}, "
        f"comments {settings.w_comments}, recency {settings.w_recency}",
        f"- Recency half-life (days): {settings.recency_half_life_days}",
        f"- HIGH: {counts['high']}",
        f"- MEDIUM: {counts['medium']}",
        f"- LOW: {counts['low']}",
        f"- STOCK_ONLY (kept): {counts['stock_only']}",
        f"- EXCLUDED_STOCK_ONLY (kept, not deleted): {counts['excluded_stock_only']}",
        "",
        "## Transcripts",
        "",
        f"- Cap this run: {transcript_cap} (HIGH then MEDIUM by popularity rank; "
        "PLAN seed videos included when present and not EXCLUDED_STOCK_ONLY)",
    ]
    if transcript_stats is None:
        lines.append("- Transcripts: not run in this invocation.")
    else:
        lines.extend(
            [
                f"- Selected: {transcript_stats.get('selected')}",
                f"- TRANSCRIPT_VERIFIED: {transcript_stats.get('verified')}",
                f"- SOURCE_UNCERTAIN (captions kept, QA flags): {transcript_stats.get('uncertain')}",
                f"- TRANSCRIPT_UNAVAILABLE: {transcript_stats.get('unavailable')}",
            ]
        )
        if transcript_stats.get("abort_reason"):
            lines.append(
                f"- Aborted remaining caption fetches: `{transcript_stats['abort_reason']}`"
            )
        failures = transcript_stats.get("failures") or []
        if failures:
            lines.append("")
            lines.append("### Caption failures")
            lines.append("")
            for item in failures:
                lines.append(
                    f"- `{item.get('video_id')}`: {item.get('reason') or 'UNKNOWN'}"
                )
        selected_ids = transcript_stats.get("selected_ids") or []
        if selected_ids:
            lines.append("")
            lines.append("### Selected video IDs")
            lines.append("")
            lines.append(", ".join(f"`{vid}`" for vid in selected_ids))
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- `{settings.catalog_csv.relative_to(settings.repo_root)}`",
            f"- `{settings.catalog_json.relative_to(settings.repo_root)}`",
            f"- `{settings.raw_transcript_dir.relative_to(settings.repo_root)}/<video_id>.json`",
            f"- `{settings.normalized_transcript_dir.relative_to(settings.repo_root)}/<video_id>.md`",
            f"- `{settings.external_candidates_path.relative_to(settings.repo_root)}` (stub only)",
            "",
            "## How to re-run",
            "",
            "From `teams/01_research/youtube` with the local venv activated:",
            "",
            "```bash",
            "python -m src validate-key",
            "python -m src catalog",
            "python -m src transcripts --cap 40",
            "python -m src retag",
            "python -m src run --cap 40",
            "```",
            "",
            "Optional env (repo-root `.env`): `YOUTUBE_TRANSCRIPT_CAP`, "
            "`YOUTUBE_POPULARITY_W_VIEWS` / `_LIKES` / `_COMMENTS` / `_RECENCY`, "
            "`YOUTUBE_RECENCY_HALF_LIFE_DAYS`, `YOUTUBE_REQUEST_PAUSE`, "
            "`YOUTUBE_TRANSCRIPT_PAUSE`.",
            "",
            "Relevance uses title + unique description (repeated Dhan app/social "
            "CTAs stripped) so catalog-wide footers do not mark every video HIGH.",
            "",
        ]
    )
    if extra_notes:
        lines.append("## Notes")
        lines.append("")
        for note in extra_notes:
            lines.append(f"- {note}")
        lines.append("")
    path = settings.run_report_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def cmd_validate_key(args: argparse.Namespace) -> int:
    settings = load_settings()
    result = validate_key(settings)
    print_validation(result)
    return 0 if result["valid"] else 2


def cmd_catalog(args: argparse.Namespace) -> int:
    settings = load_settings()
    validation = validate_key(settings)
    print_validation(validation)
    if not validation["valid"]:
        return 2
    client = YouTubeClient(
        settings.youtube_api_key, pause_seconds=settings.request_pause_seconds
    )
    try:
        videos, meta = run_catalog(settings, client)
        quota = client.quota_units_used + int(validation.get("quota_units_used") or 0)
        write_run_report(
            settings,
            validation,
            videos,
            meta,
            transcript_stats=None,
            quota_units=quota,
            transcript_cap=args.cap or settings.transcript_cap,
        )
    except YouTubeApiError as exc:
        print(
            f"catalog_failed: HTTP {exc.http_status} {exc.reason}. {_fix_hint(exc.reason, exc.http_status)}"
        )
        return 1
    finally:
        client.close()
    print(f"videos: {len(videos)}")
    print(f"playlists: {len(meta.get('playlists') or [])}")
    print(f"wrote: {settings.catalog_csv}")
    print(f"wrote: {settings.catalog_json}")
    return 0


def cmd_retag(args: argparse.Namespace) -> int:
    settings = load_settings()
    if not settings.catalog_csv.is_file():
        print("No catalog yet. Run: python -m src catalog")
        return 1
    videos = read_catalog_csv(settings.catalog_csv)
    meta = load_catalog_meta(settings.catalog_json)
    apply_relevance(videos)
    write_catalog(settings, videos, meta)
    counts = _counts(videos)
    print(f"videos: {counts['videos']}")
    print(f"HIGH: {counts['high']} MEDIUM: {counts['medium']} LOW: {counts['low']}")
    print(f"STOCK_ONLY: {counts['stock_only']}")
    print(f"EXCLUDED_STOCK_ONLY: {counts['excluded_stock_only']}")
    return 0


def probe_captions_list(settings: Settings, video_id: str) -> dict[str, Any]:
    """List caption tracks with API key; download requires OAuth (expect 401)."""
    client = YouTubeClient(
        settings.youtube_api_key, pause_seconds=settings.request_pause_seconds
    )
    try:
        data = client.captions_list(video_id)
        items = data.get("items") or []
        result: dict[str, Any] = {
            "ok": True,
            "http_status": 200,
            "reason": None,
            "item_count": len(items),
            "video_id": video_id,
            "tracks": [
                {
                    "language": (it.get("snippet") or {}).get("language"),
                    "trackKind": (it.get("snippet") or {}).get("trackKind"),
                }
                for it in items
            ],
            "download_http_status": None,
            "download_reason": None,
        }
        if items and items[0].get("id"):
            status, reason = client.captions_download(str(items[0]["id"]))
            result["download_http_status"] = status
            result["download_reason"] = reason
        return result
    except YouTubeApiError as exc:
        return {
            "ok": False,
            "http_status": exc.http_status,
            "reason": exc.reason,
            "item_count": None,
            "video_id": video_id,
            "message": sanitize(exc.message, settings.youtube_api_key),
        }
    finally:
        client.close()


def write_followup_report(
    settings: Settings,
    videos: list[VideoRecord],
    meta: dict[str, Any],
    *,
    parked: list[VideoRecord],
    retry_stats: Optional[dict[str, Any]],
    english_stats: Optional[dict[str, Any]],
    captions_probe: Optional[dict[str, Any]],
    extra_notes: Optional[list[str]] = None,
) -> None:
    counts = _counts(videos)
    playlists = meta.get("playlists") or []
    named = [p for p in playlists if not p.get("is_uploads")]
    lines = [
        "# Stage 1 YouTube run report",
        "",
        f"Enabled sources (from `config/workspace.yaml`): {_sources_markdown(settings, meta)}.",
        "Disabled channels in that file were not scraped.",
        "No secrets. `YOUTUBE_API_KEY` is not recorded here.",
        "",
        "## Key validation",
        "",
        "- Result: **valid** (prior catalog run; this follow-up did not re-validate)",
        f"- Channel id: `{meta.get('channel_id') or 'n/a'}`",
        f"- Channel name: {meta.get('channel_name') or 'UNKNOWN'}",
        f"- Playlist count (playlists.list, not including uploads): {len(named)}",
        "",
        "## Discovery (unchanged; catalog was not re-fetched)",
        "",
        f"- Named playlists enumerated: {len(named)}",
        f"- Playlists including uploads playlist: {len(playlists)}",
        f"- Videos in catalog: {counts['videos']}",
        "",
        "## Popularity and relevance",
        "",
        f"- HIGH: {counts['high']}",
        f"- MEDIUM: {counts['medium']}",
        f"- LOW: {counts['low']}",
        f"- STOCK_ONLY (kept): {counts['stock_only']}",
        f"- EXCLUDED_STOCK_ONLY (kept, not deleted): {counts['excluded_stock_only']}",
        "",
        "## Why timedtext was blocked",
        "",
        "Public captions are **not** downloaded via YouTube Data API v3. "
        "`captions.list` and `captions.download` require OAuth 2.0 scoped to the "
        "**owning channel**. An API key cannot download caption text for a channel "
        "this project does not own. "
        "This extractor uses `youtube-transcript-api`, which reads the watch page "
        "+ Innertube player JSON, then GETs the timedtext URL (optional `tlang=en` "
        "for YouTube auto-translate).",
        "",
        "After a burst of successful fetches, YouTube started returning **429** "
        "(`IpBlocked`) and/or Innertube playability `LOGIN_REQUIRED` with reason "
        '"Sign in to confirm you’re not a bot" (`RequestBlocked`). That is bot '
        "detection / IP rate-limiting on timedtext — **not** Data API quota "
        "(~115 units on the catalog run). Cloud IPs are especially likely to be "
        "blocked; a residential IP can still be blocked after too many requests "
        "without delay.",
        "",
        "Mitigations in this follow-up (no third-party transcript sites, no proxies):",
        "",
        "- Browser-like `User-Agent` + `Accept-Language` on the timedtext session",
        "- Pause between videos (`YOUTUBE_TRANSCRIPT_RETRY_PAUSE`, default 4s)",
        "- Exponential backoff on 429 / RequestBlocked "
        "(`YOUTUBE_TRANSCRIPT_BACKOFF`, default 20s, 3 attempts)",
        "- Extra cooldown after a blocked video before the next ID",
        "- Stop after 3 consecutive blocks so we do not hammer the endpoint",
        "",
    ]
    if captions_probe:
        lines.extend(
            [
                "### Data API captions.list / captions.download probe",
                "",
                f"- video_id: `{captions_probe.get('video_id')}`",
                f"- captions.list HTTP status: {captions_probe.get('http_status')}",
                f"- captions.list reason: {captions_probe.get('reason') or 'n/a'}",
                f"- tracks listed: {captions_probe.get('item_count')}",
                f"- track languages: {captions_probe.get('tracks') or []}",
                f"- captions.download HTTP status: {captions_probe.get('download_http_status')}",
                f"- captions.download reason: {captions_probe.get('download_reason') or 'n/a'}",
                "- Interpretation: `captions.list` **can** succeed with an API key "
                "(track metadata only). `captions.download` returns **401** "
                "(`API keys are not supported` / OAuth required) and would still "
                "be limited to videos this project owns. English text is taken "
                "from timedtext / `tlang=en`, not `captions.download`.",
                "",
            ]
        )
        if captions_probe.get("message"):
            lines.append(
                f"- sanitized message: {captions_probe['message']}"
            )
            lines.append("")
    lines.extend(
        [
            "## Parked for tomorrow",
            "",
            "Pending + IP-blocked IDs that are **not** Phase-1 F&O strategy "
            "(options / index / strategy / indicators / price action / Dhan tools "
            "for F&O) were parked. Catalog rows were not deleted.",
            "",
            f"- Parked count: {len(parked)}",
            f"- Folder: `{settings.parked_tomorrow_dir.relative_to(settings.repo_root)}/`",
            "",
        ]
    )
    if parked:
        lines.append("| video_id | title | status | reason |")
        lines.append("|---|---|---|---|")
        for video in parked:
            title = (video.title or "").replace("|", "/")
            lines.append(
                f"| `{video.video_id}` | {title} | {video.status} | "
                f"{video.parked_reason or ''} |"
            )
        lines.append("")
    if retry_stats is None:
        lines.append("- Retry: not run in this invocation.")
        lines.append("")
    else:
        lines.extend(
            [
                "## Retry (related pending + IP-blocked)",
                "",
                f"- Retry targets: {retry_stats.get('selected')}",
                f"- TRANSCRIPT_VERIFIED this retry: {retry_stats.get('verified')}",
                f"- TRANSCRIPT_UNAVAILABLE this retry: {retry_stats.get('unavailable')}",
                f"- Still pending after retry: {retry_stats.get('still_pending')}",
            ]
        )
        if retry_stats.get("abort_reason"):
            lines.append(
                f"- Aborted remaining caption fetches: `{retry_stats['abort_reason']}`"
            )
        failures = retry_stats.get("failures") or []
        if failures:
            lines.append("")
            lines.append("### Retry failures")
            lines.append("")
            for item in failures:
                lines.append(
                    f"- `{item.get('video_id')}`: {item.get('reason') or 'UNKNOWN'}"
                )
        selected_ids = retry_stats.get("selected_ids") or []
        if selected_ids:
            lines.append("")
            lines.append("### Retry video IDs")
            lines.append("")
            lines.append(", ".join(f"`{vid}`" for vid in selected_ids))
        lines.append("")
    if english_stats is None:
        lines.extend(["## English captions", "", "- English pass: not run.", ""])
    else:
        lines.extend(
            [
                "## English captions",
                "",
                "Hindi `SOURCE_FACT` files were left intact. English companions "
                "were fetched from YouTube only (manual English track if listed, "
                "else generated English, else `transcript.translate('en')` which "
                "appends `tlang=en`). **No LLM translation.**",
                "",
                f"- Targets considered: {english_stats.get('selected')}",
                f"- ENGLISH_VERIFIED: {english_stats.get('verified')}",
                f"- ENGLISH_UNAVAILABLE: {english_stats.get('unavailable')}",
                f"- Native English copied (no extra timedtext): "
                f"{english_stats.get('native_copied')}",
                f"- YouTube translate (`tlang=en`): {english_stats.get('youtube_translate')}",
                f"- Manual English track: {english_stats.get('manual')}",
                f"- Generated English track: {english_stats.get('generated')}",
            ]
        )
        if english_stats.get("abort_reason"):
            lines.append(
                f"- Aborted remaining English fetches: `{english_stats['abort_reason']}`"
            )
        en_fail = english_stats.get("failures") or []
        if en_fail:
            lines.append("")
            lines.append("### English failures / unavailable")
            lines.append("")
            for item in en_fail:
                lines.append(
                    f"- `{item.get('video_id')}`: {item.get('reason') or 'UNKNOWN'}"
                )
        lines.extend(
            [
                "",
                "### English file paths",
                "",
                f"- `{settings.raw_transcript_dir.relative_to(settings.repo_root)}/<video_id>.en.json`",
                f"- `{settings.normalized_en_dir.relative_to(settings.repo_root)}/<video_id>.md`",
                "",
            ]
        )
    lines.extend(
        [
            "## Catalog counts after this follow-up",
            "",
            f"- TRANSCRIPT_VERIFIED: {counts['transcript_verified']}",
            f"- TRANSCRIPT_UNAVAILABLE: {counts['transcript_unavailable']}",
            f"- TRANSCRIPT_PENDING: {counts['transcript_pending']}",
            f"- ENGLISH_VERIFIED: {counts['english_verified']}",
            f"- ENGLISH_UNAVAILABLE: {counts['english_unavailable']}",
            f"- Parked (reason set, rows kept): {counts['parked']}",
            "",
            "## Outputs",
            "",
            f"- `{settings.catalog_csv.relative_to(settings.repo_root)}`",
            f"- `{settings.catalog_json.relative_to(settings.repo_root)}`",
            f"- `{settings.raw_transcript_dir.relative_to(settings.repo_root)}/<video_id>.json` (source language)",
            f"- `{settings.raw_transcript_dir.relative_to(settings.repo_root)}/<video_id>.en.json` (English companion)",
            f"- `{settings.normalized_transcript_dir.relative_to(settings.repo_root)}/<video_id>.md`",
            f"- `{settings.normalized_en_dir.relative_to(settings.repo_root)}/<video_id>.md`",
            f"- `{settings.parked_tomorrow_dir.relative_to(settings.repo_root)}/`",
            "",
            "## How to re-run",
            "",
            "From `teams/01_research/youtube` with the local venv activated:",
            "",
            "```bash",
            "python -m src transcripts --retry-pending --english",
            "python -m src transcripts --english --english-cap 40",
            "```",
            "",
            "Optional env (repo-root `.env`): `YOUTUBE_TRANSCRIPT_PAUSE`, "
            "`YOUTUBE_TRANSCRIPT_RETRY_PAUSE`, `YOUTUBE_TRANSCRIPT_BACKOFF`, "
            "`YOUTUBE_TRANSCRIPT_BACKOFF_ATTEMPTS`.",
            "",
        ]
    )
    if extra_notes:
        lines.append("## Notes")
        lines.append("")
        for note in extra_notes:
            lines.append(f"- {note}")
        lines.append("")
    path = settings.run_report_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def cmd_transcripts(args: argparse.Namespace) -> int:
    settings = load_settings()
    if not settings.catalog_csv.is_file():
        print("No catalog yet. Run: python -m src catalog")
        return 1
    videos = read_catalog_csv(settings.catalog_csv)
    apply_relevance(videos)
    meta = load_catalog_meta(settings.catalog_json)
    followup = bool(args.retry_pending or args.english)
    if not followup:
        cap = args.cap or settings.transcript_cap
        videos, stats = run_transcripts(settings, videos, cap=cap)
        write_catalog(settings, videos, meta)
        write_run_report(
            settings,
            {
                "valid": True,
                "http_status": "n/a (transcripts skip Data API)",
                "channel_id": meta.get("channel_id"),
                "playlist_count": len(
                    [p for p in (meta.get("playlists") or []) if not p.get("is_uploads")]
                ),
            },
            videos,
            meta,
            transcript_stats=stats,
            quota_units=0,
            transcript_cap=cap,
        )
        print(f"selected: {stats['selected']}")
        print(f"verified: {stats['verified']}")
        print(f"uncertain: {stats['uncertain']}")
        print(f"unavailable: {stats['unavailable']}")
        if stats.get("abort_reason"):
            print(f"abort: {stats['abort_reason']}")
        return 0

    hydrate_catalog_from_disk(
        videos, settings.raw_transcript_dir, settings.normalized_transcript_dir
    )
    hydrate_english_from_disk(videos, settings.raw_transcript_dir)

    parked: list[VideoRecord] = []
    retry_stats: Optional[dict[str, Any]] = None
    english_stats: Optional[dict[str, Any]] = None
    captions_probe: Optional[dict[str, Any]] = None

    if args.retry_pending:
        queue = audit_queue(videos)
        keep, parked = split_park(queue)
        write_parked_folder(settings.parked_tomorrow_dir, parked)
        print(f"parked: {len(parked)}")
        print(f"retry_keep: {len(keep)}")
        fetches, abort_reason = collect_many(
            keep,
            settings.raw_transcript_dir,
            settings.normalized_transcript_dir,
            pause_seconds=settings.transcript_retry_pause_seconds,
            retry_blocked=True,
            backoff_attempts=settings.transcript_backoff_attempts,
            backoff_seconds=settings.transcript_backoff_seconds,
        )
        still_pending = sum(1 for v in keep if v.status == "TRANSCRIPT_PENDING")
        retry_stats = {
            "selected": len(keep),
            "selected_ids": [v.video_id for v in keep],
            "verified": sum(1 for f in fetches if f.status == STATUS_VERIFIED),
            "unavailable": sum(1 for f in fetches if f.status == STATUS_UNAVAILABLE),
            "still_pending": still_pending,
            "abort_reason": abort_reason,
            "failures": [
                {"video_id": f.video_id, "reason": f.reason}
                for f in fetches
                if f.status == STATUS_UNAVAILABLE
            ],
        }
        print(f"retry_verified: {retry_stats['verified']}")
        print(f"retry_unavailable: {retry_stats['unavailable']}")
        if abort_reason:
            print(f"retry_abort: {abort_reason}")

    if args.english:
        probe_id = next(
            (
                v.video_id
                for v in videos
                if v.status == STATUS_VERIFIED and v.transcript_language == "hi"
            ),
            "HAUSZx-hYdY",
        )
        captions_probe = probe_captions_list(settings, probe_id)
        print(
            f"captions_list_probe: HTTP {captions_probe.get('http_status')} "
            f"{captions_probe.get('reason') or 'ok'}"
        )
        targets = select_english_targets(videos, settings.raw_transcript_dir)
        cap = args.english_cap if args.english_cap is not None else 50
        fetches, abort_reason = collect_english_many(
            targets,
            settings.raw_transcript_dir,
            settings.normalized_en_dir,
            pause_seconds=settings.transcript_retry_pause_seconds,
            backoff_attempts=settings.transcript_backoff_attempts,
            backoff_seconds=settings.transcript_backoff_seconds,
            cap=cap,
        )
        english_stats = {
            "selected": min(len(targets), cap),
            "verified": sum(
                1 for f in fetches if f.english_status == STATUS_ENGLISH_VERIFIED
            ),
            "unavailable": sum(
                1 for f in fetches if f.english_status == STATUS_ENGLISH_UNAVAILABLE
            ),
            "native_copied": sum(
                1
                for f in fetches
                if f.translation_source in ("manual", "generated")
                and f.english_status == STATUS_ENGLISH_VERIFIED
                and (f.source_language or "").startswith("en")
            ),
            "youtube_translate": sum(
                1 for f in fetches if f.translation_source == "youtube_translate"
            ),
            "manual": sum(1 for f in fetches if f.translation_source == "manual"),
            "generated": sum(1 for f in fetches if f.translation_source == "generated"),
            "abort_reason": abort_reason,
            "failures": [
                {"video_id": f.video_id, "reason": f.reason}
                for f in fetches
                if f.english_status == STATUS_ENGLISH_UNAVAILABLE
            ],
        }
        print(f"english_verified: {english_stats['verified']}")
        print(f"english_unavailable: {english_stats['unavailable']}")
        if abort_reason:
            print(f"english_abort: {abort_reason}")

    write_catalog(settings, videos, meta)
    write_followup_report(
        settings,
        videos,
        meta,
        parked=parked,
        retry_stats=retry_stats,
        english_stats=english_stats,
        captions_probe=captions_probe,
    )
    print(f"report: {settings.run_report_path}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    settings = load_settings()
    cap = args.cap or settings.transcript_cap
    validation = validate_key(settings)
    print_validation(validation)
    if not validation["valid"]:
        write_run_report(
            settings,
            validation,
            [],
            {},
            transcript_stats=None,
            quota_units=int(validation.get("quota_units_used") or 0),
            transcript_cap=cap,
            extra_notes=["Stopped before discovery because the API key did not validate."],
        )
        return 2

    client = YouTubeClient(
        settings.youtube_api_key, pause_seconds=settings.request_pause_seconds
    )
    try:
        videos, meta = run_catalog(settings, client)
        quota = client.quota_units_used + int(validation.get("quota_units_used") or 0)
        print(f"videos: {len(videos)}")
        print(f"playlists: {len(meta.get('playlists') or [])}")
        videos, stats = run_transcripts(settings, videos, cap=cap)
        write_catalog(settings, videos, meta)
        write_run_report(
            settings,
            validation,
            videos,
            meta,
            transcript_stats=stats,
            quota_units=quota,
            transcript_cap=cap,
        )
        print(f"transcripts_selected: {stats['selected']}")
        print(f"transcripts_verified: {stats['verified']}")
        print(f"transcripts_uncertain: {stats['uncertain']}")
        print(f"transcripts_unavailable: {stats['unavailable']}")
        if stats.get("abort_reason"):
            print(f"abort: {stats['abort_reason']}")
        print(f"report: {settings.run_report_path}")
    except YouTubeApiError as exc:
        print(
            f"run_failed: HTTP {exc.http_status} {exc.reason}. {_fix_hint(exc.reason, exc.http_status)}"
        )
        return 1
    finally:
        client.close()
    return 0


def cmd_show_config(args: argparse.Namespace) -> int:
    settings = load_settings(require_youtube_key=False)
    workspace = settings.workspace
    print(f"workspace: {workspace.path}")
    if workspace.overlay_path:
        print(f"overlay: {workspace.overlay_path} (gitignored)")
    else:
        print("overlay: none")
    print(f"implementation.broker: {settings.implementation_broker}")
    print(f"implementation.indicators: {settings.indicators_policy}")
    markets = [m.id for m in workspace.markets if m.enabled]
    print(f"markets: {', '.join(markets) or '(none)'}")
    print("youtube:")
    for source in workspace.youtube_sources:
        flag = "enabled" if source.enabled else "disabled"
        print(
            f"  - {source.id} @{source.handle} {flag} {source.tier} {source.origin_tag} {source.url}"
        )
    print("books:")
    for book in workspace.books:
        flag = "enabled" if book.enabled else "disabled"
        print(f"  - {book.id} [{book.use}] {flag} {book.title}")
        if book.url:
            print(f"    {book.url}")
    print("pipeline:")
    print(f"  catalog_csv: {settings.catalog_csv_rel}")
    print(f"  transcripts_raw: {settings.raw_transcript_rel}")
    print(f"  english: {settings.normalized_en_rel}")
    print(f"  strategy_docs: {settings.strategy_docs_rel}")
    print("agent_routing:")
    for step, team in (workspace.agent_routing or {}).items():
        print(f"  {step}: {team}")
    print("secrets_from_env (names only; values not printed):")
    for logical, env_name in workspace.secrets_from_env.items():
        state = "set" if workspace.secret_present(env_name) else "missing"
        print(f"  {logical}: {env_name} ({state})")
    return 0


def cmd_topics(args: argparse.Namespace) -> int:
    settings = load_settings(require_youtube_key=False)
    if not settings.catalog_csv.is_file():
        print("No catalog yet. Run: python -m src catalog")
        return 1
    videos = read_catalog_csv(settings.catalog_csv)
    apply_relevance(videos)
    stats = run_topic_cluster(settings, videos)
    print(f"topics: {stats['topics']}")
    print(f"wrote: {stats['output_dir']}")
    for topic_id, action in (stats.get("actions") or {}).items():
        print(f"  {topic_id}: {action}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage 1 YouTube catalog and public captions (channels from config/workspace.yaml)."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-key", help="Check YOUTUBE_API_KEY against Data API v3.")

    def add_cap(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--cap",
            type=int,
            default=None,
            help="Transcript cap (default: YOUTUBE_TRANSCRIPT_CAP or 40).",
        )

    p_catalog = sub.add_parser(
        "catalog", help="Discover playlists, rank, relevance-tag, write catalog."
    )
    add_cap(p_catalog)
    p_transcripts = sub.add_parser(
        "transcripts",
        help="Fetch public captions for the popular HIGH/MEDIUM set.",
    )
    add_cap(p_transcripts)
    p_transcripts.add_argument(
        "--retry-pending",
        action="store_true",
        help="Park unrelated pending/blocked IDs; retry related ones with backoff.",
    )
    p_transcripts.add_argument(
        "--english",
        action="store_true",
        help="Fetch YouTube English (native track or tlang=en). No LLM translation.",
    )
    p_transcripts.add_argument(
        "--english-cap",
        type=int,
        default=None,
        help="Max English companion fetches (default 50).",
    )
    p_run = sub.add_parser("run", help="validate-key + catalog + transcripts.")
    add_cap(p_run)
    sub.add_parser(
        "retag",
        help="Re-apply relevance tags on an existing catalog (no Data API calls).",
    )
    sub.add_parser(
        "show-config",
        help="Print enabled channels/books/paths from config/workspace.yaml (no API, no secrets).",
    )
    sub.add_parser(
        "topics",
        help="Cluster catalog into per-topic stub docs (no scrape). UNVALIDATED.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    _configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    commands = {
        "validate-key": cmd_validate_key,
        "catalog": cmd_catalog,
        "transcripts": cmd_transcripts,
        "run": cmd_run,
        "retag": cmd_retag,
        "show-config": cmd_show_config,
        "topics": cmd_topics,
    }
    try:
        return commands[args.command](args)
    except (FileNotFoundError, ValueError) as exc:
        print(sanitize(str(exc)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
