"""Transcript QA. Flags uncertainty; never rewrites numbers by guesswork."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

INDICATOR_NEAR_NUMBER = re.compile(
    r"(?i)\b("
    r"rsi|ema|sma|macd|adx|atr|vwap|super\s*trend|bollinger|"
    r"delta|gamma|theta|vega|iv|oi|strike"
    r")\b[^.\n]{0,24}\d+(?:\.\d+)?"
)

DIGIT_RUN = re.compile(r"\d{5,}")


@dataclass
class QAResult:
    flags: list[str] = field(default_factory=list)
    uncertain_indexes: list[int] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def qa_segments(
    segments: list[dict],
    video_duration_seconds: int | None = None,
) -> QAResult:
    result = QAResult()
    if not segments:
        result.flags.append("EMPTY_TRANSCRIPT")
        result.notes.append("No caption segments returned.")
        return result

    prev_start: float | None = None
    prev_text: str | None = None
    dup_run = 0
    coverage = 0.0

    for i, seg in enumerate(segments):
        start = float(seg.get("start") or 0)
        duration = float(seg.get("duration") or 0)
        text = (seg.get("text") or "").strip()
        coverage += duration

        if prev_start is not None and start + 1e-6 < prev_start:
            if "TIMESTAMP_ANOMALY" not in result.flags:
                result.flags.append("TIMESTAMP_ANOMALY")
            result.notes.append(f"Timestamp moved backwards at segment {i}.")

        if text and text == prev_text:
            dup_run += 1
            if dup_run >= 2 and "DUPLICATE_SEGMENTS" not in result.flags:
                result.flags.append("DUPLICATE_SEGMENTS")
        else:
            dup_run = 0

        if text and (
            INDICATOR_NEAR_NUMBER.search(text) or DIGIT_RUN.search(text)
        ):
            result.uncertain_indexes.append(i)

        prev_start = start
        prev_text = text or prev_text

    if result.uncertain_indexes:
        result.flags.append("UNCERTAIN_TRANSCRIPT")
        result.notes.append(
            "Numbers near indicator names or long digit runs were flagged; "
            "values were not rewritten."
        )

    if video_duration_seconds and video_duration_seconds > 30:
        if coverage < 0.5 * float(video_duration_seconds):
            result.flags.append("SHORT_COVERAGE")
            result.notes.append(
                f"Caption duration {coverage:.0f}s vs video {video_duration_seconds}s."
            )

    return result
