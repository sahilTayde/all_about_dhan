"""Playlist + video catalog discovery for enabled workspace.yaml channels."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .config import CHANNEL_HANDLE, CHANNEL_URL, PLAYLISTS_URL
from .youtube_client import YouTubeApiError, YouTubeClient

log = logging.getLogger(__name__)

_ISO_DURATION = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso_duration_seconds(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    match = _ISO_DURATION.match(value)
    if not match:
        return None
    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _int_or_none(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _thumbnail_url(snippet: dict[str, Any]) -> Optional[str]:
    thumbs = snippet.get("thumbnails") or {}
    for key in ("maxres", "standard", "high", "medium", "default"):
        node = thumbs.get(key)
        if isinstance(node, dict) and node.get("url"):
            return str(node["url"])
    return None


@dataclass
class PlaylistInfo:
    playlist_id: str
    title: str
    item_count: Optional[int]
    is_uploads: bool = False
    source_id: str = ""


@dataclass
class VideoRecord:
    video_id: str
    title: str
    url: str
    published_at: Optional[str]
    duration_seconds: Optional[int]
    view_count: Optional[int]
    like_count: Optional[int]
    comment_count: Optional[int]
    channel_id: str
    channel_name: str
    playlist_ids: list[str] = field(default_factory=list)
    description: str = ""
    caption_available: Optional[bool] = None
    language: Optional[str] = None
    retrieved_at: str = ""
    thumbnail_url: Optional[str] = None
    popularity_score: Optional[float] = None
    popularity_rank: Optional[int] = None
    relevance_band: Optional[str] = None
    stock_tag: Optional[str] = None
    topic_tags: list[str] = field(default_factory=list)
    topic_source: str = "METADATA"
    status: str = "DISCOVERED"
    qa_flags: list[str] = field(default_factory=list)
    transcript_language: Optional[str] = None
    transcript_generated: Optional[bool] = None
    english_status: Optional[str] = None
    english_source: Optional[str] = None
    parked_reason: Optional[str] = None
    source_id: str = ""
    source_tier: str = ""
    origin_tag: str = ""


@dataclass
class DiscoveryResult:
    channel_id: str
    channel_name: str
    channel_handle: str
    uploads_playlist_id: Optional[str]
    playlists: list[PlaylistInfo]
    videos: list[VideoRecord]
    dropped_video_ids: list[str]
    retrieved_at: str
    source: str = PLAYLISTS_URL
    source_id: str = ""
    source_tier: str = ""
    origin_tag: str = ""


def _video_id_from_playlist_item(item: dict[str, Any]) -> Optional[str]:
    content = item.get("contentDetails") or {}
    vid = content.get("videoId")
    if vid:
        return str(vid)
    snippet = item.get("snippet") or {}
    resource = snippet.get("resourceId") or {}
    vid = resource.get("videoId")
    return str(vid) if vid else None


def discover_channel(client: YouTubeClient, source=None) -> DiscoveryResult:
    """Enumerate public playlists plus uploads for one workspace.yaml source."""
    if source is None:
        handle = CHANNEL_HANDLE
        source_id = "dhanhq"
        source_url = CHANNEL_URL
        playlists_url = PLAYLISTS_URL
        tier = "TIER_1"
        origin_tag = "DHAN-DERIVED"
    else:
        handle = source.handle
        source_id = source.id
        source_url = source.url
        playlists_url = source.playlists_url or source.url
        tier = source.tier
        origin_tag = source.origin_tag

    retrieved_at = utc_now_iso()
    channel = client.channels_by_handle(handle)
    channel_id = channel["id"]
    snippet = channel.get("snippet") or {}
    channel_name = snippet.get("title") or handle
    content = channel.get("contentDetails") or {}
    related = content.get("relatedPlaylists") or {}
    uploads_id = related.get("uploads")

    named = client.list_playlists(channel_id)
    playlists: list[PlaylistInfo] = []
    seen_playlist_ids: set[str] = set()
    for raw in named:
        pid = raw.get("id")
        if not pid:
            continue
        seen_playlist_ids.add(pid)
        p_snip = raw.get("snippet") or {}
        p_content = raw.get("contentDetails") or {}
        playlists.append(
            PlaylistInfo(
                playlist_id=pid,
                title=p_snip.get("title") or pid,
                item_count=_int_or_none(p_content.get("itemCount")),
                is_uploads=False,
                source_id=source_id,
            )
        )

    if uploads_id and uploads_id not in seen_playlist_ids:
        playlists.append(
            PlaylistInfo(
                playlist_id=uploads_id,
                title="Uploads",
                item_count=None,
                is_uploads=True,
                source_id=source_id,
            )
        )
        seen_playlist_ids.add(uploads_id)

    membership: dict[str, set[str]] = {}
    for plist in playlists:
        log.info(
            "Listing playlist %s (%s) source=%s",
            plist.playlist_id,
            plist.title,
            source_id,
        )
        try:
            items = client.list_playlist_items(plist.playlist_id)
        except YouTubeApiError as exc:
            log.warning(
                "Skipping playlist %s: HTTP %s %s",
                plist.playlist_id,
                exc.http_status,
                exc.reason,
            )
            continue
        for item in items:
            vid = _video_id_from_playlist_item(item)
            if not vid:
                continue
            membership.setdefault(vid, set()).add(plist.playlist_id)

    ordered_ids = list(membership.keys())
    raw_videos = client.videos_by_ids(ordered_ids)
    found_ids = {v.get("id") for v in raw_videos if v.get("id")}
    dropped = [vid for vid in ordered_ids if vid not in found_ids]

    videos: list[VideoRecord] = []
    for raw in raw_videos:
        vid = raw.get("id")
        if not vid:
            continue
        snip = raw.get("snippet") or {}
        stats = raw.get("statistics") or {}
        details = raw.get("contentDetails") or {}
        caption_flag = details.get("caption")
        caption_available = None
        if caption_flag == "true":
            caption_available = True
        elif caption_flag == "false":
            caption_available = False
        videos.append(
            VideoRecord(
                video_id=vid,
                title=snip.get("title") or "",
                url=f"https://www.youtube.com/watch?v={vid}",
                published_at=snip.get("publishedAt"),
                duration_seconds=parse_iso_duration_seconds(details.get("duration")),
                view_count=_int_or_none(stats.get("viewCount")),
                like_count=_int_or_none(stats.get("likeCount")),
                comment_count=_int_or_none(stats.get("commentCount")),
                channel_id=snip.get("channelId") or channel_id,
                channel_name=snip.get("channelTitle") or channel_name,
                playlist_ids=sorted(membership.get(vid, set())),
                description=snip.get("description") or "",
                caption_available=caption_available,
                language=snip.get("defaultAudioLanguage")
                or snip.get("defaultLanguage"),
                retrieved_at=retrieved_at,
                thumbnail_url=_thumbnail_url(snip),
                status="DISCOVERED",
                source_id=source_id,
                source_tier=tier,
                origin_tag=origin_tag,
            )
        )

    log.info(
        "Discovered %s videos across %s playlists on %s (%s) source_id=%s tier=%s",
        len(videos),
        len(playlists),
        channel_name,
        source_url,
        source_id,
        tier,
    )
    return DiscoveryResult(
        channel_id=channel_id,
        channel_name=channel_name,
        channel_handle=handle,
        uploads_playlist_id=uploads_id,
        playlists=playlists,
        videos=videos,
        dropped_video_ids=dropped,
        retrieved_at=retrieved_at,
        source=playlists_url,
        source_id=source_id,
        source_tier=tier,
        origin_tag=origin_tag,
    )
