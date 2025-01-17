"""
ObsyncIt - Obsidian Settings Sync Tool

This package provides functionality to synchronize Obsidian vault settings
between different vaults. It supports syncing core settings, plugins,
themes, and snippets.
"""

from obsyncit.sync import SyncManager
from obsyncit.backup import BackupManager
from obsyncit.vault_discovery import VaultDiscovery
from obsyncit.schemas import Config, SyncConfig
from obsyncit.errors import (
    ObsyncError,
    VaultError,
    ConfigError,
    BackupError,
    SyncError,
    ValidationError,
)

__version__ = "0.1.0"

__all__ = [
    # Core functionality
    "SyncManager",
    "BackupManager",
    "VaultDiscovery",
    
    # Configuration and schemas
    "Config",
    "SyncConfig",
    
    # Exceptions
    "ObsyncError",
    "VaultError",
    "ConfigError",
    "BackupError",
    "SyncError",
    "ValidationError",
]