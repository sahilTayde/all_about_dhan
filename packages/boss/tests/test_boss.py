"""Boss: votes over the bus, one crashing / hanging analyst cannot break it, legacy vote order kept."""

import tempfile
import time
from pathlib import Path

import pytest

import desk_ml.paper_scalp as ps
from analysts import ABSTAIN, Analyst, AnalystRoom, Vote, build
from boss import Boss
from desk_ml.event_parity import compare_boards, fixture_replay_kwargs, load_fixture
from desk_ml.event_path import EventSession
from desk_ml.picker import Vote as PickerVote
from events import MemoryBus

FIXTURE = Path(__file__).resolve().parents[2] / "desk-ml" / "tests" / "fixtures" / "synthetic_session_nifty.json"
N_TICKS = 700


class Crashes(Analyst):
    analyst_id = "TEST-CRASH"

    def vote(self, context):
        raise RuntimeError("analyst bug")


class HangsSometimes(Analyst):
    analyst_id = "TEST-HANG"

    def vote(self, context):
        if context.i % 150 == 0:
            time.sleep(0.3)
        return Vote(self.analyst_id, "BUY_CE", 1.0, "would sway the picker if it were not late")


@pytest.fixture()
def fx(monkeypatch):
    blob = load_fixture(FIXTURE)
    blob["triples"] = blob["triples"][:N_TICKS]
    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})
    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: (int(blob["lot_size"]), "fixture"))
    return blob


def _replay(fx, **kw):
    with tempfile.TemporaryDirectory() as tmp:
        return ps.replay_paper_scalp(**fixture_replay_kwargs(fx, Path(tmp)), write=False, **kw)


def test_crashing_and_hanging_analysts_do_not_break_the_boss(fx):
    old = _replay(fx, use_event_bus=False)
    room = AnalystRoom([*build(), Crashes()], timeout_s=0.1)
    session = EventSession(room=room)
    new = _replay(fx, event_session=session)
    summary = new["event_bus"]
    assert summary["handler_errors"] == []
    assert room.stats["errors"] == summary["events"]["REQUEST_VOTES"]  # crashed every tick, ABSTAIN each time
    assert compare_boards(old, new) == []  # ABSTAIN is silent: same picker, same trades
    assert len([r for r in old["closed_trades"] if r["filled"]]) > 0
    session.close()


def test_late_vote_is_abstain_not_a_block(fx):
    fx["triples"] = fx["triples"][:320]
    room = AnalystRoom([*build(), HangsSometimes()], timeout_s=0.05)
    session = EventSession(room=room)
    new = _replay(fx, event_session=session)
    assert room.stats["timeouts"] >= 1 and new["event_bus"]["handler_errors"] == []
    assert new["event_bus"]["latency_p99_ms"]["boss_decision"] < 1000.0
    session.close()


def test_one_vote_per_analyst_per_request_and_ordered_like_the_room():
    bus, contexts = MemoryBus(), {}
    room = AnalystRoom(build())
    room.attach(bus, contexts)
    boss = Boss(bus, engine=None, steps={}, signals={}, contexts=contexts, analyst_ids=room.analyst_ids)
    votes = [Vote(a, ABSTAIN, 0.0, "x", {"legacy": True, "reason_class": "SILENT", "silent": True, "side": None})
             for a in reversed(room.analyst_ids)]
    extra = PickerVote(source="LAB-X", side="CE", reason_class="CONFIRM", silent=False, detail="lab")
    out = boss.legacy_votes(votes, {"extra": [extra]})
    sources = [v.source for v in out]
    assert sources[: sources.index("LAB-X")] == room.analyst_ids[: room.analyst_ids.index("STRAT-001")]
    assert sources[sources.index("LAB-X") + 1] == "STRAT-001" and len(out) == len(room.analyst_ids) + 1
    room.close()
