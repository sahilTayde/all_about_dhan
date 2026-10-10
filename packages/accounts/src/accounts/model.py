"""Account row: account_id, kind, broker, status (architecture §5.6)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from accounts.errors import AccountSafetyError
from accounts.slots import (
    normalize_basket,
    normalize_journal_tag,
    normalize_portal_sub,
    normalize_slot,
    normalize_strategy_id,
    slot_payload,
)

KINDS = frozenset({"founder", "customer"})
BROKERS = frozenset({"paper", "shadow"})
LIVE_BROKERS = frozenset({"dhan", "live", "limited_live"})
STATUSES = frozenset({"active", "disabled", "halted"})
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _norm(raw: object) -> str:
    return str(raw or "").strip().lower()


@dataclass(frozen=True)
class Account:
    """One paper/shadow book. No broker credentials. No live path."""

    account_id: str
    kind: str
    broker: str
    status: str
    risk_budget_inr: int = 30000
    portal_sub: str = ""
    slot: str = ""
    journal_tag: str = ""
    strategy_id: str = ""
    basket: str = ""

    def __post_init__(self) -> None:
        aid = self.account_id.strip()
        if not _ID_RE.fullmatch(aid) or "|" in aid:
            raise AccountSafetyError(f"V2 accounts fail-closed: illegal account_id {self.account_id!r}")
        object.__setattr__(self, "account_id", aid)
        kind = _norm(self.kind)
        broker = _norm(self.broker)
        status = _norm(self.status)
        if kind not in KINDS:
            raise AccountSafetyError(f"V2 accounts fail-closed: kind {self.kind!r} is not founder|customer")
        if broker in LIVE_BROKERS:
            raise AccountSafetyError(f"V2 accounts fail-closed: broker {self.broker!r} is live and cannot load")
        if broker not in BROKERS:
            raise AccountSafetyError(f"V2 accounts fail-closed: broker {self.broker!r} is not paper|shadow")
        if status not in STATUSES:
            raise AccountSafetyError(f"V2 accounts fail-closed: status {self.status!r} is not active|disabled|halted")
        if (
            not isinstance(self.risk_budget_inr, int)
            or isinstance(self.risk_budget_inr, bool)
            or self.risk_budget_inr <= 0
        ):
            raise AccountSafetyError("V2 accounts fail-closed: risk_budget_inr must be a positive int")
        slot = normalize_slot(self.slot)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "broker", broker)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "portal_sub", normalize_portal_sub(self.portal_sub))
        object.__setattr__(self, "slot", slot)
        object.__setattr__(self, "journal_tag", normalize_journal_tag(self.journal_tag, slot=slot))
        object.__setattr__(self, "strategy_id", normalize_strategy_id(self.strategy_id))
        object.__setattr__(self, "basket", normalize_basket(self.basket))

    @property
    def slot_armed(self) -> bool:
        return bool(self.strategy_id or self.basket)

    def slot_fields(self) -> dict[str, object]:
        return slot_payload(self)

    @classmethod
    def from_mapping(cls, raw: object) -> Account:
        if not isinstance(raw, dict):
            raise AccountSafetyError("V2 accounts fail-closed: account row must be a mapping")
        budget = raw.get("risk_budget_inr", 30000)
        if isinstance(budget, float) and budget.is_integer():
            budget = int(budget)
        return cls(
            account_id=str(raw.get("account_id") or ""),
            kind=str(raw.get("kind") or ""),
            broker=str(raw.get("broker") or ""),
            status=str(raw.get("status") or ""),
            risk_budget_inr=int(budget) if isinstance(budget, int) else 0,
            portal_sub=str(raw.get("portal_sub") or ""),
            slot=str(raw.get("slot") or ""),
            journal_tag=str(raw.get("journal_tag") or ""),
            strategy_id=str(raw.get("strategy_id") or ""),
            basket=str(raw.get("basket") or ""),
        )
