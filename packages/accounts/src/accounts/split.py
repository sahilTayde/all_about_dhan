"""Signal vs exec split (architecture §2.15). Same kernel, different handler set."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from accounts.errors import AccountClosed
from accounts.isolation import IsolatedBook, bind_book, oms_stream, position_stream
from accounts.model import Account
from accounts.registry import AccountRegistry
from accounts.safety import assert_paper_only

SIGNAL_HANDLERS = frozenset({"features", "strategies", "boss"})
EXEC_HANDLERS = frozenset({"risk", "router", "position_manager", "ledger"})
SIGNAL_CONSUMES = frozenset({"md:*"})
SIGNAL_PRODUCES = frozenset({"boss:decisions"})
EXEC_CONSUMES = frozenset({"md:*", "boss:decisions", "ctl:commands"})


@dataclass(frozen=True)
class RoleBinding:
    role: Literal["signal", "exec"]
    account_id: str | None
    handlers: frozenset[str]
    consumes: frozenset[str]
    produces: frozenset[str]
    broker: str | None = None
    partition: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "account_id": self.account_id,
            "handlers": sorted(self.handlers),
            "consumes": sorted(self.consumes),
            "produces": sorted(self.produces),
            "broker": self.broker,
            "partition": self.partition,
            "live_broker": False,
            "orders": "REFUSED" if self.role == "signal" else "PAPER",
        }


def handlers_for(role: str) -> frozenset[str]:
    cleaned = (role or "").strip().lower()
    if cleaned == "signal":
        return SIGNAL_HANDLERS
    if cleaned == "exec":
        return EXEC_HANDLERS
    raise AccountClosed(f"UNKNOWN_ROLE:{role}")


def bind_signal() -> RoleBinding:
    overlap = SIGNAL_HANDLERS & EXEC_HANDLERS
    if overlap:
        raise AccountClosed(f"HANDLER_OVERLAP:{sorted(overlap)}")
    return RoleBinding(
        role="signal",
        account_id=None,
        handlers=SIGNAL_HANDLERS,
        consumes=SIGNAL_CONSUMES,
        produces=SIGNAL_PRODUCES,
    )


def bind_exec(account: Account) -> tuple[RoleBinding, IsolatedBook]:
    book = bind_book(account)
    return (
        RoleBinding(
            role="exec",
            account_id=account.account_id,
            handlers=EXEC_HANDLERS,
            consumes=EXEC_CONSUMES,
            produces=frozenset({oms_stream(account.account_id), position_stream(account.account_id)}),
            broker=account.broker,
            partition=book.partition,
        ),
        book,
    )


def run_role_once(
    *,
    role: str,
    account_id: str | None = None,
    state_dir: Path | None = None,
    config_path: Path | None = None,
    mode: str = "paper",
) -> dict[str, Any]:
    """Paper stub for `runtime signal` / `runtime exec --account`. No broker process."""
    assert_paper_only(mode)
    cleaned = (role or "").strip().lower()
    if cleaned == "signal":
        binding = bind_signal()
        body = binding.as_dict()
        body["ok"] = True
        _write_ready(state_dir, "signal")
        return body
    if cleaned != "exec":
        raise AccountClosed(f"UNKNOWN_ROLE:{role}")
    registry = AccountRegistry.load(config_path)
    account = registry.require_active(account_id or registry.default_account)
    binding, _book = bind_exec(account)
    body = binding.as_dict()
    body["ok"] = True
    _write_ready(state_dir, f"exec-{account.account_id}")
    return body


def _write_ready(state_dir: Path | None, name: str) -> None:
    if state_dir is None:
        return
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / f"{name}.ready").write_text("ok\n", encoding="utf-8")
