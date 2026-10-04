"""Per-account ledger partition, positions, streams, and sizing (architecture §5.6)."""

from __future__ import annotations

from dataclasses import dataclass, field

from contracts.ids import order_id

from accounts.errors import AccountClosed, AccountIsolationError
from accounts.model import Account
from accounts.safety import assert_active


def ledger_partition(account_id: str) -> str:
    return f"ledger:{account_id}"


def position_stream(account_id: str) -> str:
    return f"pos:{account_id}"


def oms_stream(account_id: str) -> str:
    return f"oms:{account_id}"


def position_key(account_id: str, instrument_id: str) -> tuple[str, str]:
    return (account_id, instrument_id)


@dataclass
class IsolatedBook:
    """In-memory partition for one account. A never reads, writes, or sizes B."""

    account: Account
    rows: list[dict[str, object]] = field(default_factory=list)
    positions: dict[tuple[str, str], dict[str, object]] = field(default_factory=dict)
    spent_inr: int = 0

    def __post_init__(self) -> None:
        assert_active(self.account)

    @property
    def partition(self) -> str:
        return ledger_partition(self.account.account_id)

    @property
    def stream(self) -> str:
        return position_stream(self.account.account_id)

    @property
    def remaining_budget_inr(self) -> int:
        return self.account.risk_budget_inr - self.spent_inr

    def _own(self, account_id: str, action: str) -> None:
        if account_id != self.account.account_id:
            raise AccountIsolationError(self.account.account_id, account_id, action)

    def append_row(self, row: dict[str, object]) -> None:
        self._own(str(row.get("account_id") or ""), "write")
        self.rows.append(dict(row))

    def read(self, account_id: str) -> list[dict[str, object]]:
        self._own(account_id, "read")
        return [dict(row) for row in self.rows]

    def size_lots(self, account_id: str, stop_inr_per_lot: int) -> int:
        self._own(account_id, "size")
        if not isinstance(stop_inr_per_lot, int) or isinstance(stop_inr_per_lot, bool) or stop_inr_per_lot <= 0:
            raise AccountClosed("STOP_INR_INVALID")
        return self.remaining_budget_inr // stop_inr_per_lot

    def apply_fill(self, account_id: str, instrument_id: str, qty: int, premium_inr: int) -> dict[str, object]:
        self._own(account_id, "affect")
        if qty <= 0 or premium_inr <= 0:
            raise AccountClosed("FILL_INVALID")
        if premium_inr > self.remaining_budget_inr:
            raise AccountClosed("BUDGET")
        key = position_key(account_id, instrument_id)
        pos = self.positions.get(key) or {
            "account_id": account_id,
            "instrument_id": instrument_id,
            "net_qty": 0,
            "premium_inr": 0,
        }
        net = pos["net_qty"]
        prem = pos["premium_inr"]
        if not isinstance(net, int) or isinstance(net, bool):
            raise AccountClosed("POSITION_CORRUPT")
        if not isinstance(prem, int) or isinstance(prem, bool):
            raise AccountClosed("POSITION_CORRUPT")
        pos["net_qty"] = net + qty
        pos["premium_inr"] = prem + premium_inr
        self.positions[key] = pos
        self.spent_inr += premium_inr
        self.append_row(
            {
                "account_id": account_id,
                "instrument_id": instrument_id,
                "qty": qty,
                "premium_inr": premium_inr,
                "partition": self.partition,
                "stream": self.stream,
            }
        )
        return dict(pos)

    def apply_decision(self, decision: dict[str, object]) -> dict[str, object]:
        """Stamp a shared boss:decision onto this book. Foreign account_id is refused."""
        bound = decision.get("account_id")
        if bound not in (None, "", self.account.account_id):
            raise AccountIsolationError(self.account.account_id, str(bound), "apply-decision")
        signal_id = str(decision.get("signal_id") or "")
        if not signal_id:
            raise AccountClosed("SIGNAL_ID_REQUIRED")
        oid = order_id(self.account.account_id, signal_id, "entry")
        row: dict[str, object] = {
            "account_id": self.account.account_id,
            "signal_id": signal_id,
            "client_order_id": oid,
            "partition": self.partition,
            "stream": oms_stream(self.account.account_id),
            "broker": self.account.broker,
        }
        self.append_row(row)
        return dict(row)


def bind_book(account: Account) -> IsolatedBook:
    return IsolatedBook(account=assert_active(account))
