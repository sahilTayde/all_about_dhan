"""Public caption collector. Never invents text from title or description."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .caption_http import (
    is_block_error,
    list_transcripts,
    sanitize_block_message,
    track_inventory,
    with_backoff,
)
from .discovery import VideoRecord, utc_now_iso
from .transcript_qa import QAResult, qa_segments

log = logging.getLogger(__name__)

PREFERRED_LANGS = ("en", "en-IN", "en-GB", "en-US", "hi")
STATUS_UNAVAILABLE = "TRANSCRIPT_UNAVAILABLE"
STATUS_VERIFIED = "TRANSCRIPT_VERIFIED"
STATUS_UNCERTAIN = "SOURCE_UNCERTAIN"


@dataclass
class TranscriptFetch:
    video_id: str
    source_url: str
    retrieved_at: str
    language: Optional[str]
    is_generated: Optional[bool]
    segments: list[dict[str, Any]]
    status: str
    reason: Optional[str]
    qa: QAResult
    translation_source: Optional[str] = None
    source_language: Optional[str] = None
    caption_tracks: list[dict[str, Any]] = field(default_factory=list)
    english_status: Optional[str] = None


class CaptionCircuitOpen(Exception):
    """Raised when timedtext starts blocking the client IP."""

    def __init__(self, message: str = "", caption_tracks: Optional[list[dict[str, Any]]] = None):
        super().__init__(message)
        self.caption_tracks = caption_tracks or []


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _as_segments(fetched: Any) -> tuple[list[dict[str, Any]], Optional[str], Optional[bool]]:
    snippets: list[Any]
    language = None
    generated = None
    if hasattr(fetched, "snippets"):
        snippets = list(fetched.snippets)
        language = getattr(fetched, "language_code", None) or getattr(
            fetched, "language", None
        )
        generated = getattr(fetched, "is_generated", None)
    elif isinstance(fetched, list):
        snippets = fetched
    else:
        snippets = list(fetched)

    segments: list[dict[str, Any]] = []
    for item in snippets:
        if hasattr(item, "text"):
            text = item.text
            start = float(getattr(item, "start", 0) or 0)
            duration = float(getattr(item, "duration", 0) or 0)
        elif isinstance(item, dict):
            text = item.get("text") or ""
            start = float(item.get("start") or 0)
            duration = float(item.get("duration") or 0)
        else:
            continue
        segments.append(
            {
                "start": round(start, 3),
                "duration": round(duration, 3),
                "text": str(text).replace("\n", " ").strip(),
            }
        )
    return segments, language, generated


def _pick_from_listing(listing: Any) -> Any:
    for finder in (
        "find_manually_created_transcript",
        "find_generated_transcript",
        "find_transcript",
    ):
        fn = getattr(listing, finder, None)
        if fn is None:
            continue
        try:
            return fn(list(PREFERRED_LANGS))
        except Exception:
            continue
    try:
        return next(iter(listing))
    except StopIteration as exc:
        raise RuntimeError("No transcripts listed.") from exc


def fetch_public_captions(
    video_id: str,
    *,
    backoff_attempts: int = 3,
    backoff_seconds: float = 20.0,
) -> TranscriptFetch:
    """Return public captions or TRANSCRIPT_UNAVAILABLE. Never fabricates text."""
    source_url = f"https://www.youtube.com/watch?v={video_id}"
    retrieved_at = _now()
    try:
        import youtube_transcript_api  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("youtube-transcript-api is not installed.") from exc

    try:
        fetched: Any
        language = None
        generated = None
        tracks: list[dict[str, Any]] = []

        def _list() -> Any:
            return list_transcripts(video_id)

        listing = with_backoff(
            _list,
            attempts=backoff_attempts,
            base_delay=backoff_seconds,
            label=f"list:{video_id}",
        )
        tracks = track_inventory(listing)
        transcript = _pick_from_listing(listing)

        def _fetch() -> Any:
            return transcript.fetch()

        fetched = with_backoff(
            _fetch,
            attempts=backoff_attempts,
            base_delay=backoff_seconds,
            label=f"fetch:{video_id}",
        )
        language = getattr(transcript, "language_code", None)
        generated = getattr(transcript, "is_generated", None)

        segments, lang2, gen2 = _as_segments(fetched)
        language = language or lang2
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
                reason="empty_captions",
                qa=qa_segments([]),
                caption_tracks=tracks,
            )
        return TranscriptFetch(
            video_id=video_id,
            source_url=source_url,
            retrieved_at=retrieved_at,
            language=language,
            is_generated=generated,
            segments=segments,
            status=STATUS_VERIFIED,
            reason=None,
            qa=QAResult(),
            caption_tracks=tracks,
        )
    except CaptionCircuitOpen:
        raise
    except Exception as exc:
        if is_block_error(exc):
            raise CaptionCircuitOpen(sanitize_block_message(exc), caption_tracks=tracks) from exc
        reason = type(exc).__name__
        log.info("Captions unavailable for %s (%s)", video_id, reason)
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
            caption_tracks=tracks,
        )


def format_timestamp(seconds: float) -> str:
    total = max(int(seconds), 0)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def is_source_transcript_json(path: Path) -> bool:
    """True for Hindi/source raw files; skip companion `*.en.json`."""
    name = path.name
    return name.endswith(".json") and not name.endswith(".en.json")


def write_raw_json(path: Path, fetch: TranscriptFetch) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "video_id": fetch.video_id,
        "source_url": fetch.source_url,
        "retrieved_at": fetch.retrieved_at,
        "language": fetch.language,
        "is_generated": fetch.is_generated,
        "status": fetch.status,
        "reason": fetch.reason,
        "qa_flags": fetch.qa.flags,
        "qa_notes": fetch.qa.notes,
        "translation_source": fetch.translation_source,
        "source_language": fetch.source_language,
        "caption_tracks": fetch.caption_tracks,
        "english_status": fetch.english_status,
        "segments": fetch.segments,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_normalized_md(path: Path, video: VideoRecord, fetch: TranscriptFetch) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    uncertain = set(fetch.qa.uncertain_indexes)
    lines = [
        f"# {video.title or video.video_id}",
        "",
        f"- video_id: `{fetch.video_id}`",
        f"- url: {fetch.source_url}",
        f"- retrieved_at: {fetch.retrieved_at}",
        f"- language: {fetch.language or 'UNKNOWN'}",
        f"- is_generated: {fetch.is_generated if fetch.is_generated is not None else 'UNKNOWN'}",
        f"- status: {fetch.status}",
        f"- qa_flags: {', '.join(fetch.qa.flags) if fetch.qa.flags else 'none'}",
        f"- translation_source: {fetch.translation_source or 'n/a'}",
        f"- source_language: {fetch.source_language or 'n/a'}",
        f"- english_status: {fetch.english_status or 'n/a'}",
        "",
    ]
    if fetch.status == STATUS_UNAVAILABLE:
        lines.extend(
            [
                STATUS_UNAVAILABLE,
                "",
                f"Reason: {fetch.reason or 'UNKNOWN'}",
                "",
                "No caption segments. Title/description were not used as a substitute.",
                "",
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    lines.append("## Transcript")
    lines.append("")
    for i, seg in enumerate(fetch.segments):
        stamp = format_timestamp(float(seg.get("start") or 0))
        text = seg.get("text") or ""
        marker = " [UNCERTAIN_TRANSCRIPT]" if i in uncertain else ""
        lines.append(f"[{stamp}] {text}{marker}")
    lines.append("")
    if fetch.qa.notes:
        lines.append("## QA notes")
        lines.append("")
        for note in fetch.qa.notes:
            lines.append(f"- {note}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def load_raw_fetch(path: Path) -> Optional[TranscriptFetch]:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    qa = QAResult(
        flags=list(data.get("qa_flags") or []),
        notes=list(data.get("qa_notes") or []),
    )
    segments = list(data.get("segments") or [])
    status = data.get("status") or STATUS_UNAVAILABLE
    if segments and status == STATUS_UNCERTAIN:
        status = STATUS_VERIFIED
    video_id = str(data.get("video_id") or "")
    if not video_id:
        stem = path.stem
        video_id = stem[:-3] if stem.endswith(".en") else stem
    return TranscriptFetch(
        video_id=video_id,
        source_url=str(data.get("source_url") or ""),
        retrieved_at=str(data.get("retrieved_at") or ""),
        language=data.get("language"),
        is_generated=data.get("is_generated"),
        segments=segments,
        status=status,
        reason=data.get("reason"),
        qa=qa,
        translation_source=data.get("translation_source"),
        source_language=data.get("source_language"),
        caption_tracks=list(data.get("caption_tracks") or []),
        english_status=data.get("english_status"),
    )


def should_refetch(
    fetch: Optional[TranscriptFetch], *, retry_blocked: bool = False
) -> bool:
    if fetch is None:
        return True
    if retry_blocked and fetch.reason in (
        "ip_or_request_blocked",
        "CaptionCircuitOpen",
    ):
        return True
    # Do not immediately retry IP blocks; `--retry-pending` opts in later.
    if fetch.reason in ("ip_or_request_blocked", "CaptionCircuitOpen"):
        return False
    if fetch.status == STATUS_UNAVAILABLE and fetch.reason not in (
        "TranscriptsDisabled",
        "NoTranscriptFound",
        "empty_captions",
        "VideoUnavailable",
        "ip_or_request_blocked",
    ):
        return True
    return False


def hydrate_catalog_from_disk(
    videos: list[VideoRecord],
    raw_dir: Path,
    normalized_dir: Path,
) -> None:
    by_id = {v.video_id: v for v in videos}
    for path in sorted(raw_dir.glob("*.json")):
        if not is_source_transcript_json(path):
            continue
        fetch = load_raw_fetch(path)
        if fetch is None:
            continue
        video = by_id.get(fetch.video_id)
        if video is None:
            continue
        if fetch.segments and fetch.status == STATUS_VERIFIED:
            write_raw_json(path, fetch)
            write_normalized_md(normalized_dir / f"{fetch.video_id}.md", video, fetch)
        apply_fetch_to_video(video, fetch)



def apply_fetch_to_video(video: VideoRecord, fetch: TranscriptFetch) -> None:
    video.caption_available = bool(fetch.segments)
    video.transcript_language = fetch.language
    video.transcript_generated = fetch.is_generated
    video.qa_flags = list(fetch.qa.flags)
    video.status = fetch.status
    if fetch.language:
        video.language = fetch.language


def apply_english_to_video(video: VideoRecord, fetch: TranscriptFetch) -> None:
    """Set English companion fields only. Do not overwrite SOURCE_FACT language."""
    video.english_status = fetch.english_status
    video.english_source = fetch.translation_source


def collect_one(
    video: VideoRecord,
    raw_dir: Path,
    normalized_dir: Path,
    *,
    backoff_attempts: int = 3,
    backoff_seconds: float = 20.0,
) -> TranscriptFetch:
    fetch = fetch_public_captions(
        video.video_id,
        backoff_attempts=backoff_attempts,
        backoff_seconds=backoff_seconds,
    )
    if fetch.segments:
        fetch.qa = qa_segments(fetch.segments, video.duration_seconds)
        if "EMPTY_TRANSCRIPT" in fetch.qa.flags:
            fetch.status = STATUS_UNAVAILABLE
            fetch.reason = fetch.reason or "empty_captions"
        else:
            # Captions exist. Segment-level [UNCERTAIN_TRANSCRIPT] stays in the
            # markdown; do not treat ordinary number flags as SOURCE_UNCERTAIN.
            fetch.status = STATUS_VERIFIED
    write_raw_json(raw_dir / f"{video.video_id}.json", fetch)
    write_normalized_md(normalized_dir / f"{video.video_id}.md", video, fetch)
    apply_fetch_to_video(video, fetch)
    video.retrieved_at = utc_now_iso()
    return fetch


def collect_many(
    videos: list[VideoRecord],
    raw_dir: Path,
    normalized_dir: Path,
    pause_seconds: float,
    *,
    retry_blocked: bool = False,
    backoff_attempts: int = 3,
    backoff_seconds: float = 20.0,
) -> tuple[list[TranscriptFetch], Optional[str]]:
    results: list[TranscriptFetch] = []
    abort_reason: Optional[str] = None
    consecutive_blocks = 0
    fetched_from_network = 0
    for i, video in enumerate(videos):
        existing = load_raw_fetch(raw_dir / f"{video.video_id}.json")
        if existing is not None and not should_refetch(
            existing, retry_blocked=retry_blocked
        ):
            if existing.segments and existing.status == STATUS_VERIFIED:
                write_raw_json(raw_dir / f"{video.video_id}.json", existing)
                write_normalized_md(
                    normalized_dir / f"{video.video_id}.md", video, existing
                )
            apply_fetch_to_video(video, existing)
            results.append(existing)
            continue
        try:
            fetch = collect_one(
                video,
                raw_dir,
                normalized_dir,
                backoff_attempts=backoff_attempts,
                backoff_seconds=backoff_seconds,
            )
            consecutive_blocks = 0
            fetched_from_network += 1
            results.append(fetch)
        except CaptionCircuitOpen as exc:
            consecutive_blocks += 1
            log.warning("Caption endpoint blocked while fetching %s", video.video_id)
            fetch = TranscriptFetch(
                video_id=video.video_id,
                source_url=video.url,
                retrieved_at=_now(),
                language=None,
                is_generated=None,
                segments=[],
                status=STATUS_UNAVAILABLE,
                reason="ip_or_request_blocked",
                qa=qa_segments([]),
                caption_tracks=list(getattr(exc, "caption_tracks", None) or []),
            )
            write_raw_json(raw_dir / f"{video.video_id}.json", fetch)
            write_normalized_md(normalized_dir / f"{video.video_id}.md", video, fetch)
            apply_fetch_to_video(video, fetch)
            results.append(fetch)
            if consecutive_blocks >= 3:
                abort_reason = "caption_endpoint_blocked"
                remaining = videos[i + 1 :]
                for skipped in remaining:
                    if skipped.status not in (
                        STATUS_VERIFIED,
                        STATUS_UNAVAILABLE,
                        STATUS_UNCERTAIN,
                    ):
                        skipped.status = "TRANSCRIPT_PENDING"
                break
            time.sleep(min(backoff_seconds, 60.0))
            _ = exc
        if fetched_from_network and i + 1 < len(videos) and abort_reason is None:
            time.sleep(pause_seconds)
    return results, abort_reason
