"""Load settings from config/workspace.yaml + repo-root `.env`. Never print secrets."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Fallback defaults if yaml is missing a field. Live channel list is workspace.yaml.
CHANNEL_HANDLE = "DhanHQ"
CHANNEL_URL = "https://www.youtube.com/@DhanHQ"
PLAYLISTS_URL = "https://www.youtube.com/@DhanHQ/playlists"

# PLAN.md §6 defaults (configurable via env)
DEFAULT_W_VIEWS = 0.55
DEFAULT_W_LIKES = 0.20
DEFAULT_W_COMMENTS = 0.10
DEFAULT_W_RECENCY = 0.15
DEFAULT_RECENCY_HALF_LIFE_DAYS = 365.0
DEFAULT_TRANSCRIPT_CAP = 40
DEFAULT_REQUEST_PAUSE = 0.2
DEFAULT_TRANSCRIPT_PAUSE = 1.2
DEFAULT_RETRY_PAUSE = 4.0
DEFAULT_BACKOFF_SECONDS = 20.0
DEFAULT_BACKOFF_ATTEMPTS = 3

# Seed videos from PLAN.md §8 — include in the transcript set when present.
PLAN_SEED_VIDEO_IDS = (
    "HAUSZx-hYdY",
    "wDZXqzdGBDc",
    "H_6keeRUCDM",
    "PUkzVgVPCf0",
    "njqeZc_tYy8",
    "gA5FtEnSABM",
)


def repo_root() -> Path:
    start = Path(__file__).resolve()
    for candidate in [start.parent, *start.parents]:
        if (candidate / "AGENT.md").is_file() and (candidate / ".env.example").is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate repo root (expected AGENT.md and .env.example)."
    )


def _ensure_repo_on_path(root: Path) -> None:
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)


def load_workspace_config():
    """Load the customer master file `config/workspace.yaml`."""
    root = repo_root()
    _ensure_repo_on_path(root)
    from config.load import load_workspace  # noqa: WPS433 — repo-root package

    return load_workspace(root)


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass
class Settings:
    youtube_api_key: str = field(repr=False)
    repo_root: Path
    channel_handle: str = CHANNEL_HANDLE
    channel_url: str = CHANNEL_URL
    playlists_url: str = PLAYLISTS_URL
    w_views: float = DEFAULT_W_VIEWS
    w_likes: float = DEFAULT_W_LIKES
    w_comments: float = DEFAULT_W_COMMENTS
    w_recency: float = DEFAULT_W_RECENCY
    recency_half_life_days: float = DEFAULT_RECENCY_HALF_LIFE_DAYS
    transcript_cap: int = DEFAULT_TRANSCRIPT_CAP
    request_pause_seconds: float = DEFAULT_REQUEST_PAUSE
    transcript_pause_seconds: float = DEFAULT_TRANSCRIPT_PAUSE
    transcript_retry_pause_seconds: float = DEFAULT_RETRY_PAUSE
    transcript_backoff_seconds: float = DEFAULT_BACKOFF_SECONDS
    transcript_backoff_attempts: int = DEFAULT_BACKOFF_ATTEMPTS
    workspace: object = None
    catalog_csv_rel: str = "data/youtube/video_catalog.csv"
    catalog_json_rel: str = "data/youtube/video_catalog.json"
    raw_transcript_rel: str = "data/transcripts/raw"
    normalized_transcript_rel: str = "data/transcripts/normalized"
    normalized_en_rel: str = "data/transcripts/normalized_en"
    parked_tomorrow_rel: str = "data/transcripts/parked_tomorrow"
    run_report_rel: str = "teams/01_research/youtube/docs/RUN_REPORT.md"
    external_candidates_rel: str = "data/youtube/external_candidates.md"
    strategy_docs_rel: str = "teams/04_quant/docs/topics"
    topic_extract_rel: str = "data/topics"

    @property
    def catalog_csv(self) -> Path:
        return self.repo_root / self.catalog_csv_rel

    @property
    def catalog_json(self) -> Path:
        return self.repo_root / self.catalog_json_rel

    @property
    def raw_transcript_dir(self) -> Path:
        return self.repo_root / self.raw_transcript_rel

    @property
    def normalized_transcript_dir(self) -> Path:
        return self.repo_root / self.normalized_transcript_rel

    @property
    def normalized_en_dir(self) -> Path:
        return self.repo_root / self.normalized_en_rel

    @property
    def parked_tomorrow_dir(self) -> Path:
        return self.repo_root / self.parked_tomorrow_rel

    @property
    def run_report_path(self) -> Path:
        return self.repo_root / self.run_report_rel

    @property
    def external_candidates_path(self) -> Path:
        return self.repo_root / self.external_candidates_rel

    @property
    def strategy_docs_dir(self) -> Path:
        return self.repo_root / self.strategy_docs_rel

    @property
    def topic_extract_dir(self) -> Path:
        return self.repo_root / self.topic_extract_rel

    @property
    def enabled_youtube_sources(self) -> list:
        workspace = self.workspace
        if workspace is None:
            return []
        return workspace.enabled_youtube_sources

    @property
    def implementation_broker(self) -> str:
        workspace = self.workspace
        if workspace is None:
            return "dhan"
        return workspace.implementation.broker

    @property
    def indicators_policy(self) -> str:
        workspace = self.workspace
        if workspace is None:
            return "dhan_only"
        return workspace.implementation.indicators


def _settings_from_workspace(root: Path, workspace, *, youtube_api_key: str) -> Settings:
    primary = workspace.primary_youtube
    pipe = workspace.pipeline
    return Settings(
        youtube_api_key=youtube_api_key,
        repo_root=root,
        channel_handle=primary.handle,
        channel_url=primary.url,
        playlists_url=primary.playlists_url,
        w_views=_float_env("YOUTUBE_POPULARITY_W_VIEWS", DEFAULT_W_VIEWS),
        w_likes=_float_env("YOUTUBE_POPULARITY_W_LIKES", DEFAULT_W_LIKES),
        w_comments=_float_env("YOUTUBE_POPULARITY_W_COMMENTS", DEFAULT_W_COMMENTS),
        w_recency=_float_env("YOUTUBE_POPULARITY_W_RECENCY", DEFAULT_W_RECENCY),
        recency_half_life_days=_float_env(
            "YOUTUBE_RECENCY_HALF_LIFE_DAYS", DEFAULT_RECENCY_HALF_LIFE_DAYS
        ),
        transcript_cap=_int_env("YOUTUBE_TRANSCRIPT_CAP", DEFAULT_TRANSCRIPT_CAP),
        request_pause_seconds=_float_env(
            "YOUTUBE_REQUEST_PAUSE", DEFAULT_REQUEST_PAUSE
        ),
        transcript_pause_seconds=_float_env(
            "YOUTUBE_TRANSCRIPT_PAUSE", DEFAULT_TRANSCRIPT_PAUSE
        ),
        transcript_retry_pause_seconds=_float_env(
            "YOUTUBE_TRANSCRIPT_RETRY_PAUSE", DEFAULT_RETRY_PAUSE
        ),
        transcript_backoff_seconds=_float_env(
            "YOUTUBE_TRANSCRIPT_BACKOFF", DEFAULT_BACKOFF_SECONDS
        ),
        transcript_backoff_attempts=_int_env(
            "YOUTUBE_TRANSCRIPT_BACKOFF_ATTEMPTS", DEFAULT_BACKOFF_ATTEMPTS
        ),
        workspace=workspace,
        catalog_csv_rel=pipe.catalog_csv,
        catalog_json_rel=pipe.catalog_json,
        raw_transcript_rel=pipe.transcripts_raw,
        normalized_transcript_rel=pipe.transcripts_normalized,
        normalized_en_rel=pipe.english_normalized,
        parked_tomorrow_rel=pipe.transcripts_parked,
        run_report_rel=pipe.run_report,
        external_candidates_rel=pipe.external_candidates,
        strategy_docs_rel=pipe.strategy_docs_dir,
        topic_extract_rel=pipe.topic_extract_dir,
    )


def load_settings(*, require_youtube_key: bool = True) -> Settings:
    """Load YOUTUBE_API_KEY from repo-root `.env`; channels from workspace.yaml."""
    root = repo_root()
    env_path = root / ".env"
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path, override=False)
    elif require_youtube_key:
        raise FileNotFoundError(
            f"Missing {env_path}. Copy .env.example to .env and set YOUTUBE_API_KEY. "
            "URLs/books live in config/workspace.yaml. Never paste the key into chat."
        )

    workspace = load_workspace_config()
    key_name = workspace.secret_env_name("youtube_api_key", "YOUTUBE_API_KEY")
    key = (os.environ.get(key_name) or "").strip()
    if require_youtube_key and not key:
        raise ValueError(
            f"{key_name} is empty in repo-root .env. "
            "See teams/01_research/youtube/README.md. "
            "Do not put the key in config/workspace.yaml."
        )
    return _settings_from_workspace(root, workspace, youtube_api_key=key)
