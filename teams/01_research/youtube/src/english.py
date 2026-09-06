"""YouTube-provided English captions. Never LLM-translates the corpus."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Optional

from .caption_http import (
    is_block_error,
    list_transcripts,
    sanitize_block_message,
    track_inventory,
    with_backoff,
)
from .discovery import VideoRecord
from .transcript_qa import qa_segments
from .transcripts import (
    STATUS_UNAVAILABLE,
    TranscriptFetch,
    _as_segments,
    _now,
    apply_english_to_video,
    is_source_transcript_json,
    load_raw_fetch,
    write_normalized_md,
    write_raw_json,
)

log = logging.getLogger(__name__)

ENGLISH_CODES = ("en", "en-IN", "en-GB", "en-US", "en-CA")
STATUS_ENGLISH_VERIFIED = "ENGLISH_VERIFIED"
STATUS_ENGLISH_UNAVAILABLE = "ENGLISH_UNAVAILABLE"


def _is_english_code(code: Optional[str]) -> bool:
    if not code:
        return False
    return code.lower() == "en" or code.lower().startswith("en-") or code.lower().startswith("en_")


def _try_finder(listing: Any, finder: str, codes: tuple[str, ...]) -> Optional[Any]:
    fn = getattr(listing, finder, None)
    if fn is None:
        return None
    try:
        return fn(list(codes))
    except Exception:
        return None


def _force_tlang(track: Any, language_code: str = "en") -> Any:
    """Append YouTube `tlang=` even if Innertube omitted translationLanguages.

    The ANDROID player JSON used by youtube-transcript-api often lists ASR Hindi
    as not translatable. The watch-page player still supports auto-translate via
    `tlang=en` on the same timedtext URL.
    """
    from youtube_transcript_api._transcripts import Transcript

    url = getattr(track, "_url", "") or ""
    if "tlang=" not in url:
        url = f"{url}&tlang={language_code}"
    http = getattr(track, "_http_client", None)
    return Transcript(
        http,
        getattr(track, "video_id", ""),
        url,
        "English",
        language_code,
        True,
        [],
    )


def pick_english_track(listing: Any) -> tuple[Optional[Any], Optional[str], Optional[str]]:
    """Prefer a native English track; else YouTube auto-translate (`tlang=en`).

    Returns (track_or_translated, translation_source, source_language).
    translation_source is `manual`, `generated`, or `youtube_translate`.
    """
    manual = _try_finder(listing, "find_manually_created_transcript", ENGLISH_CODES)
    if manual is not None:
        return manual, "manual", getattr(manual, "language_code", None)

    generated = _try_finder(listing, "find_generated_transcript", ENGLISH_CODES)
    if generated is not None:
        return generated, "generated", getattr(generated, "language_code", None)

    tracks: list[Any]
    try:
        tracks = list(listing)
    except TypeError:
        tracks = []

    def _rank(track: Any) -> tuple[int, int]:
        code = (getattr(track, "language_code", None) or "").lower()
        hi_rank = 0 if code.startswith("hi") else 1
        gen_rank = 1 if getattr(track, "is_generated", False) else 0
        return (hi_rank, gen_rank)

    translatable = [t for t in tracks if getattr(t, "is_translatable", False)]
    translatable.sort(key=_rank)
    for track in translatable:
        try:
            translated = track.translate("en")
        except Exception:
            continue
        src = getattr(track, "language_code", None)
        return translated, "youtube_translate", src

    # ANDROID listing often has empty translationLanguages; still try tlang=en.
    fallback = sorted(tracks, key=_rank)
    if fallback:
        src_track = fallback[0]
        return (
            _force_tlang(src_track, "en"),
            "youtube_translate",
            getattr(src_track, "language_code", None),
        )
    return None, None, None


def fetch_youtube_english(
    video_id: str,
    *,
    backoff_attempts: int = 3,
    backoff_seconds: float = 20.0,
) -> TranscriptFetch:
    source_url = f"https://www.youtube.com/watch?v={video_id}"
    retrieved_at = _now()

    def _list() -> Any:
        return list_transcripts(video_id)

    try:
        listing = with_backoff(
            _list,
            attempts=backoff_attempts,
            base_delay=backoff_seconds,
            label=f"list:{video_id}",
        )
    except Exception as exc:
        if is_block_error(exc):
            raise
        reason = type(exc).__name__
        log.info("English captions unavailable for %s (%s)", video_id, reason)
        return TranscriptFetch(
            video_id=video_id,
            source_url=source_url,
            retrieved_at=retrieved_at,
            language=None,
            is_generated=None,
            segments=[],
            status=STATUS_UNAVAILABLE,
            reason=reason,
            qa=qa_segments([]),
            translation_source=None,
            source_language=None,
            caption_tracks=[],
            english_status=STATUS_ENGLISH_UNAVAILABLE,
        )

    tracks = track_inventory(listing)
    track, source_kind, source_lang = pick_english_track(listing)
    if track is None:
        return TranscriptFetch(
            video_id=video_id,
            source_url=source_url,
            retrieved_at=retrieved_at,
            language=None,
            is_generated=None,
            segments=[],
            status=STATUS_UNAVAILABLE,
            reason="no_english_track_or_translate",
            qa=qa_segments([]),
            translation_source=None,
            source_language=None,
            caption_tracks=tracks,
            english_status=STATUS_ENGLISH_UNAVAILABLE,
        )

    def _fetch() -> Any:
        return track.fetch()

    fetched = with_backoff(
        _fetch,
        attempts=backoff_attempts,
        base_delay=backoff_seconds,
        label=f"en:{video_id}",
    )
    segments, lang2, gen2 = _as_segments(fetched)
    language = getattr(track, "language_code", None) or lang2 or "en"
    generated = getattr(track, "is_generated", None)
    if generated is None:
        generated = gen2
    if not segments:
        return TranscriptFetch(
            video_id=video_id,
            source_url=source_url,
            retrieved_at=retrieved_at,
            language=language,
            is_generated=generated,
            segments=[],
            status=STATUS_UNAVAILABLE,
            reason="empty_english_captions",
            qa=qa_segments([]),
            translation_source=source_kind,
            source_language=source_lang,
            caption_tracks=tracks,
            english_status=STATUS_ENGLISH_UNAVAILABLE,
        )
    return TranscriptFetch(
        video_id=video_id,
        source_url=source_url,
        retrieved_at=retrieved_at,
        language=language,
        is_generated=generated,
        segments=segments,
        status="TRANSCRIPT_VERIFIED",
        reason=None,
        qa=qa_segments([]),
        translation_source=source_kind,
        source_language=source_lang,
        caption_tracks=tracks,
        english_status=STATUS_ENGLISH_VERIFIED,
    )


def english_raw_path(raw_dir: Path, video_id: str) -> Path:
    return raw_dir / f"{video_id}.en.json"


def copy_native_english(
    video: VideoRecord,
    source_fetch: TranscriptFetch,
    raw_dir: Path,
    normalized_en_dir: Path,
) -> TranscriptFetch:
    """Already-English source file: store a companion `.en.json` without a network call."""
    fetch = TranscriptFetch(
        video_id=video.video_id,
        source_url=source_fetch.source_url,
        retrieved_at=source_fetch.retrieved_at,
        language=source_fetch.language or "en",
        is_generated=source_fetch.is_generated,
        segments=list(source_fetch.segments),
        status=source_fetch.status,
        reason=source_fetch.reason,
        qa=source_fetch.qa,
        translation_source="generated" if source_fetch.is_generated else "manual",
        source_language=source_fetch.language,
        caption_tracks=[],
        english_status=STATUS_ENGLISH_VERIFIED,
    )
    if fetch.segments:
        fetch.qa = qa_segments(fetch.segments, video.duration_seconds)
    write_raw_json(english_raw_path(raw_dir, video.video_id), fetch)
    write_normalized_md(normalized_en_dir / f"{video.video_id}.md", video, fetch)
    apply_english_to_video(video, fetch)
    return fetch


def collect_english_many(
    videos: list[VideoRecord],
    raw_dir: Path,
    normalized_en_dir: Path,
    *,
    pause_seconds: float,
    backoff_attempts: int,
    backoff_seconds: float,
    cap: Optional[int] = None,
) -> tuple[list[TranscriptFetch], Optional[str]]:
    """Fetch YouTube English (native or tlang=en) for verified source transcripts."""
    results: list[TranscriptFetch] = []
    abort_reason: Optional[str] = None
    consecutive_blocks = 0
    fetched_from_network = 0
    targets = videos if cap is None else videos[:cap]

    for i, video in enumerate(targets):
        existing_en = load_raw_fetch(english_raw_path(raw_dir, video.video_id))
        if (
            existing_en is not None
            and existing_en.segments
            and existing_en.english_status == STATUS_ENGLISH_VERIFIED
        ):
            apply_english_to_video(video, existing_en)
            results.append(existing_en)
            continue
        if (
            existing_en is not None
            and existing_en.english_status == STATUS_ENGLISH_UNAVAILABLE
            and existing_en.reason
            not in (None, "ip_or_request_blocked", "CaptionCircuitOpen")
        ):
            apply_english_to_video(video, existing_en)
            results.append(existing_en)
            continue

        source = load_raw_fetch(raw_dir / f"{video.video_id}.json")
        if source and source.segments and _is_english_code(source.language):
            results.append(
                copy_native_english(video, source, raw_dir, normalized_en_dir)
            )
            continue
        if not source or not source.segments:
            continue

        try:
            fetch = fetch_youtube_english(
                video.video_id,
                backoff_attempts=backoff_attempts,
                backoff_seconds=backoff_seconds,
            )
            if fetch.segments:
                fetch.qa = qa_segments(fetch.segments, video.duration_seconds)
                fetch.status = "TRANSCRIPT_VERIFIED"
                fetch.english_status = STATUS_ENGLISH_VERIFIED
            write_raw_json(english_raw_path(raw_dir, video.video_id), fetch)
            write_normalized_md(
                normalized_en_dir / f"{video.video_id}.md", video, fetch
            )
            apply_english_to_video(video, fetch)
            consecutive_blocks = 0
            fetched_from_network += 1
            results.append(fetch)
        except Exception as exc:
            if not is_block_error(exc):
                log.info(
                    "English fetch failed for %s (%s)",
                    video.video_id,
                    type(exc).__name__,
                )
                fetch = TranscriptFetch(
                    video_id=video.video_id,
                    source_url=video.url,
                    retrieved_at=_now(),
                    language=None,
                    is_generated=None,
                    segments=[],
                    status=STATUS_UNAVAILABLE,
                    reason=type(exc).__name__,
                    qa=qa_segments([]),
                    english_status=STATUS_ENGLISH_UNAVAILABLE,
                )
                write_raw_json(english_raw_path(raw_dir, video.video_id), fetch)
                write_normalized_md(
                    normalized_en_dir / f"{video.video_id}.md", video, fetch
                )
                apply_english_to_video(video, fetch)
                results.append(fetch)
                continue
            consecutive_blocks += 1
            log.warning(
                "English timedtext blocked for %s: %s",
                video.video_id,
                sanitize_block_message(exc),
            )
            video.english_status = "ENGLISH_PENDING"
            if consecutive_blocks >= 3:
                abort_reason = "caption_endpoint_blocked"
                for skipped in targets[i + 1 :]:
                    if not skipped.english_status:
                        skipped.english_status = "ENGLISH_PENDING"
                break
        if fetched_from_network and i + 1 < len(targets) and abort_reason is None:
            time.sleep(pause_seconds)
    return results, abort_reason


def hydrate_english_from_disk(videos: list[VideoRecord], raw_dir: Path) -> None:
    by_id = {v.video_id: v for v in videos}
    for path in sorted(raw_dir.glob("*.en.json")):
        fetch = load_raw_fetch(path)
        if fetch is None:
            continue
        video = by_id.get(fetch.video_id)
        if video is None:
            continue
        apply_english_to_video(video, fetch)


def select_english_targets(videos: list[VideoRecord], raw_dir: Path) -> list[VideoRecord]:
    """Verified captions that are not already English-on-disk, HIGH/MEDIUM first."""
    by_id = {v.video_id: v for v in videos}
    verified: list[VideoRecord] = []
    for path in sorted(raw_dir.glob("*.json")):
        if not is_source_transcript_json(path):
            continue
        fetch = load_raw_fetch(path)
        if fetch is None or not fetch.segments:
            continue
        video = by_id.get(fetch.video_id)
        if video is None:
            continue
        if video.status != "TRANSCRIPT_VERIFIED":
            continue
        verified.append(video)

    def _band_rank(video: VideoRecord) -> tuple[int, int]:
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        return (
            order.get((video.relevance_band or "").upper(), 9),
            video.popularity_rank or 10**9,
        )

    verified.sort(key=_band_rank)
    native_first: list[VideoRecord] = []
    rest: list[VideoRecord] = []
    for video in verified:
        src = load_raw_fetch(raw_dir / f"{video.video_id}.json")
        if src and _is_english_code(src.language):
            native_first.append(video)
        else:
            rest.append(video)
    return native_first + rest


# Re-export for callers that only import english.
_ = sanitize_block_message
