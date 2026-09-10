"""Counsel job templates. Cursor codes; Gemini/OpenAI reason on cited facts.

Each job says: when to use it, which details to collect, what is forbidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CounselJob:
    job_id: str
    role: str
    title: str
    when: str
    need: tuple[str, ...]
    how_to_get: str
    output: str
    keywords: tuple[str, ...]
    system: str
    missing_ok: bool = False
    extra_slots: tuple[str, ...] = field(default_factory=tuple)


JOBS: dict[str, CounselJob] = {}


def _add(job: CounselJob) -> None:
    JOBS[job.job_id] = job


_add(
    CounselJob(
        job_id="SIGNAL_REVIEW",
        role="review",
        title="Review our call — do not invent a signal",
        when="The desk already has a paper lean. Counsel checks our reasoning only.",
        need=(
            "underlying (NIFTY|BANKNIFTY|SENSEX)",
            "session_kind (NORMAL|NEWS_DAY|EXPIRY or unknown)",
            "our_call (BUY_CE|BUY_PE|HOLD + stage WATCH|EARLY|CONFIRMED — already decided)",
            "our_why (desk bullets — why we took this call)",
            "cited_tape (INDEX last and/or ATM LTP/PCR/OI wall — or say missing)",
            "mix_or_strat_id (MIX-LEAN-* / MIX-DEFAULT-BUY / STRAT-00x)",
        ),
        how_to_get="Desk snapshot + our written why. Never invent a new CE/PE. Never invent LTP.",
        output=(
            "AGREE | DISAGREE | AGREE_WITH_CAVEATS. "
            "2–4 bullets on whether our why matches the cited tape. "
            "Suggestions only (stage, hold, more data) — do not output a replacement signal. "
            "No win rate."
        ),
        keywords=(
            "buy",
            "sell",
            "ce",
            "pe",
            "hold",
            "signal",
            "ticket",
            "lean",
            "agree",
            "reasoning",
            "review our",
        ),
        system=(
            "You are a second-opinion reviewer, not a signal generator. "
            "The desk already chose our_call. Do NOT pick BUY_CE / BUY_PE / HOLD as a new call. "
            "Judge the reasoning: does our_why follow from cited_tape? "
            "If tape is thin, say DATA_INSUFFICIENT and suggest what to gather — still do not invent a side. "
            "Credit/sell as customer default is out of scope. No live orders. No win rates."
        ),
    )
)
_add(
    CounselJob(
        job_id="VALIDATE_GATHER",
        role="validate",
        title="Is gather enough to speak",
        when="Signals are vetoed or DATA_INSUFFICIENT and you need an honest gap list.",
        need=(
            "what_we_have (INDEX 1m? ATM snapshot? news?)",
            "what_the_recipe_asks (FUT 3m, greeks, OF, premium bars)",
            "session_kind",
        ),
        how_to_get="candidate_audit / paper evaluators / CONTINUE_NEXT_CHAT gather notes.",
        output="Keep / park / proxy. Do not delete STRAT-001–014. No fake fills.",
        keywords=("data", "insufficient", "veto", "gather", "gap", "validate"),
        system="Honesty over a ticket. Unbound PARKED DI is correct. INDEX 1m is not FUT 3m.",
    )
)
_add(
    CounselJob(
        job_id="REVIEW_NOTES",
        role="review",
        title="09 notes — not a five-pass",
        when="A change or HANDOFF needs a second opinion.",
        need=("what_changed", "keep_all_ok (yes/no)", "promote_claimed (yes/no)"),
        how_to_get="git diff summary + HANDOFF block. Notes ≠ RESEARCH_READY.",
        output="ACCEPT / REJECT / UNKNOWN. One paragraph. No promote.",
        keywords=("review", "handoff", "five-pass", "09", "notes"),
        system="09 review counsel. Notes only. Gate stays unset unless founder+five-pass.",
    )
)
_add(
    CounselJob(
        job_id="CONFIRM_STAGE",
        role="confirm",
        title="WATCH vs EARLY vs CONFIRMED",
        when="Someone wants to upgrade the stage.",
        need=("current_stage", "5m_st_macd_fact (present|absent)", "clock_ok (007/009)"),
        how_to_get="SIGNAL_STAGING.md + clock helpers. 5m ST/MACD is confirm-or-kill, not entry.",
        output="Allowed stage + why. Never invent CONFIRMED.",
        keywords=("confirmed", "early", "watch", "stage", "confirm"),
        system="Staging counsel. EARLY is a valid ticket. CONFIRMED needs confirm-or-kill facts.",
    )
)
_add(
    CounselJob(
        job_id="WEB_FACT_PACK",
        role="counsel",
        title="What to look up next (no scrape)",
        when="You need latest public context before reasoning.",
        need=("question", "already_have"),
        how_to_get="Cursor web search / desk_intel RSS / NSE circulars. Do not scrape Google SERPs.",
        output="3 lookup queries + fields to copy back as cited facts. No invented quotes.",
        keywords=("web", "latest", "news", "google", "scrape", "lookup"),
        system="Pack a search list only. You do not browse. Founder/Cursor fetches, then SIGNAL_REVIEW.",
        extra_slots=("question",),
    )
)
_add(
    CounselJob(
        job_id="DHANHQ_BIND",
        role="counsel",
        title="DhanHQ video → bind checklist",
        when="Founder watched / will watch an @DhanHQ video.",
        need=("video_id_or_title", "spoken_tf", "buy_or_sell_said", "indicator_names"),
        how_to_get="@DhanHQ transcript EN + SOURCE_FACT packet. External channels are out.",
        output="KEEP as STRAT overlay / new MIX-* / PARK. No STRAT-015+.",
        keywords=("dhanhq", "transcript", "bind", "video", "teacher"),
        system="01+04 bind counsel. DHAN-DERIVED vs PROJECT-DERIVED. KEEP_ALL on 001–014.",
    )
)
_add(
    CounselJob(
        job_id="DHAN_API_REVIEW",
        role="review",
        title="Does this Dhan call match the desk book",
        when="Someone wants a new HQ endpoint, TF, or skill-script pattern.",
        need=(
            "proposed_path_or_sdk (exact /v2 path or dhanhq method)",
            "what_data_they_claim (field names)",
            "desk_use (signal|warehouse|backtest|order|other)",
        ),
        how_to_get="teams/03_phd_market/docs/DHAN_API_END_TO_END.md + official dhanhq.co/docs/v2/. Do not invent fields.",
        output=(
            "USE / STORE / READ-ONLY later / NEVER. "
            "Cite the official field list. Flag fake TFs (3m/1w REST). "
            "Never approve place/modify/cancel/super/forever. No CE/PE from this job."
        ),
        keywords=(
            "dhan api",
            "endpoint",
            "optionchain",
            "marketfeed",
            "charts",
            "skill.md",
            "dhanhq",
            "rest",
        ),
        system=(
            "You review API usage against the cited desk book and official v2 docs. "
            "Do not invent REST fields, lots, or intervals. "
            "Intraday intervals are 1/5/15/25/60 only. Orders are NEVER. "
            "Do not output BUY_CE / BUY_PE. No win rates."
        ),
    )
)
_add(
    CounselJob(
        job_id="COUNSEL_NEXT",
        role="counsel",
        title="What to do next",
        when="Unsure of the next desk move.",
        need=("left_off", "gate_state"),
        how_to_get="CONTINUE_NEXT_CHAT.md + canvas /cleanup.",
        output="One next action. PAPER. No npm/paper restart unless founder asked.",
        keywords=("next", "what now", "priority", "plan"),
        system="00 orchestrator counsel. Customer profitability over SDLC theater.",
    )
)


_ALIASES = {
    "SIGNAL_BUY_SELL": "SIGNAL_REVIEW",  # old id — review only, never generate
}


def get_job(job_id: str) -> CounselJob | None:
    key = (job_id or "").strip().upper()
    key = _ALIASES.get(key, key)
    return JOBS.get(key)


def list_jobs() -> list[dict[str, str]]:
    return [
        {
            "job_id": j.job_id,
            "title": j.title,
            "when": j.when,
            "role": j.role,
            "need": "; ".join(j.need),
            "how_to_get": j.how_to_get,
        }
        for j in JOBS.values()
    ]
