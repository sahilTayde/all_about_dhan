"""V2-24 secret store. Paper/shadow only. Never constructs a Dhan session."""

from secretstore.accounts import AccountDirectory, AccountRef, AccountStub, MemoryAccounts
from secretstore.crypto import AgeIdentity, AgeRecipient, generate_identity, parse_identity, parse_recipient
from secretstore.errors import SecretClosed
from secretstore.store import (
    BlobBackend,
    BrokerCredential,
    DiskBlobBackend,
    FileSecretStore,
    OnePasswordConnectAdapter,
    SecretStore,
    VaultAdapter,
    open_store,
    open_store_from_env,
)

__version__ = "0.1.0+aad"

__all__ = [
    "AccountDirectory",
    "AccountRef",
    "AccountStub",
    "AgeIdentity",
    "AgeRecipient",
    "BlobBackend",
    "BrokerCredential",
    "DiskBlobBackend",
    "FileSecretStore",
    "MemoryAccounts",
    "OnePasswordConnectAdapter",
    "SecretClosed",
    "SecretStore",
    "VaultAdapter",
    "__version__",
    "generate_identity",
    "open_store",
    "open_store_from_env",
    "parse_identity",
    "parse_recipient",
]
