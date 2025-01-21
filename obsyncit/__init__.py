"""
ObsyncIt - Obsidian Settings Sync Tool

This package provides functionality to synchronize Obsidian vault settings
between different vaults on a file system. It handles all aspects of vault
synchronization, including settings, plugins, themes, and backups.

Core Features:
1. Vault Management
   - Automatic vault discovery
   - Structure validation
   - Settings verification
   - Resource management

2. Settings Synchronization
   - Core settings files
   - Plugin configurations
   - Theme settings
   - Hotkey mappings
   - Template configurations
   - Type definitions

3. Resource Management
   - Community plugins
   - Plugin data and icons
   - Custom themes
   - CSS snippets
   - Migration settings

4. Backup and Safety
   - Automatic backups
   - Backup rotation
   - Safe restoration
   - Integrity verification

5. User Interfaces
   - Command-line interface (CLI)
   - Text user interface (TUI)
   - Progress indicators
   - Error reporting

Configuration:
    The package uses TOML configuration files with sensible defaults:
    - Sync options (dry run, error handling, etc.)
    - Backup settings (count, rotation, etc.)
    - Logging configuration
    - UI preferences

Examples:
    Basic Synchronization:
        >>> from obsyncit import SyncManager, Config
        >>> 
        >>> # Initialize with defaults
        >>> sync_mgr = SyncManager(
        ...     source_vault="path/to/source",
        ...     target_vault="path/to/target",
        ...     config=Config()
        ... )
        >>> 
        >>> # Sync all settings
        >>> result = sync_mgr.sync_settings()
        >>> if result.success:
        ...     print(f"Synced {len(result.items_synced)} items")

    Advanced Configuration:
        >>> from obsyncit import Config, SyncConfig
        >>> 
        >>> # Create custom configuration
        >>> config = Config(
        ...     sync=SyncConfig(
        ...         dry_run=True,
        ...         ignore_errors=True,
        ...         core_settings=True,
        ...         plugins=True,
        ...         themes=True
        ...     ),
        ...     backup={"max_backups": 5},
        ...     logging={"level": "DEBUG"}
        ... )
        >>> 
        >>> # Initialize with custom config
        >>> sync_mgr = SyncManager("source", "target", config)
        >>> 
        >>> # Sync specific items
        >>> result = sync_mgr.sync_settings([
        ...     "appearance.json",
        ...     "plugins",
        ...     "themes"
        ... ])

    Vault Discovery:
        >>> from obsyncit import VaultDiscovery
        >>> 
        >>> # Find all vaults
        >>> finder = VaultDiscovery()
        >>> vaults = finder.find_vaults()
        >>> 
        >>> # Get vault information
        >>> for vault in vaults:
        ...     info = finder.get_vault_info(vault)
        ...     print(f"Vault: {info.name}")
        ...     print(f"Settings: {info.settings_count}")
        ...     print(f"Plugins: {info.plugin_count}")

    Backup Management:
        >>> from obsyncit import BackupManager
        >>> 
        >>> # Initialize backup manager
        >>> backup_mgr = BackupManager(
        ...     vault_path="path/to/vault",
        ...     backup_dir=".backups",
        ...     max_backups=5
        ... )
        >>> 
        >>> # Create backup
        >>> info = backup_mgr.create_backup()
        >>> print(f"Created: {info.timestamp}")
        >>> print(f"Size: {info.size_mb:.1f}MB")
        >>> 
        >>> # List backups
        >>> for backup in backup_mgr.list_backups():
        ...     print(f"{backup.timestamp}: {backup.size_mb:.1f}MB")
        >>> 
        >>> # Restore backup
        >>> if backup_mgr.restore_backup():
        ...     print("Backup restored successfully")

    Error Handling:
        >>> from obsyncit.errors import VaultError, SyncError
        >>> 
        >>> try:
        ...     sync_mgr.sync_settings()
        ... except VaultError as e:
        ...     print(f"Invalid vault: {e.vault_path}")
        ... except SyncError as e:
        ...     print(f"Sync failed: {e.message}")
        ...     for item, error in e.errors.items():
        ...         print(f"  {item}: {error}")
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