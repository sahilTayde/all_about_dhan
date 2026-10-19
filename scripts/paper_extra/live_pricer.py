"""Live premium pricer for paper_extra OPEN rows (2026-10-19, Sahil option A). PAPER ONLY, read-only on the V2 tape.
Marks every open row at the BID (exit side; mid/ltp never used to fire) from data/tape/v2/<day>/depth_quotes.jsonl, polled every ~3 s.
Fires STOP / TRAIL / TARGET on the bid: stop = entry x (1-S); after the bid high-water reaches entry x (1+S) the stop moves to
max(entry, hw x (1-S)); target = entry x (1+T); stop is checked before target. Fill = the triggering bid. 15:15 IST safety close at the bid.
A row whose last bid is older than STALE_S seconds is 'stale' and the runner falls back to the 1-minute-close rule."""
import json, os
from datetime import datetime

STALE_S = 10.0


def iid_of(und: str, exp: str, strike, side: str) -> str:
    return f"{'NSE_FNO' if und == 'NIFTY' else 'BSE_FNO'}:{und}:{exp}:{int(float(strike))}:{side}"


class LiveTrade:
    def __init__(self, key, iid, entry, stop_frac, target_frac, hw=None, safety_hhmmss="15:15:00", not_before=None):
        self.key, self.iid, self.entry = key, iid, float(entry)
        self.not_before = not_before   # ISO ts: quotes earlier than this (before entry / before restart) are ignored (2026-10-19 live bug)
        self.S, self.T = float(stop_frac), float(target_frac)
        self.hw = max(float(hw or entry), self.entry)
        self.safety = safety_hhmmss
        self.last_bid = None; self.last_ts = None
        self.closed = None   # dict(exit_px, exit_ts, why)
        self.stop_floor = None   # 2026-10-19 Sahil manual lock (e.g. +15%); stop never below this
        self.trail_gap = None    # 2026-10-19 Sahil: trail this fraction under the bid high-water (0.15 => stop = hw x 0.85)

    @property
    def stop(self) -> float:
        s = self.entry * (1 - self.S)
        if self.hw >= self.entry * (1 + self.S):
            s = max(s, self.entry, self.hw * (1 - self.S))
        if self.stop_floor:
            s = max(s, float(self.stop_floor))
        if self.trail_gap:
            s = max(s, self.hw * (1 - float(self.trail_gap)))
        return s

    @property
    def target(self) -> float:
        return self.entry * (1 + self.T)

    def on_quote(self, bid, ts: str):
        """bid: best bid (None/0 -> ignored, no fire). ts: ISO time with +05:30. Returns the close dict when this quote closes the trade."""
        if self.closed is not None or not bid or bid <= 0:
            return None
        if self.not_before and ts[:19] < self.not_before[:19]:
            return None
        self.last_bid, self.last_ts = float(bid), ts
        if ts[11:19] >= self.safety:
            self.closed = dict(exit_px=float(bid), exit_ts=ts, why="SAFETY_1515"); return self.closed
        st = self.stop   # level BEFORE this quote updates the high-water (no same-tick look-ahead)
        if bid <= st:
            self.closed = dict(exit_px=float(bid), exit_ts=ts, why="STOP" if st < self.entry - 1e-9 else "TRAIL"); return self.closed
        if bid >= self.target:
            self.closed = dict(exit_px=float(bid), exit_ts=ts, why="TARGET"); return self.closed
        self.hw = max(self.hw, float(bid))
        return None

    def stale(self, now_ts: str) -> bool:
        if self.last_ts is None:
            return True
        return (datetime.fromisoformat(now_ts) - datetime.fromisoformat(self.last_ts)).total_seconds() > STALE_S

    def to_json(self):
        return dict(not_before=self.not_before, key=list(self.key), iid=self.iid, entry=self.entry, S=self.S, T=self.T, hw=self.hw, last_bid=self.last_bid,
                    last_ts=self.last_ts, closed=self.closed, stop_floor=self.stop_floor, trail_gap=self.trail_gap)

    @classmethod
    def from_json(cls, d):
        t = cls(tuple(d["key"]), d["iid"], d["entry"], d["S"], d["T"], d["hw"], not_before=d.get("not_before")); t.last_bid, t.last_ts, t.closed = d["last_bid"], d["last_ts"], d["closed"]
        t.stop_floor = d.get("stop_floor")
        t.trail_gap = d.get("trail_gap")
        return t


class DepthTail:
    """Incremental reader of depth_quotes.jsonl (keeps a byte offset; only complete lines). Yields (iid, bid, ts)."""
    def __init__(self, path, start_at_end=False):
        self.path = str(path); self.off = 0
        if start_at_end and os.path.exists(self.path):
            self.off = os.path.getsize(self.path)

    def read(self, want=None):
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, "rb") as f:
            f.seek(self.off); buf = f.read()
        end = buf.rfind(b"\n")
        if end < 0:
            return []
        self.off += end + 1
        for line in buf[:end].split(b"\n"):
            try:
                j = json.loads(line); p = j.get("payload") or {}
            except ValueError:
                continue
            iid = p.get("instrument_id")
            if not iid or (want is not None and iid not in want):
                continue
            out.append((iid, p.get("bid"), j.get("timestamp") or p.get("exchange_ts")))
        return out
