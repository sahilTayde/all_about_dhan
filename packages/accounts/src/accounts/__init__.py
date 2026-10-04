"""V2-22 / C5-01 accounts layer. Paper/shadow only. Fail closed. No live broker."""

from accounts.errors import AccountClosed, AccountIsolationError, AccountSafetyError
from accounts.isolation import IsolatedBook, bind_book, ledger_partition, position_key, position_stream
from accounts.model import Account
from accounts.registry import (
    MAX_CUSTOMER_ACCOUNTS,
    PAPER_LAUNCH_CUSTOMER_IDS,
    AccountRegistry,
    optional_customers_path,
    set_account_status,
)
from accounts.safety import assert_paper_only, refuse_broker_name
from accounts.split import EXEC_HANDLERS, SIGNAL_HANDLERS, RoleBinding, bind_exec, bind_signal, run_role_once

__version__ = "0.1.0+aad"

__all__ = [
    "EXEC_HANDLERS",
    "MAX_CUSTOMER_ACCOUNTS",
    "PAPER_LAUNCH_CUSTOMER_IDS",
    "SIGNAL_HANDLERS",
    "Account",
    "AccountClosed",
    "AccountIsolationError",
    "AccountRegistry",
    "AccountSafetyError",
    "IsolatedBook",
    "RoleBinding",
    "__version__",
    "assert_paper_only",
    "bind_book",
    "bind_exec",
    "bind_signal",
    "ledger_partition",
    "optional_customers_path",
    "position_key",
    "position_stream",
    "refuse_broker_name",
    "run_role_once",
    "set_account_status",
]
