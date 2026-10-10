"""Traded-strike set: ATM, ITM100, ITM200, OTM100, OTM200 on CE and PE, plus index and future.

ITM wings sit in the money (CE below ATM, PE above ATM). OTM wings are the
mirror: two listed strikes on each side, CE above ATM and PE below ATM, using
the same 100 / 200 point offsets. The ``rule`` field on the existing snapshot
row identifies the wing (no new columns).

Re-centred when spot moves more than half a strike step (plus hysteresis) away from the
current ATM. Strikes that leave the set keep streaming for ``retention_s`` (10 minutes);
instruments with an open position are never dropped.

Steady-state count per underlying: index + future + 10 option wings = 12.
Default NIFTY + SENSEX = 24. After a recentre, old option wings stay up to 10
minutes, so a dual-underlying book can briefly hold 44. Dhan allows 5,000 ids
per socket and 100 ids per subscribe JSON (see ``DHAN_FEED_LIMITS``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from marketdata.instruments import Instrument, Universe

# (rule, ITM points). Negative = OTM: CE = ATM − offset (above), PE = ATM + offset (below).
RULES: tuple[tuple[str, int], ...] = (
    ("ATM", 0),
    ("ITM100", 100),
    ("ITM200", 200),
    ("OTM100", -100),
    ("OTM200", -200),
)
# 2 sides × 5 rules. Index + future make the per-underlying steady set 12.
OPTION_WINGS = 2 * len(RULES)
STEADY_INSTRUMENTS = 1 + 1 + OPTION_WINGS  # index + future + 10 options
# Dhan live-feed connection caps (SOURCE_FACT: teams/03_phd_market/docs/DHAN_API_END_TO_END.md).
DHAN_FEED_LIMITS = {"sockets": 5, "instruments_per_socket": 5000, "ids_per_subscribe": 100}


@dataclass
class Change:
    atm: int | None
    subscribe: list[Instrument] = field(default_factory=list)
    unsubscribe: list[Instrument] = field(default_factory=list)
    recentred: bool = False


def _no_positions() -> set[str]:
    return set()


class StrikeSet:
    def __init__(
        self,
        universe: Universe,
        *,
        retention_s: float = 600.0,
        max_instruments: int = 100,
        hysteresis: float = 0.2,
        open_positions: Callable[[], set[str]] = _no_positions,
    ) -> None:
        self.universe = universe
        self.retention_s = retention_s
        self.max_instruments = max_instruments
        self.hysteresis = hysteresis
        self.open_positions = open_positions
        self.atm: int | None = None
        self.current: dict[str, tuple[str, str]] = {}
        self.retained: dict[str, float] = {}
        self.subscribed: dict[str, Instrument] = {}
        self._strikes = sorted({k[0] for k in universe.options})
        self._by_id = {i.instrument_id: i for i in universe.all_instruments()}

    def nearest_strike(self, spot: float) -> int:
        return min(self._strikes, key=lambda s: (abs(s - spot), s))

    def targets(self, atm: int) -> dict[str, tuple[str, str]]:
        out: dict[str, tuple[str, str]] = {}
        for rule, itm in RULES:
            for side, strike in (("CE", atm - itm), ("PE", atm + itm)):
                inst = self.universe.options.get((strike, side))
                if inst is not None:
                    out[inst.instrument_id] = (rule, side)
        return out

    def rule_for(self, instrument_id: str) -> tuple[str, str] | None:
        return self.current.get(instrument_id)

    def update(self, spot: float, now_s: float) -> Change:
        change = Change(atm=self.atm)
        want: list[str] = []
        if self.atm is None:
            want += [self.universe.index.instrument_id]
            if self.universe.future:
                want.append(self.universe.future.instrument_id)
        step = self.universe.strike_step
        if self.atm is None or abs(spot - self.atm) > step * (0.5 + self.hysteresis):
            atm = self.nearest_strike(spot)
            if atm != self.atm:
                new = self.targets(atm)
                for iid in self.current:
                    if iid not in new:
                        self.retained[iid] = now_s + self.retention_s
                for iid in new:
                    self.retained.pop(iid, None)
                want += list(new)
                change.recentred = self.atm is not None
                self.current, self.atm = new, atm
                change.atm = atm

        keep = self.open_positions()
        want += [iid for iid in keep if iid in self._by_id]
        pending = [iid for iid in dict.fromkeys(want) if iid not in self.subscribed]
        for iid, expires in sorted(self.retained.items(), key=lambda kv: kv[1]):
            over_cap = len(self.subscribed) + len(pending) > self.max_instruments
            if (expires <= now_s or over_cap) and iid not in keep:
                del self.retained[iid]
                inst = self.subscribed.pop(iid, None)
                if inst is not None:
                    change.unsubscribe.append(inst)
        for iid in pending:
            if len(self.subscribed) < self.max_instruments:
                self.subscribed[iid] = self._by_id[iid]
                change.subscribe.append(self._by_id[iid])
        return change
