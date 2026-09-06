"""Popularity ranking from public metrics. Weights are configurable."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional, Sequence

from .discovery import VideoRecord


def _parse_published(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _minmax(values: Sequence[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return [1.0 if v > 0 else 0.0 for v in values]
    return [(v - lo) / (hi - lo) for v in values]


def recency_score(published_at: Optional[str], now: datetime, half_life_days: float) -> float:
    published = _parse_published(published_at)
    if published is None:
        return 0.0
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age_days = max((now - published).total_seconds() / 86400.0, 0.0)
    if half_life_days <= 0:
        return 0.0
    return math.exp(-age_days / half_life_days)


def rank_videos(
    videos: list[VideoRecord],
    w_views: float = 0.55,
    w_likes: float = 0.20,
    w_comments: float = 0.10,
    w_recency: float = 0.15,
    half_life_days: float = 365.0,
    now: Optional[datetime] = None,
) -> list[VideoRecord]:
    """Attach PopularityScore and 1-based rank (1 = most popular).

    Count metrics are log1p then min-max normalized so a few viral videos
    do not collapse the rest of the catalog to ~0.
    """
    if not videos:
        return videos
    clock = now or datetime.now(timezone.utc)

    view_raw = [math.log1p(max(v.view_count or 0, 0)) for v in videos]
    like_raw = [math.log1p(max(v.like_count or 0, 0)) for v in videos]
    comment_raw = [math.log1p(max(v.comment_count or 0, 0)) for v in videos]
    recency_raw = [
        recency_score(v.published_at, clock, half_life_days) for v in videos
    ]

    n_views = _minmax(view_raw)
    n_likes = _minmax(like_raw)
    n_comments = _minmax(comment_raw)
    n_recency = _minmax(recency_raw)

    weight_sum = w_views + w_likes + w_comments + w_recency
    if weight_sum <= 0:
        raise ValueError("Popularity weights must sum to a positive number.")

    for i, video in enumerate(videos):
        score = (
            n_views[i] * w_views
            + n_likes[i] * w_likes
            + n_comments[i] * w_comments
            + n_recency[i] * w_recency
        ) / weight_sum
        video.popularity_score = round(score, 6)

    ranked = sorted(
        videos,
        key=lambda v: (
            v.popularity_score if v.popularity_score is not None else -1.0,
            v.view_count or 0,
        ),
        reverse=True,
    )
    for rank, video in enumerate(ranked, start=1):
        video.popularity_rank = rank
    return ranked
