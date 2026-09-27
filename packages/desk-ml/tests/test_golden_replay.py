"""Legacy replay goldens and the replay determinism contract.

The goldens were generated on this branch and verified byte-identical to main (0375e94) on the same
fixtures; any change to a legacy golden must be explained in the PR. Regenerate with
``python -m desk_ml.testing.canonical --write-goldens``.
"""

from __future__ import annotations

import difflib
import os
import subprocess
import sys
import sys as _sys
from datetime import datetime

import pytest

from desk_ml.testing import canonical as canon


def _diff(a: bytes, b: bytes) -> str:
    return "\n".join(list(difflib.unified_diff(a.decode().split(","), b.decode().split(","), lineterm=""))[:40])


@pytest.mark.parametrize("flag", ["off", "on"])
@pytest.mark.parametrize("name", canon.GOLDEN_FIXTURES)
def test_legacy_replay_matches_golden(name, flag):
    want = (canon.GOLDEN_DIR / f"{name}.legacy.json").read_bytes()
    got = canon.golden_dump(name, flag=flag)
    assert got == want, f"{name} flag {flag} drifted from the legacy golden:\n{_diff(want, got)}"


def test_goldens_trade():
    import json

    for name in canon.GOLDEN_FIXTURES:
        blob = json.loads((canon.GOLDEN_DIR / f"{name}.legacy.json").read_text())
        n = sum(d["n_trades"] for d in blob["per_index"].values())
        assert n >= 5, f"{name} golden has {n} trades; a fixture that does not trade proves nothing"


def test_committed_fixtures_are_generated_not_hand_edited():
    for fname, data in canon.regenerate_all().items():
        assert (canon.FIXTURE_DIR / fname).read_bytes() == data, f"{fname} differs from its generator output"
        assert b'"synthetic":true' in data or b"Synthetic" in data


def _refuse(*_a, **_k):
    raise AssertionError("engine path called repo_root(): replays must use their explicit data root")


def test_engine_never_calls_repo_root(monkeypatch):
    import desk_ml.persist as persist

    real = persist.repo_root
    monkeypatch.setattr(persist, "repo_root", _refuse)
    for mod in list(_sys.modules.values()):
        if getattr(mod, "__name__", "").startswith(("desk_ml", "desk.", "boss", "analysts")) and getattr(mod, "repo_root", None) is real:
            monkeypatch.setattr(mod, "repo_root", _refuse)
    for flag in ("off", "on"):
        want = (canon.GOLDEN_DIR / "syn_nifty_live_s23.legacy.json").read_bytes()
        assert canon.golden_dump("syn_nifty_live_s23", flag=flag) == want


def test_replay_ignores_the_wall_clock(monkeypatch):
    import desk_ml.paper_scalp as ps

    class Future(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2031, 3, 3, 3, 3, 3, tzinfo=tz)

    monkeypatch.setattr(ps, "datetime", Future)
    want = (canon.GOLDEN_DIR / "syn_nifty_live_s23.legacy.json").read_bytes()
    assert canon.golden_dump("syn_nifty_live_s23") == want


def test_replay_is_the_same_from_any_cwd_and_home(tmp_path):
    code = "import sys; from desk_ml.testing import canonical as c; sys.stdout.buffer.write(c.golden_dump('syn_nifty_live_s23'))"
    outs = []
    for sub in ("a", "b"):
        cwd = tmp_path / sub
        cwd.mkdir()
        env = {**os.environ, "HOME": str(cwd), "TZ": "America/Chicago" if sub == "a" else "Asia/Tokyo"}
        outs.append(subprocess.run([sys.executable, "-c", code], cwd=cwd, env=env, capture_output=True, check=True).stdout)
    assert outs[0] == outs[1] == (canon.GOLDEN_DIR / "syn_nifty_live_s23.legacy.json").read_bytes()


def test_offline_replay_writes_nothing(tmp_path, monkeypatch):
    """write=False: the data root is byte-for-byte unchanged (no model log, no alerts, no board)."""
    import desk_ml.paper_scalp as ps

    monkeypatch.setattr(ps, "resolve_lot_size", lambda und, root=None: (65, "fixture"))
    monkeypatch.setattr(ps, "load_index_closes", lambda u, root=None: {})

    fx = canon.load_fixture("syn_nifty_live_s23")
    recon = tmp_path / "data" / "recon"
    recon.mkdir(parents=True)
    (recon / "founder_trade_underlyings.json").write_text('{"trade_underlyings": ["NIFTY"]}')
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    ps.replay_paper_scalp(root=tmp_path, underlyings=("NIFTY",), triples_by_und=fx["triples"],
                          session_ist_date=fx["day"], write=False, live_session=True)
    assert sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*")) == before
