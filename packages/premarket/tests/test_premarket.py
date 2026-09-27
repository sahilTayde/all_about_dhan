"""Pre-market service: fail-soft per source, structured context, pluggable markets. Synthetic fixtures only."""

from __future__ import annotations

import json
import shutil
import time
from datetime import date, datetime
from pathlib import Path

import pytest

from premarket.__main__ import main as cli
from premarket.service import build_context, load_config, render_brief, write_outputs
from premarket.sources import (FixtureFetcher, NoNetworkFetcher, Source, SourceResult, parse_feed, pivots,
                               register_source_type)

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic"
NOW = datetime.fromisoformat("2026-09-28T08:30:00+05:30")
DAY = date(2026, 9, 28)


def _ctx(**kw):
    base = dict(config=load_config(), fetcher=FixtureFetcher(FIX), root=FIX / "root", now=NOW, session_date=DAY)
    return build_context("india_index", **{**base, **kw})


def test_fixture_context_is_structured_and_marks_missing() -> None:
    c = _ctx()
    assert c["advisory_only"] is True and c["orders"] == "never" and c["blocks_trading"] is False
    assert c["layer"] == "HYPOTHESIS" and c["validated"] is False
    assert c["missing"] == ["gift_nifty", "bse_announcements"]
    assert "no free endpoint" in c["sources"]["gift_nifty"]["error"]
    assert c["bias"]["label"] == "BULLISH" and c["bias"]["n_inputs"] == 6 and c["bias"]["score"] == 4
    assert 0 < c["confidence"] < 1
    nifty = c["levels"]["NIFTY"]
    assert nifty["prev_day"]["date"] == "2026-09-25"
    assert nifty["oi_walls"]["call_wall_strike"] == 25050.0 and nifty["oi_walls"]["put_wall_strike"] == 24800.0
    assert "oi_walls" not in c["levels"]["SENSEX"]  # no SENSEX chain in the snapshot: level row still present
    assert c["flows"]["FII_NET_CR"] == 1500.0
    assert c["event_risk"]["label"] == "MEDIUM" and not c["hold_new_tickets_advice"]
    assert [h["title"] for h in c["headlines"]] == [
        "Synthetic: Fed officials signal patience as inflation data looms",
        "Synthetic: Asian markets open mixed; crude steady",
    ]  # older than 36h dropped
    assert c["generated_before_brief_by"] is True
    json.dumps(c, allow_nan=False)  # plain JSON
    brief = render_brief(c)
    assert "BULLISH" in brief and "Missing sources:** gift_nifty, bse_announcements" in brief


def test_everything_missing_still_writes_a_context(tmp_path: Path) -> None:
    c = _ctx(fetcher=NoNetworkFetcher(), root=tmp_path)
    assert c["coverage"] == 0.0 and len(c["missing"]) == len(c["sources"])
    assert c["bias"]["label"] == "UNKNOWN" and c["confidence"] == 0.0
    assert c["event_risk"]["label"] == "UNKNOWN"
    paths = write_outputs(c, tmp_path / "out")
    saved = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert saved["missing"] == c["missing"]
    assert Path(paths["brief"]).read_text(encoding="utf-8").startswith("# Pre-market brief")
    assert not list((tmp_path / "out").glob(".*.tmp"))


@register_source_type("test_boom")
class Boom(Source):
    def fetch(self, ctx):
        raise KeyError("unexpected bug inside a source")


@register_source_type("test_hang")
class Hang(Source):
    def fetch(self, ctx):
        time.sleep(float(self.params.get("sleep_s", 3)))
        return SourceResult(self.name, "OK", {})


def test_a_crashing_or_hanging_source_does_not_hold_the_others() -> None:
    cfg = load_config()
    cfg["deadline_s"] = 0.5
    m = cfg["markets"]["india_index"]
    m["sources"] = [*m["sources"], {"name": "boom", "type": "test_boom"}, {"name": "hang", "type": "test_hang"}]
    t0 = time.perf_counter()
    c = _ctx(config=cfg)
    assert time.perf_counter() - t0 < 2.5
    assert c["sources"]["boom"]["status"] == "MISSING" and "KeyError" in c["sources"]["boom"]["error"]
    assert c["sources"]["hang"]["status"] == "MISSING" and "deadline" in c["sources"]["hang"]["error"]
    assert c["sources"]["us_futures"]["status"] == "OK" and c["bias"]["label"] == "BULLISH"


