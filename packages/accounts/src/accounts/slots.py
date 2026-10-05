"""C5-07 paper slot map. Portal c1-c5 -> customer-01..05. No live broker.

Exec today binds ``runtime exec --account``. It did not read a strategy/basket
field. These optional account keys are the mapping it now reads:

- ``slot``: placeholder label (CONTROL / CANDLE_GEOM / LOCATION / SKLEARN /
  HYBRID_OR_ROUTER). Not a registry plugin and not claimed edge.
- ``journal_tag``: night-card compare key (``SLOT-<slot>`` when omitted).
- ``portal_sub``: portal JWT seat ``c1``..``c5`` (C5-02 allowlist).
- ``strategy_id`` / ``basket``: unset until desk lead assigns. Empty = knobs
  off (``slot_armed`` is false). No invented trades.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from accounts.errors import AccountClosed, AccountSafetyError

PAPER_SLOT_LABELS = (
    "CONTROL",
    "CANDLE_GEOM",
    "LOCATION",
    "SKLEARN",
    "HYBRID_OR_ROUTER",
)
PAPER_SLOT_SET = frozenset(PAPER_SLOT_LABELS)
PORTAL_SUBS = tuple(f"c{i}" for i in range(1, 6))
PORTAL_TO_ACCOUNT = {f"c{i}": f"customer-{i:02d}" for i in range(1, 6)}
ACCOUNT_TO_PORTAL = {account: sub for sub, account in PORTAL_TO_ACCOUNT.items()}
LAUNCH_SLOT_PLAN: tuple[tuple[str, str, str], ...] = (
    ("customer-01", "c1", "CONTROL"),
    ("customer-02", "c2", "CANDLE_GEOM"),
    ("customer-03", "c3", "LOCATION"),
    ("customer-04", "c4", "SKLEARN"),
    ("customer-05", "c5", "HYBRID_OR_ROUTER"),
)
ACCOUNT_TO_SLOT = {account: slot for account, _sub, slot in LAUNCH_SLOT_PLAN}

_PORTAL_RE = re.compile(r"^c[1-5]$")
_TAG_RE = re.compile(r"^[A-Z][A-Z0-9_-]{0,63}$")
_STRATEGY_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{0,63}$")
_BASKET_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_STRAT_015_RE = re.compile(r"^STRAT-(0(1[5-9]|[2-9]\d)|[1-9]\d{2,})$")
_FORBIDDEN_BASKETS = frozenset({"dry_run", "dry-run", "live", "dhan", "limited_live"})
TEST_CROSS_ID = "TEST-CROSS"


def optional_text(raw: object) -> str:
    return str(raw or "").strip()


def normalize_portal_sub(raw: object) -> str:
    text = optional_text(raw).lower()
    if not text:
        return ""
    if not _PORTAL_RE.fullmatch(text):
        raise AccountSafetyError(f"V2 accounts fail-closed: portal_sub {raw!r} is not c1..c5")
    return text


def normalize_slot(raw: object) -> str:
    text = optional_text(raw).upper().replace(" ", "_")
    if not text:
        return ""
    if text not in PAPER_SLOT_SET:
        raise AccountSafetyError(f"V2 accounts fail-closed: slot {raw!r} is not one of {', '.join(PAPER_SLOT_LABELS)}")
    return text


def normalize_journal_tag(raw: object, *, slot: str = "") -> str:
    text = optional_text(raw).upper().replace(" ", "_")
    if not text:
        return f"SLOT-{slot}" if slot else ""
    if not _TAG_RE.fullmatch(text):
        raise AccountSafetyError(f"V2 accounts fail-closed: illegal journal_tag {raw!r}")
    return text


def normalize_strategy_id(raw: object) -> str:
    text = optional_text(raw)
    if not text:
        return ""
    if text == TEST_CROSS_ID:
        raise AccountSafetyError(f"V2 accounts fail-closed: {TEST_CROSS_ID} is dry-run only")
    if _STRAT_015_RE.fullmatch(text):
        raise AccountSafetyError("V2 accounts fail-closed: STRAT-015+ is forbidden")
    if not _STRATEGY_RE.fullmatch(text):
        raise AccountSafetyError(f"V2 accounts fail-closed: illegal strategy_id {raw!r}")
    return text


def normalize_basket(raw: object) -> str:
    text = optional_text(raw).lower().rsplit("/", 1)[-1]
    if text.endswith(".yaml"):
        text = text[: -len(".yaml")]
    if not text:
        return ""
    if ".." in text or text in _FORBIDDEN_BASKETS:
        raise AccountSafetyError(f"V2 accounts fail-closed: basket {raw!r} is not paper/shadow")
    if not _BASKET_RE.fullmatch(text):
        raise AccountSafetyError(f"V2 accounts fail-closed: illegal basket {raw!r}")
    return text


def account_id_for_portal_sub(sub: str, registry: object | None = None) -> str:
    """Map portal JWT seat ``c1`` to paper book ``customer-01``. Fail closed."""
    who = optional_text(sub).lower()
    if registry is not None:
        matches = [acc for acc in registry.all() if acc.portal_sub == who]  # type: ignore[attr-defined]
        if len(matches) > 1:
            raise AccountSafetyError(f"V2 accounts fail-closed: portal_sub {who!r} is bound more than once")
        if len(matches) == 1:
            return str(matches[0].account_id)
    found = PORTAL_TO_ACCOUNT.get(who)
    if found is None:
        raise AccountClosed(f"UNKNOWN_PORTAL_SUB:{sub}")
    return found


def assert_unique_slot_fields(accounts: Sequence[object]) -> None:
    slots: dict[str, str] = {}
    portals: dict[str, str] = {}
    tags: dict[str, str] = {}
    strategies: dict[str, str] = {}
    for acc in accounts:
        aid = str(getattr(acc, "account_id", "") or "")
        slot = str(getattr(acc, "slot", "") or "")
        portal = str(getattr(acc, "portal_sub", "") or "")
        tag = str(getattr(acc, "journal_tag", "") or "")
        strategy = str(getattr(acc, "strategy_id", "") or "")
        if slot:
            prior = slots.get(slot)
            if prior and prior != aid:
                raise AccountSafetyError(f"V2 accounts fail-closed: duplicate slot {slot!r}")
            slots[slot] = aid
        if portal:
            prior = portals.get(portal)
            if prior and prior != aid:
                raise AccountSafetyError(f"V2 accounts fail-closed: duplicate portal_sub {portal!r}")
            portals[portal] = aid
        if tag:
            prior = tags.get(tag)
            if prior and prior != aid:
                raise AccountSafetyError(f"V2 accounts fail-closed: duplicate journal_tag {tag!r}")
            tags[tag] = aid
        if strategy:
            prior = strategies.get(strategy)
            if prior and prior != aid:
                raise AccountSafetyError(f"V2 accounts fail-closed: duplicate strategy_id {strategy!r}")
            strategies[strategy] = aid


def slot_payload(account: object) -> dict[str, object]:
    """Stable exec / list / journal stamp. Empty strategy/basket => unarmed."""
    slot = str(getattr(account, "slot", "") or "") or None
    journal_tag = str(getattr(account, "journal_tag", "") or "") or None
    strategy_id = str(getattr(account, "strategy_id", "") or "") or None
    basket = str(getattr(account, "basket", "") or "") or None
    portal_sub = str(getattr(account, "portal_sub", "") or "") or None
    return {
        "portal_sub": portal_sub,
        "slot": slot,
        "journal_tag": journal_tag,
        "strategy_id": strategy_id,
        "basket": basket,
        "slot_armed": bool(strategy_id or basket),
    }
