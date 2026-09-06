"""Read/write video_catalog.csv and video_catalog.json."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Optional

from .config import CHANNEL_HANDLE, PLAYLISTS_URL, Settings
from .discovery import DiscoveryResult, VideoRecord, utc_now_iso

CSV_FIELDS = [
    "video_id",
    "title",
    "url",
    "published_at",
    "duration_seconds",
    "view_count",
    "like_count",
    "comment_count",
    "channel_id",
    "channel_name",
    "playlist_ids",
    "description",
    "caption_available",
    "language",
    "retrieved_at",
    "thumbnail_url",
    "popularity_score",
    "popularity_rank",
    "relevance_band",
    "stock_tag",
    "topic_tags",
    "topic_source",
    "status",
    "qa_flags",
    "transcript_language",
    "transcript_generated",
    "english_status",
    "english_source",
    "parked_reason",
    "source_id",
    "source_tier",
    "origin_tag",
]


def _join(values: Optional[list[str]]) -> str:
    if not values:
        return ""
    return "|".join(values)


def _split(raw: str) -> list[str]:
    if not raw:
        return []
    return [part for part in raw.split("|") if part]


def _bool_to_csv(value: Optional[bool]) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


def _csv_to_bool(raw: str) -> Optional[bool]:
    if raw == "":
        return None
    if raw.lower() in ("true", "1", "yes"):
        return True
    if raw.lower() in ("false", "0", "no"):
        return False
    return None


def _opt_int(raw: str) -> Optional[int]:
    if raw == "":
        return None
    return int(float(raw))


def _opt_float(raw: str) -> Optional[float]:
    if raw == "":
        return None
    return float(raw)


def video_to_row(video: VideoRecord) -> dict[str, Any]:
    return {
        "video_id": video.video_id,
        "title": video.title,
        "url": video.url,
        "published_at": video.published_at or "",
        "duration_seconds": video.duration_seconds if video.duration_seconds is not None else "",
        "view_count": video.view_count if video.view_count is not None else "",
        "like_count": video.like_count if video.like_count is not None else "",
        "comment_count": video.comment_count if video.comment_count is not None else "",
        "channel_id": video.channel_id,
        "channel_name": video.channel_name,
        "playlist_ids": _join(video.playlist_ids),
        "description": video.description,
        "caption_available": _bool_to_csv(video.caption_available),
        "language": video.language or "",
        "retrieved_at": video.retrieved_at,
        "thumbnail_url": video.thumbnail_url or "",
        "popularity_score": video.popularity_score if video.popularity_score is not None else "",
        "popularity_rank": video.popularity_rank if video.popularity_rank is not None else "",
        "relevance_band": video.relevance_band or "",
        "stock_tag": video.stock_tag or "",
        "topic_tags": _join(video.topic_tags),
        "topic_source": video.topic_source,
        "status": video.status,
        "qa_flags": _join(video.qa_flags),
        "transcript_language": video.transcript_language or "",
        "transcript_generated": _bool_to_csv(video.transcript_generated),
        "english_status": video.english_status or "",
        "english_source": video.english_source or "",
        "parked_reason": video.parked_reason or "",
        "source_id": video.source_id or "",
        "source_tier": video.source_tier or "",
        "origin_tag": video.origin_tag or "",
    }


def video_to_json(video: VideoRecord) -> dict[str, Any]:
    return {
        "video_id": video.video_id,
        "title": video.title,
        "url": video.url,
        "published_at": video.published_at,
        "duration_seconds": video.duration_seconds,
        "view_count": video.view_count,
        "like_count": video.like_count,
        "comment_count": video.comment_count,
        "channel_id": video.channel_id,
        "channel_name": video.channel_name,
        "playlist_ids": video.playlist_ids,
        "description": video.description,
        "caption_available": video.caption_available,
        "language": video.language,
        "retrieved_at": video.retrieved_at,
        "thumbnail_url": video.thumbnail_url,
        "popularity_score": video.popularity_score,
        "popularity_rank": video.popularity_rank,
        "relevance_band": video.relevance_band,
        "stock_tag": video.stock_tag,
        "topic_tags": video.topic_tags,
        "topic_source": video.topic_source,
        "status": video.status,
        "qa_flags": video.qa_flags,
        "transcript_language": video.transcript_language,
        "transcript_generated": video.transcript_generated,
        "english_status": video.english_status,
        "english_source": video.english_source,
        "parked_reason": video.parked_reason,
        "source_id": video.source_id or None,
        "source_tier": video.source_tier or None,
        "origin_tag": video.origin_tag or None,
    }


def row_to_video(row: dict[str, str]) -> VideoRecord:
    return VideoRecord(
        video_id=row.get("video_id") or "",
        title=row.get("title") or "",
        url=row.get("url") or "",
        published_at=row.get("published_at") or None,
        duration_seconds=_opt_int(row.get("duration_seconds") or ""),
        view_count=_opt_int(row.get("view_count") or ""),
        like_count=_opt_int(row.get("like_count") or ""),
        comment_count=_opt_int(row.get("comment_count") or ""),
        channel_id=row.get("channel_id") or "",
        channel_name=row.get("channel_name") or "",
        playlist_ids=_split(row.get("playlist_ids") or ""),
        description=row.get("description") or "",
        caption_available=_csv_to_bool(row.get("caption_available") or ""),
        language=row.get("language") or None,
        retrieved_at=row.get("retrieved_at") or "",
        thumbnail_url=row.get("thumbnail_url") or None,
        popularity_score=_opt_float(row.get("popularity_score") or ""),
        popularity_rank=_opt_int(row.get("popularity_rank") or ""),
        relevance_band=row.get("relevance_band") or None,
        stock_tag=row.get("stock_tag") or None,
        topic_tags=_split(row.get("topic_tags") or ""),
        topic_source=row.get("topic_source") or "METADATA",
        status=row.get("status") or "DISCOVERED",
        qa_flags=_split(row.get("qa_flags") or ""),
        transcript_language=row.get("transcript_language") or None,
        transcript_generated=_csv_to_bool(row.get("transcript_generated") or ""),
        english_status=row.get("english_status") or None,
        english_source=row.get("english_source") or None,
        parked_reason=row.get("parked_reason") or None,
        source_id=row.get("source_id") or "dhanhq",
        source_tier=row.get("source_tier") or "TIER_1",
        origin_tag=row.get("origin_tag") or "DHAN-DERIVED",
    )


def write_catalog(
    settings: Settings,
    videos: list[VideoRecord],
    meta: Optional[dict[str, Any]] = None,
) -> None:
    settings.catalog_csv.parent.mkdir(parents=True, exist_ok=True)
    with settings.catalog_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for video in videos:
            writer.writerow(video_to_row(video))

    document = {
        "retrieved_at": (meta or {}).get("retrieved_at") or utc_now_iso(),
        "channel_handle": (meta or {}).get("channel_handle") or CHANNEL_HANDLE,
        "channel_id": (meta or {}).get("channel_id"),
        "channel_name": (meta or {}).get("channel_name"),
        "source": (meta or {}).get("source") or PLAYLISTS_URL,
        "sources": (meta or {}).get("sources") or [],
        "video_count": len(videos),
        "playlists": (meta or {}).get("playlists") or [],
        "videos": [video_to_json(v) for v in videos],
    }
    settings.catalog_json.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_catalog_csv(path: Path) -> list[VideoRecord]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [row_to_video(row) for row in reader]


def catalog_meta_from_discovery(result: DiscoveryResult) -> dict[str, Any]:
    source_entry = {
        "id": result.source_id or result.channel_handle,
        "handle": result.channel_handle,
        "channel_id": result.channel_id,
        "channel_name": result.channel_name,
        "source": result.source,
        "tier": result.source_tier,
        "origin_tag": result.origin_tag,
        "uploads_playlist_id": result.uploads_playlist_id,
    }
    return {
        "retrieved_at": result.retrieved_at,
        "channel_handle": result.channel_handle,
        "channel_id": result.channel_id,
        "channel_name": result.channel_name,
        "source": result.source,
        "sources": [source_entry],
        "playlists": [
            {
                "playlist_id": p.playlist_id,
                "title": p.title,
                "item_count": p.item_count,
                "is_uploads": p.is_uploads,
                "source_id": p.source_id or result.source_id,
            }
            for p in result.playlists
        ],
        "dropped_video_ids": result.dropped_video_ids,
        "uploads_playlist_id": result.uploads_playlist_id,
    }


def merge_catalog_meta(parts: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine per-source discovery meta into one catalog document."""
    if not parts:
        return {}
    if len(parts) == 1:
        return parts[0]
    primary = parts[0]
    playlists: list[dict[str, Any]] = []
    dropped: list[str] = []
    sources: list[dict[str, Any]] = []
    for part in parts:
        playlists.extend(part.get("playlists") or [])
        dropped.extend(part.get("dropped_video_ids") or [])
        sources.extend(part.get("sources") or [])
    return {
        "retrieved_at": primary.get("retrieved_at") or utc_now_iso(),
        "channel_handle": primary.get("channel_handle") or CHANNEL_HANDLE,
        "channel_id": primary.get("channel_id"),
        "channel_name": primary.get("channel_name"),
        "source": primary.get("source") or PLAYLISTS_URL,
        "sources": sources,
        "playlists": playlists,
        "dropped_video_ids": dropped,
        "uploads_playlist_id": primary.get("uploads_playlist_id"),
    }


def load_catalog_meta(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("videos", None)
    return data
