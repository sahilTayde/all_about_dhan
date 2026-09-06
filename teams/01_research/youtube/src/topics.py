"""Cluster catalog videos into per-topic strategy-doc stubs.

Does not scrape, does not invent claims, does not dump transcripts into one blob.
Status on every file: UNVALIDATED / HYPOTHESIS. Education ≠ proof.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .config import Settings
from .discovery import VideoRecord

CLUSTER_START = "<!-- CLUSTER_AUTO:START -->"
CLUSTER_END = "<!-- CLUSTER_AUTO:END -->"


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def video_matches_cluster(video: VideoRecord, tags: Iterable[str], match: str) -> bool:
    have = {t.upper() for t in (video.topic_tags or [])}
    need = [t.upper() for t in tags if t]
    if not need:
        return False
    if match == "all":
        return all(tag in have for tag in need)
    return any(tag in have for tag in need)


def cluster_videos(
    videos: list[VideoRecord],
    clusters: list[Any],
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for cluster in clusters:
        hits = [
            v
            for v in videos
            if video_matches_cluster(v, cluster.tags, cluster.match)
            and v.stock_tag != "EXCLUDED_STOCK_ONLY"
        ]
        grouped[cluster.id] = {
            "cluster": cluster,
            "videos": hits,
            "verified": [v for v in hits if v.status == "TRANSCRIPT_VERIFIED"],
            "english": [
                v
                for v in hits
                if (v.english_status or "") in ("ENGLISH_VERIFIED",)
            ],
        }
    return grouped


def _source_tag(video: VideoRecord) -> str:
    origin = video.origin_tag or (
        "EXTERNAL_RESEARCH" if video.source_tier == "EXTERNAL_RESEARCH" else "DHAN-DERIVED"
    )
    source_id = video.source_id or "unknown"
    return f"`{source_id}` / `{origin}`"


def render_cluster_block(cluster: Any, payload: dict[str, Any]) -> str:
    hits: list[VideoRecord] = payload["videos"]
    verified: list[VideoRecord] = payload["verified"]
    lines = [
        CLUSTER_START,
        "",
        f"**Cluster:** `{cluster.id}` · tags `{', '.join(cluster.tags)}` · match `{cluster.match}`",
        f"**Catalog hits:** {len(hits)} · **TRANSCRIPT_VERIFIED:** {len(verified)}",
        "",
        "Pointers only — agents must read transcripts and write claims as `SOURCE_FACT`,",
        "then this file stays `HYPOTHESIS` / `UNVALIDATED`. Do not paste a transcript dump here.",
        "",
    ]
    if not hits:
        lines.extend(["_No catalog videos matched this cluster yet._", "", CLUSTER_END, ""])
        return "\n".join(lines)

    lines.extend(
        [
            "| video_id | title | source | band | transcript |",
            "|---|---|---|---|---|",
        ]
    )
    shown = sorted(
        hits,
        key=lambda v: (0 if v.status == "TRANSCRIPT_VERIFIED" else 1, v.popularity_rank or 10**9),
    )[:40]
    for video in shown:
        title = (video.title or "").replace("|", "/")
        lines.append(
            f"| `{video.video_id}` | {title} | {_source_tag(video)} | "
            f"{video.relevance_band or ''} | {video.status} |"
        )
    if len(hits) > 40:
        lines.append(f"| … | {len(hits) - 40} more in catalog | | | |")
    lines.extend(["", CLUSTER_END, ""])
    return "\n".join(lines)


def stub_body(cluster: Any, payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {cluster.title}",
            "",
            "**Status:** `HYPOTHESIS` / `UNVALIDATED` / `STUB`",
            "**Layer:** do not collapse `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS`",
            "**Compliance:** education ≠ proof. Not investment advice. No guaranteed profits.",
            "See [`docs/COMPLIANCE.md`](../../../../docs/COMPLIANCE.md).",
            "",
            "Production Dhan indicators stay Dhan-only unless `config/workspace.yaml`",
            "`implementation.indicators` is not `dhan_only`. Videos tagged `EXTERNAL_RESEARCH`",
            "are ideas only.",
            "",
            "## Catalog cluster (auto)",
            "",
            render_cluster_block(cluster, payload),
            "## SOURCE_FACT (team 01 — fill from transcripts)",
            "",
            "_Empty until research extracts claims with video_id + timestamps._",
            "",
            "## VALIDATION (teams 02/03 — books from workspace.yaml)",
            "",
            "_Empty. Books listed in `config/workspace.yaml` `sources.books` are VALIDATION only._",
            "",
            "## HYPOTHESIS (team 04 — per-topic spec, not one blob)",
            "",
            "_Empty. Do not claim edge. Mark UNVALIDATED until backtest + review._",
            "",
            "## Linked candidates",
            "",
            "See [`../MASTER_STRATEGY_PLAN.md`](../MASTER_STRATEGY_PLAN.md) if a STRAT-ID already covers this topic.",
            "",
        ]
    )


def upsert_topic_file(path: Path, cluster: Any, payload: dict[str, Any]) -> str:
    block = render_cluster_block(cluster, payload)
    if not path.is_file():
        path.write_text(stub_body(cluster, payload), encoding="utf-8")
        return "created"
    text = path.read_text(encoding="utf-8")
    if CLUSTER_START in text and CLUSTER_END in text:
        start = text.index(CLUSTER_START)
        end = text.index(CLUSTER_END) + len(CLUSTER_END)
        # render_cluster_block already includes markers
        new_text = text[:start] + block.rstrip() + text[end:]
        path.write_text(new_text, encoding="utf-8")
        return "updated"
    path.write_text(text.rstrip() + "\n\n## Catalog cluster (auto)\n\n" + block, encoding="utf-8")
    return "appended"


def write_topics_index(
    directory: Path,
    grouped: dict[str, dict[str, Any]],
    *,
    workspace_path: str,
) -> None:
    lines = [
        "# Topic strategy documents",
        "",
        "**Status:** stubs / `UNVALIDATED` / `HYPOTHESIS`. Not `RESEARCH_READY_FOR_PROGRAMMING`.",
        "One markdown file per topic. Agents cluster videos here; they do **not** dump all",
        "transcripts into a single blob.",
        "",
        f"Source channels and books: [`{workspace_path}`](../../../../config/workspace.yaml).",
        "Customer switches YouTube by changing a URL (or `enabled`) in that file.",
        "",
        "Refresh cluster tables from the current catalog (no YouTube scrape):",
        "",
        "```bash",
        "cd teams/01_research/youtube",
        "python -m src topics",
        "```",
        "",
        "Coded candidates (still UNVALIDATED): [`../candidates/`](../candidates/).",
        "Pipeline: [`../../../01_research/docs/TOPIC_STRATEGY_PIPELINE.md`](../../../01_research/docs/TOPIC_STRATEGY_PIPELINE.md).",
        "",
        "| Topic | File | Catalog hits | Verified transcripts |",
        "|---|---|---:|---:|",
    ]
    for topic_id, payload in grouped.items():
        cluster = payload["cluster"]
        rel = f"{_slug(cluster.id)}.md"
        lines.append(
            f"| {cluster.title} | [`{rel}`]({rel}) | {len(payload['videos'])} | "
            f"{len(payload['verified'])} |"
        )
    lines.extend(
        [
            "",
            "Template: [`_TEMPLATE.md`](_TEMPLATE.md).",
            "",
        ]
    )
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "README.md").write_text("\n".join(lines), encoding="utf-8")


def run_topic_cluster(settings: Settings, videos: list[VideoRecord]) -> dict[str, Any]:
    workspace = settings.workspace
    clusters = list(getattr(getattr(workspace, "pipeline", None), "topic_clusters", None) or [])
    grouped = cluster_videos(videos, clusters)
    out_dir = settings.strategy_docs_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    actions: dict[str, str] = {}
    for topic_id, payload in grouped.items():
        cluster = payload["cluster"]
        path = out_dir / f"{_slug(cluster.id)}.md"
        actions[topic_id] = upsert_topic_file(path, cluster, payload)
    ws_rel = "config/workspace.yaml"
    if workspace is not None:
        try:
            ws_rel = str(workspace.path.relative_to(settings.repo_root))
        except ValueError:
            ws_rel = str(workspace.path)
    write_topics_index(out_dir, grouped, workspace_path=ws_rel)
    return {
        "topics": len(grouped),
        "actions": actions,
        "output_dir": str(out_dir.relative_to(settings.repo_root)),
    }
