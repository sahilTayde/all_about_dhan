from trading_agents_india.counsel_jobs import missing_slots, route_job, run_job
from trading_agents_india.counsel_templates import JOBS, get_job


def test_route_buy_sell() -> None:
    job = route_job("review our buy CE reasoning and signal")
    assert job.job_id == "SIGNAL_REVIEW"


def test_route_gather_gap() -> None:
    assert route_job("veto data insufficient gather").job_id == "VALIDATE_GATHER"


def test_route_default_next() -> None:
    assert route_job("asdf").job_id == "COUNSEL_NEXT"


def test_dry_job_lists_missing_slots() -> None:
    job = get_job("SIGNAL_REVIEW")
    assert job is not None
    miss = missing_slots(job, {"underlying": "NIFTY"})
    assert "our_call" in miss
    pack = run_job("SIGNAL_REVIEW", slots={"underlying": "NIFTY"}, dry=True)
    assert pack["dry"] is True
    assert pack["job_id"] == "SIGNAL_REVIEW"
    assert get_job("SIGNAL_BUY_SELL") is job
    assert "why" in pack["how_to_get"].lower() or "desk" in pack["how_to_get"].lower()


def test_all_jobs_registered() -> None:
    assert "SIGNAL_REVIEW" in JOBS
    assert "WEB_FACT_PACK" in JOBS
    assert "DHAN_API_REVIEW" in JOBS
