"""Pick a counsel template and run Gemini/OpenAI on filled slots."""

from __future__ import annotations

from typing import Any, Optional

from trading_agents_india.counsel import complete
from trading_agents_india.counsel_templates import JOBS, CounselJob, get_job, list_jobs


def route_job(text: str) -> CounselJob:
    """Pick one template from founder/agent wording. Default COUNSEL_NEXT."""
    blob = (text or "").lower()
    scored: list[tuple[int, CounselJob]] = []
    for job in JOBS.values():
        hits = sum(1 for kw in job.keywords if kw in blob)
        if hits:
            scored.append((hits, job))
    if not scored:
        job = get_job("COUNSEL_NEXT")
        assert job is not None
        return job
    scored.sort(key=lambda x: (-x[0], x[1].job_id))
    return scored[0][1]


def _slot_block(slots: dict[str, str]) -> str:
    lines = []
    for k, v in slots.items():
        val = (v or "").strip() or "DATA_INSUFFICIENT"
        lines.append(f"- {k}: {val}")
    return "\n".join(lines)


def missing_slots(job: CounselJob, slots: dict[str, str]) -> list[str]:
    miss = []
    for need in job.need:
        key = need.split(" ", 1)[0].split("(")[0].strip()
        if not (slots.get(key) or "").strip():
            miss.append(key)
    return miss


def run_job(
    job_id: str,
    *,
    slots: Optional[dict[str, str]] = None,
    extra_prompt: str = "",
    dry: bool = False,
) -> dict[str, Any]:
    job = get_job(job_id)
    if job is None:
        return {"ok": False, "data_gaps": [f"UNKNOWN job_id={job_id}"], "jobs": list_jobs()}
    slots = {str(k): str(v) for k, v in (slots or {}).items()}
    miss = missing_slots(job, slots)
    facts = (
        f"JOB {job.job_id}: {job.title}\n"
        f"When: {job.when}\n"
        f"Collect via: {job.how_to_get}\n"
        f"Output shape: {job.output}\n"
        f"Slots:\n{_slot_block(slots)}\n"
    )
    prompt = (
        job.system
        + "\n\nFollow output shape. If a required slot is DATA_INSUFFICIENT, say so — do not invent Dhan tape.\n"
        + (extra_prompt.strip() + "\n" if extra_prompt.strip() else "")
    )
    if dry:
        return {
            "ok": True,
            "dry": True,
            "job_id": job.job_id,
            "role": job.role,
            "missing_slots": miss,
            "need": list(job.need),
            "how_to_get": job.how_to_get,
            "facts_pack": facts,
            "provider": None,
            "text": "",
        }
    result = complete(prompt, role=job.role, facts=facts)
    result["job_id"] = job.job_id
    result["missing_slots"] = miss
    result["how_to_get"] = job.how_to_get
    if miss:
        result.setdefault("data_gaps", []).append(
            "DATA_INSUFFICIENT: empty slots " + ",".join(miss)
        )
    return result
