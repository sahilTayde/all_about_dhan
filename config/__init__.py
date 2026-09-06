"""Customer master config: `config/workspace.yaml`."""

from .load import (
    DeskIntelSettings,
    Market,
    NewsSource,
    WorkspaceConfig,
    load_workspace,
)

__all__ = [
    "DeskIntelSettings",
    "Market",
    "NewsSource",
    "WorkspaceConfig",
    "load_workspace",
]
