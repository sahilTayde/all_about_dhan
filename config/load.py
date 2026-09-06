"""Load `config/workspace.yaml` (optional gitignored overlay + env interpolation).

Never print secret values. `.env` is the only place keys are stored.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

_ENV_INTERPOLATION = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
_YT_HANDLE_IN_URL = re.compile(
    r"(?:https?://)?(?:www\.)?youtube\.com/@([^/?#]+)", re.IGNORECASE
)

WORKSPACE_FILENAME = "workspace.yaml"
WORKSPACE_LOCAL_FILENAME = "workspace.local.yaml"


def repo_root_from(start: Optional[Path] = None) -> Path:
    here = (start or Path(__file__)).resolve()
    if here.is_file():
        here = here.parent
    for candidate in [here, *here.parents]:
        if (candidate / "AGENT.md").is_file() and (candidate / ".env.example").is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate repo root (expected AGENT.md and .env.example)."
    )


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _interpolate(value: Any) -> Any:
    if isinstance(value, str):

        def repl(match: re.Match[str]) -> str:
            return os.environ.get(match.group(1), "")

        return _ENV_INTERPOLATION.sub(repl, value)
    if isinstance(value, list):
        return [_interpolate(item) for item in value]
    if isinstance(value, dict):
        return {k: _interpolate(v) for k, v in value.items()}
    return value


def env_name_from_ref(raw: str, default: str) -> str:
    """Map `YOUTUBE_API_KEY` or `${YOUTUBE_API_KEY}` to the env variable name."""
    text = (raw or "").strip()
    match = re.fullmatch(r"\$\{([A-Z][A-Z0-9_]*)\}", text)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Z][A-Z0-9_]*", text):
        return text
    return default


def _secret_name_map(raw_secrets: Any) -> dict[str, str]:
    """logical_key → ENV_VAR_NAME. Never stores secret values."""
    if not isinstance(raw_secrets, dict):
        return {}
    mapped: dict[str, str] = {}
    for logical, ref in raw_secrets.items():
        key = str(logical).strip()
        default = re.sub(r"[^A-Z0-9]+", "_", key.upper()).strip("_") or key.upper()
        mapped[key] = env_name_from_ref(str(ref), default)
    return mapped


def parse_youtube_handle(handle: Optional[str], url: Optional[str]) -> str:
    """Handle from `handle` or a youtube.com/@... URL (including /playlists)."""
    if handle and str(handle).strip():
        return str(handle).strip().lstrip("@")
    if url:
        match = _YT_HANDLE_IN_URL.search(str(url))
        if match:
            return match.group(1).strip().lstrip("@")
    raise ValueError(
        "YouTube source needs `handle` or a URL like https://www.youtube.com/@Name"
    )


@dataclass
class YoutubeSource:
    id: str
    handle: str
    url: str
    playlists_url: str
    tier: str
    origin: str
    enabled: bool

    @property
    def origin_tag(self) -> str:
        if self.tier == "EXTERNAL_RESEARCH" or self.origin == "EXTERNAL_RESEARCH":
            return "EXTERNAL_RESEARCH"
        if self.tier == "TIER_1":
            return self.origin or "DHAN-DERIVED"
        return self.origin or "EXTERNAL_RESEARCH"

    @property
    def display_handle(self) -> str:
        return f"@{self.handle}"


@dataclass
class BookSource:
    id: str
    title: str
    author: str
    url: str
    use: str
    enabled: bool


@dataclass
class Market:
    id: str
    type: str
    enabled: bool
    # Dhan option-chain body. Official docs example uses UnderlyingScrip 13 unnamed.
    # VERIFY FROM instrument master — do not treat defaults as eternal truth.
    dhan_underlying_scrip: Optional[int] = None
    dhan_underlying_seg: str = "IDX_I"
    option_quote_seg: str = "NSE_FNO"


@dataclass
class NewsSource:
    id: str
    url: str
    kind: str  # rss | official | calendar
    region: str
    tags: list[str]
    enabled: bool
    note: str


@dataclass
class DeskIntelSettings:
    chain_interval: str = "3m"
    strike_buildup_interval: str = "1m"
    strike_buildup_enabled: bool = False
    remember_last_snapshot: bool = True
    atm_wing: int = 5
    option_chain_min_seconds: int = 3
    quote_min_seconds: float = 1.0
    sentiment_windows: list[str] = field(default_factory=lambda: ["10m", "15m", "30m", "1h"])
    snapshots_dir: str = "data/desk_intel/snapshots"
    signals_dir: str = "data/desk_intel/signals"
    ledger_dir: str = "data/desk_intel/ledger"
    recon_dir: str = "data/recon"
    phd_handoff_dir: str = "teams/02_phd_math/docs/handoffs"
    cas_calls_dir: str = "teams/03_phd_market/cas/calls"
    news_lookback_hours: int = 18
    event_veto_minutes: int = 60
    opening_drive_until: str = "09:45"
    keywords: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class JobWindow:
    enabled: bool = True
    before_ist: Optional[str] = None
    after_ist: Optional[str] = None
    session_close_ist: str = "UNKNOWN"
    session_close_note: str = ""
    note: str = ""


@dataclass
class DocsAuditorJob:
    """Standing Docs Auditor (09). Cadence daily = post-market + on demand."""

    enabled: bool = True
    cadence: str = "daily"
    note: str = ""


@dataclass
class JobsSettings:
    pre_market: JobWindow = field(default_factory=JobWindow)
    post_market: JobWindow = field(default_factory=JobWindow)
    docs_auditor: DocsAuditorJob = field(default_factory=DocsAuditorJob)


@dataclass
class TopicCluster:
    id: str
    title: str
    tags: list[str]
    match: str  # any | all


@dataclass
class PipelinePaths:
    catalog_csv: str
    catalog_json: str
    external_candidates: str
    transcripts_raw: str
    transcripts_normalized: str
    transcripts_parked: str
    english_normalized: str
    topic_extract_dir: str
    strategy_docs_dir: str
    run_report: str
    topic_clusters: list[TopicCluster] = field(default_factory=list)


@dataclass
class Implementation:
    broker: str
    indicators: str


@dataclass
class WorkspaceConfig:
    """Customer master config. Secret *values* are not stored here."""

    path: Path
    overlay_path: Optional[Path]
    schema_version: int
    implementation: Implementation
    markets: list[Market]
    youtube_sources: list[YoutubeSource]
    books: list[BookSource]
    news_sources: list[NewsSource]
    pre_open_sources: list[NewsSource]
    gift_sources: list[NewsSource]
    global_tape_sources: list[NewsSource]
    desk_intel: DeskIntelSettings
    jobs: JobsSettings
    secrets_from_env: dict[str, str]
    pipeline: PipelinePaths
    agent_routing: dict[str, str]
    repo_root: Path

    @property
    def enabled_youtube_sources(self) -> list[YoutubeSource]:
        return [s for s in self.youtube_sources if s.enabled]

    @property
    def primary_youtube(self) -> YoutubeSource:
        enabled = self.enabled_youtube_sources
        if not enabled:
            raise ValueError(
                "No enabled YouTube sources in config/workspace.yaml. "
                "Set sources.youtube[].enabled: true on at least one channel."
            )
        for source in enabled:
            if source.tier == "TIER_1":
                return source
        return enabled[0]

    def secret_present(self, env_name: str) -> bool:
        return bool((os.environ.get(env_name) or "").strip())

    def secret_env_name(self, logical_key: str, default: str) -> str:
        return self.secrets_from_env.get(logical_key) or default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def _youtube_source(raw: dict[str, Any]) -> YoutubeSource:
    url = str(raw.get("url") or "").strip()
    handle = parse_youtube_handle(raw.get("handle"), url or raw.get("playlists_url"))
    playlists = str(raw.get("playlists_url") or "").strip()
    if not playlists and url:
        playlists = url.rstrip("/") + "/playlists"
    if not url:
        url = f"https://www.youtube.com/@{handle}"
    tier = str(raw.get("tier") or "EXTERNAL_RESEARCH").strip()
    origin = str(raw.get("origin") or "").strip()
    if not origin:
        origin = "DHAN-DERIVED" if tier == "TIER_1" else "EXTERNAL_RESEARCH"
    source_id = str(raw.get("id") or handle).strip()
    if tier == "TIER_1" and source_id.lower() not in ("dhanhq", "dhan"):
        # Customer may do this; keep the value but origin must not look official Dhan.
        if origin == "DHAN-DERIVED":
            origin = "EXTERNAL_RESEARCH"
    return YoutubeSource(
        id=source_id,
        handle=handle,
        url=url,
        playlists_url=playlists or f"https://www.youtube.com/@{handle}/playlists",
        tier=tier,
        origin=origin,
        enabled=_as_bool(raw.get("enabled"), False),
    )


def _book(raw: dict[str, Any]) -> BookSource:
    title = str(raw.get("title") or "").strip()
    return BookSource(
        id=str(raw.get("id") or title).strip(),
        title=title,
        author=str(raw.get("author") or "").strip(),
        url=str(raw.get("url") or "").strip(),
        use=str(raw.get("use") or "VALIDATION").strip(),
        enabled=_as_bool(raw.get("enabled"), True),
    )


def _market(raw: dict[str, Any]) -> Market:
    scrip = raw.get("dhan_underlying_scrip")
    scrip_i: Optional[int] = None
    if scrip not in (None, ""):
        scrip_i = int(scrip)
    return Market(
        id=str(raw.get("id") or "").strip(),
        type=str(raw.get("type") or "INDEX_OPTION").strip(),
        enabled=_as_bool(raw.get("enabled"), True),
        dhan_underlying_scrip=scrip_i,
        dhan_underlying_seg=str(raw.get("dhan_underlying_seg") or "IDX_I").strip(),
        option_quote_seg=str(raw.get("option_quote_seg") or "NSE_FNO").strip(),
    )


def _news_source(raw: dict[str, Any]) -> NewsSource:
    tags = raw.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    return NewsSource(
        id=str(raw.get("id") or "").strip(),
        url=str(raw.get("url") or "").strip(),
        kind=str(raw.get("kind") or "rss").strip().lower(),
        region=str(raw.get("region") or "").strip(),
        tags=[str(t).strip() for t in tags if str(t).strip()],
        enabled=_as_bool(raw.get("enabled"), True),
        note=str(raw.get("note") or "").strip(),
    )


def _keyword_map(raw: Any) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, str):
            items = [value]
        elif isinstance(value, list):
            items = value
        else:
            continue
        out[str(key)] = [str(v).strip() for v in items if str(v).strip()]
    return out


def _desk_intel(raw: Optional[dict[str, Any]]) -> DeskIntelSettings:
    data = raw or {}
    poll = data.get("poll") or {}
    sentiment = data.get("sentiment") or {}
    windows_raw = sentiment.get("windows") or poll.get("sentiment_windows") or data.get(
        "sentiment_windows"
    )
    if isinstance(windows_raw, list) and windows_raw:
        sentiment_windows = [str(x).strip() for x in windows_raw if str(x).strip()]
    else:
        sentiment_windows = ["10m", "15m", "30m", "1h"]
    return DeskIntelSettings(
        chain_interval=str(poll.get("chain_interval") or data.get("chain_interval") or "3m"),
        strike_buildup_interval=str(
            poll.get("strike_buildup_interval")
            or data.get("strike_buildup_interval")
            or "1m"
        ),
        strike_buildup_enabled=_as_bool(
            poll.get("strike_buildup_enabled", data.get("strike_buildup_enabled")),
            False,
        ),
        remember_last_snapshot=_as_bool(
            poll.get("remember_last_snapshot", data.get("remember_last_snapshot")),
            True,
        ),
        atm_wing=int(poll.get("atm_wing") or data.get("atm_wing") or 5),
        option_chain_min_seconds=int(
            poll.get("option_chain_min_seconds")
            or data.get("option_chain_min_seconds")
            or 3
        ),
        quote_min_seconds=float(
            poll.get("quote_min_seconds") or data.get("quote_min_seconds") or 1.0
        ),
        snapshots_dir=str(
            data.get("snapshots_dir") or "data/desk_intel/snapshots"
        ),
        signals_dir=str(data.get("signals_dir") or "data/desk_intel/signals"),
        ledger_dir=str(data.get("ledger_dir") or "data/desk_intel/ledger"),
        recon_dir=str(data.get("recon_dir") or "data/recon"),
        phd_handoff_dir=str(
            data.get("phd_handoff_dir") or "teams/02_phd_math/docs/handoffs"
        ),
        cas_calls_dir=str(
            data.get("cas_calls_dir") or "teams/03_phd_market/cas/calls"
        ),
        news_lookback_hours=int(data.get("news_lookback_hours") or 18),
        event_veto_minutes=int(data.get("event_veto_minutes") or 60),
        opening_drive_until=str(data.get("opening_drive_until") or "09:45"),
        keywords=_keyword_map(data.get("keywords")),
        sentiment_windows=sentiment_windows,
    )


def _job_window(raw: Optional[dict[str, Any]], *, default_before: Optional[str] = None, default_after: Optional[str] = None) -> JobWindow:
    data = raw or {}
    return JobWindow(
        enabled=_as_bool(data.get("enabled"), True),
        before_ist=(str(data["before_ist"]).strip() if data.get("before_ist") else default_before),
        after_ist=(str(data["after_ist"]).strip() if data.get("after_ist") else default_after),
        session_close_ist=str(data.get("session_close_ist") or "UNKNOWN").strip(),
        session_close_note=str(data.get("session_close_note") or "").strip(),
        note=str(data.get("note") or "").strip(),
    )


def _docs_auditor_job(raw: Any) -> DocsAuditorJob:
    if isinstance(raw, str):
        cadence = raw.strip().lower() or "daily"
        return DocsAuditorJob(
            enabled=cadence not in {"off", "false", "0", "disabled"},
            cadence=cadence,
        )
    data = raw if isinstance(raw, dict) else {}
    cadence = str(data.get("cadence") or "daily").strip().lower() or "daily"
    return DocsAuditorJob(
        enabled=_as_bool(data.get("enabled"), True),
        cadence=cadence,
        note=str(data.get("note") or "").strip(),
    )


def _jobs(raw: Optional[dict[str, Any]]) -> JobsSettings:
    data = raw or {}
    pre = data.get("pre_market") if isinstance(data.get("pre_market"), dict) else {}
    post = data.get("post_market") if isinstance(data.get("post_market"), dict) else {}
    return JobsSettings(
        pre_market=_job_window(pre, default_before="09:15"),
        post_market=_job_window(post, default_after="15:40"),
        docs_auditor=_docs_auditor_job(data.get("docs_auditor")),
    )


def _cluster(raw: dict[str, Any]) -> TopicCluster:
    tags = raw.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    match = str(raw.get("match") or "any").strip().lower()
    if match not in ("any", "all"):
        match = "any"
    return TopicCluster(
        id=str(raw.get("id") or "").strip(),
        title=str(raw.get("title") or raw.get("id") or "").strip(),
        tags=[str(t).strip() for t in tags if str(t).strip()],
        match=match,
    )


def _pipeline(raw: Optional[dict[str, Any]]) -> PipelinePaths:
    data = raw or {}
    catalog = data.get("catalog") or {}
    transcripts = data.get("transcripts") or {}
    english = data.get("english") or {}
    topic_extract = data.get("topic_extract") or {}
    strategy_docs = data.get("strategy_docs") or {}
    clusters_raw = data.get("topic_clusters") or []
    return PipelinePaths(
        catalog_csv=str(catalog.get("csv") or "data/youtube/video_catalog.csv"),
        catalog_json=str(catalog.get("json") or "data/youtube/video_catalog.json"),
        external_candidates=str(
            catalog.get("external_candidates") or "data/youtube/external_candidates.md"
        ),
        transcripts_raw=str(transcripts.get("raw") or "data/transcripts/raw"),
        transcripts_normalized=str(
            transcripts.get("normalized") or "data/transcripts/normalized"
        ),
        transcripts_parked=str(
            transcripts.get("parked") or "data/transcripts/parked_tomorrow"
        ),
        english_normalized=str(
            english.get("normalized") or "data/transcripts/normalized_en"
        ),
        topic_extract_dir=str(topic_extract.get("dir") or "data/topics"),
        strategy_docs_dir=str(
            strategy_docs.get("dir") or "teams/04_quant/docs/topics"
        ),
        run_report=str(
            data.get("run_report") or "teams/01_research/youtube/docs/RUN_REPORT.md"
        ),
        topic_clusters=[_cluster(c) for c in clusters_raw if isinstance(c, dict)],
    )


def load_workspace(
    root: Optional[Path] = None, *, load_env: bool = True
) -> WorkspaceConfig:
    """Load the master yaml. Secret values come from `.env` via ${VAR} interpolation."""
    repo = repo_root_from(root)
    if load_env:
        env_path = repo / ".env"
        if env_path.is_file():
            load_dotenv(dotenv_path=env_path, override=False)

    path = repo / "config" / WORKSPACE_FILENAME
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing {path}. This is the customer master file for URLs and books."
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a YAML mapping.")

    overlay_path = repo / "config" / WORKSPACE_LOCAL_FILENAME
    used_overlay: Optional[Path] = None
    if overlay_path.is_file():
        overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8")) or {}
        if isinstance(overlay, dict):
            raw = _deep_merge(raw, overlay)
            used_overlay = overlay_path

    # Capture env *names* before interpolation so secret values never sit in this object.
    secret_names = _secret_name_map(raw.pop("secrets_from_env", {}) or {})
    raw = _interpolate(raw)

    sources = raw.get("sources") or {}
    youtube_raw = sources.get("youtube") or []
    books_raw = sources.get("books") or []
    news_raw = sources.get("news") or []
    pre_open_raw = sources.get("pre_open") or []
    gift_raw = sources.get("gift_nifty") or []
    global_tape_raw = sources.get("global_tape") or []
    impl = raw.get("implementation") or {}

    return WorkspaceConfig(
        path=path,
        overlay_path=used_overlay,
        schema_version=int(raw.get("schema_version") or 1),
        implementation=Implementation(
            broker=str(impl.get("broker") or "dhan").strip().lower(),
            indicators=str(impl.get("indicators") or "dhan_only").strip().lower(),
        ),
        markets=[_market(m) for m in (raw.get("markets") or []) if isinstance(m, dict)],
        youtube_sources=[
            _youtube_source(item) for item in youtube_raw if isinstance(item, dict)
        ],
        books=[_book(item) for item in books_raw if isinstance(item, dict)],
        news_sources=[
            _news_source(item) for item in news_raw if isinstance(item, dict)
        ],
        pre_open_sources=[
            _news_source(item) for item in pre_open_raw if isinstance(item, dict)
        ],
        gift_sources=[
            _news_source(item) for item in gift_raw if isinstance(item, dict)
        ],
        global_tape_sources=[
            _news_source(item) for item in global_tape_raw if isinstance(item, dict)
        ],
        desk_intel=_desk_intel(raw.get("desk_intel") if isinstance(raw.get("desk_intel"), dict) else {}),
        jobs=_jobs(raw.get("jobs") if isinstance(raw.get("jobs"), dict) else {}),
        secrets_from_env=secret_names,
        pipeline=_pipeline(raw.get("pipeline")),
        agent_routing={
            str(k): str(v)
            for k, v in (raw.get("agent_routing") or {}).items()
        },
        repo_root=repo,
    )