def test_stale_quotes_are_flagged_and_left_out_of_the_bias() -> None:
    later = datetime.fromisoformat("2026-10-09T08:30:00+05:30")
    c = _ctx(now=later, session_date=later.date())
    assert c["sources"]["us_futures"]["status"] == "STALE"
    assert "us_futures" in c["stale"] and c["bias"]["label"] == "UNKNOWN"
    assert c["sources"]["prev_day_levels"]["status"] == "STALE"


def test_calendar_event_makes_risk_high_and_advises_hold() -> None:
    cfg = load_config()
    cfg["markets"]["india_index"]["event_risk"]["calendar"] = [{"date": "2026-09-28", "event": "RBI policy", "weight": 3}]
    c = _ctx(config=cfg)
    assert c["event_risk"]["label"] == "HIGH" and c["hold_new_tickets_advice"] is True
    assert "calendar: RBI policy" in c["event_risk"]["reasons"]


def test_another_market_reuses_the_source_types(tmp_path: Path) -> None:
    shutil.copy(FIX / "yahoo_DX-Y.NYB.json", tmp_path / "yahoo_DX-Y.NYB.json")
    shutil.copy(FIX / "yahoo_ES_F.json", tmp_path / "yahoo_EURUSD_X.json")
    shutil.copy(FIX / "rss_global_news_0.xml", tmp_path / "rss_fx_news_0.xml")
    cfg = {"deadline_s": 5, "markets": {"forex_majors": {
        "timezone": "Europe/London", "underlyings": ["EURUSD"],
        "sources": [{"name": "fx", "type": "yahoo_quotes", "symbols": {"EURUSD": "EURUSD=X", "DXY": "DX-Y.NYB"}},
                    {"name": "fx_news", "type": "rss", "role": "news", "urls": ["https://example.invalid/fx.xml"]}],
        "bias_rules": [{"metric": "DXY", "field": "change_pct", "sign": -1, "threshold": 0.3}],
        "min_bias_inputs": 1, "event_risk": {"keywords": {"fed": 1}}}}}
    c = build_context("forex_majors", config=cfg, fetcher=FixtureFetcher(tmp_path), root=tmp_path, now=NOW)
    assert c["market"] == "forex_majors" and c["as_of"].endswith("+01:00")
    assert c["bias"]["label"] == "BULLISH" and c["missing"] == []
    assert c["event_risk"]["label"] == "LOW" and c["event_risk"]["score"] == 1
    assert set(c["intermarket"]) == {"EURUSD", "DXY"}


def test_unknown_market_or_source_type_is_a_config_error() -> None:
    with pytest.raises(ValueError):
        build_context("crypto", config={"markets": {}})
    with pytest.raises(ValueError):
        build_context("x", config={"markets": {"x": {"sources": [{"name": "a", "type": "nope"}]}}})


def test_cli_offline_writes_and_exits_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli(["--offline", "--root", str(tmp_path), "--out-dir", str(tmp_path / "out"), "--date", "2026-09-28",
              "--now", "2026-09-28T08:30:00+05:30"])
    assert rc == 0
    assert (tmp_path / "out" / "india_index_2026-09-28.json").is_file()
    assert (tmp_path / "out" / "india_index_latest.json").is_file()
    assert "Missing sources:" in capsys.readouterr().out


def test_atom_feed_and_pivots() -> None:
    atom = (b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Synthetic  atom</title>'
            b'<link href="https://example.invalid/a"/><updated>2026-09-28T01:00:00Z</updated></entry></feed>')
    [item] = parse_feed(atom, "x")
    assert item == {"title": "Synthetic atom", "link": "https://example.invalid/a",
                    "published": "2026-09-28T01:00:00+00:00", "source": "x"}
    p = pivots(110.0, 90.0, 100.0)
    assert p == {"pivot": 100.0, "r1": 110.0, "s1": 90.0, "r2": 120.0, "s2": 80.0}
