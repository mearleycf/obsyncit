"""
Sync Manager - Core synchronization functionality.

This module provides the core functionality for syncing settings between Obsidian vaults.
It handles the synchronization of various settings components:
- Core settings (app.json, appearance.json, hotkeys.json)
- Plugin settings (core and community)
- Themes and CSS snippets
- Backup management during sync operations

The module ensures data integrity through:
- JSON validation
- Backup creation before modifications
- Error handling with detailed context
- Dry run capability for safe testing

Example usage:
    ```python
    from obsyncit.sync import SyncManager
    from obsyncit.schemas import Config

    # Initialize with source and target vaults
    sync_mgr = SyncManager(
        source_vault="/path/to/source",
        target_vault="/path/to/target",
        config=Config()
    )

    # Sync all settings
    sync_mgr.sync_settings()

    # Sync specific items
    sync_mgr.sync_settings(items=['themes', 'snippets'])

    # Restore from backup
    sync_mgr.restore_backup()
    ```
"""

import json
import shutil
from pathlib import Path
from typing import List, Optional, Set, Union

from loguru import logger

from obsyncit.backup import BackupManager
from obsyncit.errors import (
    BackupError,
    SyncError,
    ValidationError,
    ObsyncError,
    handle_file_operation_error
)
from obsyncit.schemas import Config
from obsyncit.vault import VaultManager


class SyncManager:
    """
    Manages the synchronization of settings between Obsidian vaults.

    This class handles the complete sync workflow including:
    - Vault validation
    - Backup management
    - Settings synchronization
    - JSON validation
    - Error handling

    The sync process follows these steps:
    1. Validate source and target vaults
    2. Create backup of target settings (if not in dry run mode)
    3. Determine items to sync based on configuration
    4. Syncs each item with validation
    5. Handles any errors according to configuration

    Attributes:
        source (VaultManager): Manager for the source vault
        target (VaultManager): Manager for the target vault
        config (Config): Sync configuration
        backup_mgr (BackupManager): Manager for backup operations
    """

    def __init__(
        self,
        source_vault: str | Path,
        target_vault: str | Path,
        config: Config
    ) -> None:
        """
        Initialize the sync manager.

        Args:
            source_vault: Path to the source vault. Can be string or Path object.
            target_vault: Path to the target vault. Can be string or Path object.
            config: Configuration object controlling sync behavior, including:
                   - Dry run mode
                   - Error handling preferences
                   - Backup settings
                   - Items to sync

        Raises:
            VaultError: If either vault path is invalid
            ConfigError: If configuration is invalid
        """
        self.source = VaultManager(source_vault)
        self.target = VaultManager(target_vault)
        self.config = config
        self.backup_mgr = BackupManager(
            self.target.vault_path,
            config.backup.backup_dir,
            config.backup.max_backups
        )

    def sync_settings(self, items: Optional[List[str]] = None) -> bool:
        """
        Sync settings from source to target vault.

        This method orchestrates the complete sync process:
        1. Validates both vaults
        2. Creates a backup of target settings (unless in dry run mode)
        3. Determines which items to sync
        4. Syncs each item with validation
        5. Handles any errors according to configuration

        The sync operation can be customized through:
        - Specifying items to sync
        - Using dry run mode
        - Configuring error handling behavior

        Args:
            items: Optional list of specific items to sync. If None, syncs all
                  items according to configuration. Valid items include:
                  - 'app.json'
                  - 'appearance.json'
                  - 'hotkeys.json'
                  - 'core-plugins.json'
                  - 'community-plugins.json'
                  - 'themes'
                  - 'snippets'

        Returns:
            bool: True if sync was successful, or if ignore_errors is True and at
                 least one item synced successfully.

        Raises:
            SyncError: If there is an error during sync
            ValidationError: If JSON validation fails
            BackupError: If backup creation fails
            PermissionError: If unable to access required files
            FileNotFoundError: If required files are missing
            json.JSONDecodeError: If JSON parsing fails
            OSError: If there are OS-level issues
        """
        try:
            # Validate vaults
            if not self.source.validate_vault():
                raise SyncError(
                    "Invalid source vault",
                    source=self.source.vault_path,
                    target=self.target.vault_path,
                    details="Source vault validation failed"
                )
            if not self.target.validate_vault():
                raise SyncError(
                    "Invalid target vault",
                    source=self.source.vault_path,
                    target=self.target.vault_path,
                    details="Target vault validation failed"
                )

            # Create backup of target settings if not in dry run mode
            if not self.config.sync.dry_run:
                try:
                    self.backup_mgr.create_backup()
                except (PermissionError, FileNotFoundError) as e:
                    raise BackupError(
                        "Failed to create backup",
                        backup_path=self.backup_mgr.backup_dir,
                        details=str(e)
                    ) from e
                except OSError as e:
                    raise BackupError(
                        "System error during backup",
                        backup_path=self.backup_mgr.backup_dir,
                        details=str(e)
                    ) from e

            # Get list of items to sync
            if items is None:
                items = self._get_sync_items()
            elif not items:
                logger.warning("No items specified for sync")
                return True

            # Create target settings directory if it doesn't exist
            if not self.config.sync.dry_run:
                try:
                    self.target.settings_dir.mkdir(exist_ok=True)
                except PermissionError as e:
                    raise SyncError(
                        "Permission denied",
                        source=self.source.vault_path,
                        target=self.target.vault_path,
                        details=f"Cannot create settings directory: {str(e)}"
                    ) from e
                except OSError as e:
                    raise SyncError(
                        "System error",
                        source=self.source.vault_path,
                        target=self.target.vault_path,
                        details=f"Failed to create settings directory: {str(e)}"
                    ) from e

            # Sync each item
            success = True
            any_success = False
            for item in items:
                try:
                    self._sync_item(item)
                    any_success = True
                except json.JSONDecodeError as e:
                    error = ValidationError(
                        f"Invalid JSON in {item}",
                        file_path=Path(item),
                        schema_errors=[f"JSON parse error: {str(e)}"]
                    )
                    if not self.config.sync.ignore_errors:
                        raise error
                    logger.warning(str(error))
                    success = False
                except (PermissionError, FileNotFoundError) as e:
                    error = SyncError(
                        f"Failed to sync {item}",
                        source=self.source.vault_path,
                        target=self.target.vault_path,
                        details=str(e)
                    )
                    if not self.config.sync.ignore_errors:
                        raise error
                    logger.warning(str(error))
                    success = False
                except OSError as e:
                    error = SyncError(
                        f"System error syncing {item}",
                        source=self.source.vault_path,
                        target=self.target.vault_path,
                        details=str(e)
                    )
                    if not self.config.sync.ignore_errors:
                        raise error
                    logger.warning(str(error))
                    success = False
                except (SyncError, ValidationError) as e:
                    if not self.config.sync.ignore_errors:
                        raise
                    logger.warning(f"Failed to sync {item}: {str(e)}")
                    success = False

            # Return True if all items synced successfully, or if ignore_errors is True and at least one item synced
            return success if not self.config.sync.ignore_errors else any_success

        except (SyncError, ValidationError, BackupError, PermissionError, FileNotFoundError, json.JSONDecodeError, OSError) as e:
            # Log the error with appropriate context
            if isinstance(e, (SyncError, ValidationError, BackupError)):
                logger.error(str(e))
            else:
                logger.error(f"Sync failed: {str(e)}")
            logger.debug("", exc_info=True)
            
            # Re-raise specific errors
            if isinstance(e, (SyncError, ValidationError, BackupError)):
                raise
            # Wrap system errors in SyncError with context
            raise SyncError(
                str(e),
                source=self.source.vault_path,
                target=self.target.vault_path,
                details=f"System error during sync operation: {type(e).__name__}"
            ) from e

    def _get_sync_items(self) -> Set[str]:
        """
        Get the list of items to sync based on configuration.

        This method determines which items should be synced based on:
        1. Configuration settings (enabled/disabled items)
        2. Existence of items in source vault
        3. User-specified items (if provided)

        The following items can be synced:
        - Core settings: app.json, appearance.json, hotkeys.json
        - Plugin settings: core-plugins.json, community-plugins.json
        - Themes directory
        - Snippets directory

        Returns:
            Set[str]: Set of items to sync, containing file and directory names

        Example:
            ```python
            # Get all configured items
            items = sync_mgr._get_sync_items()

            # Get specific items
            items = sync_mgr._get_sync_items(['themes', 'snippets'])
            ```
        """
        # Start with configured items
        sync_items = set()

        # Add core settings if enabled
        if self.config.sync.core_settings:
            for item in ["app.json", "appearance.json", "hotkeys.json"]:
                if (self.source.settings_dir / item).exists():
                    sync_items.add(item)

        # Add core plugins if enabled
        if self.config.sync.core_plugins:
            if (self.source.settings_dir / "core-plugins.json").exists():
                sync_items.add("core-plugins.json")

        # Add community plugins if enabled
        if self.config.sync.community_plugins:
            if (self.source.settings_dir / "community-plugins.json").exists():
                sync_items.add("community-plugins.json")

        # Add snippets if enabled
        if self.config.sync.snippets:
            if (self.source.settings_dir / "snippets").exists():
                sync_items.add("snippets")

        # Add themes if enabled
        if self.config.sync.themes:
            if (self.source.settings_dir / "themes").exists():
                sync_items.add("themes")

        return sync_items

    def validate_json_file(self, file_path: Path, required_fields: Optional[List[str]] = None) -> None:
        """
        Validate a JSON file for correct format and required fields.

        This method performs several validation checks:
        1. File existence
        2. File permissions
        3. JSON syntax
        4. Required fields presence (if specified)

        Args:
            file_path: Path to the JSON file to validate
            required_fields: Optional list of field names that must be present
                           in the JSON object

        Raises:
            ObsyncError: If the file doesn't exist or can't be read
            ValidationError: If the JSON is invalid or missing required fields

        Example:
            ```python
            # Validate JSON syntax only
            sync_mgr.validate_json_file(Path("settings.json"))

            # Validate with required fields
            sync_mgr.validate_json_file(
                Path("app.json"),
                required_fields=["theme", "fontSize"]
            )
            ```
        """
        try:
            if not file_path.exists():
                raise ObsyncError("File not found", str(file_path))

            try:
                with open(file_path) as f:
                    data = json.load(f)
            except PermissionError:
                raise ObsyncError("Permission denied", str(file_path))
            except json.JSONDecodeError as e:
                raise ValidationError("Invalid JSON", file_path, [str(e)])

            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    raise ValidationError(
                        "Schema validation failed",
                        file_path,
                        [f"Missing required fields: {', '.join(missing_fields)}"]
                    )

        except (ObsyncError, ValidationError):
            raise
        except Exception as e:
            raise ObsyncError(f"Failed to validate JSON file: {str(e)}", str(file_path)) from e

    def _sync_item(self, item: str) -> None:
        """
        Sync a specific settings item from source to target vault.

        This method handles the synchronization of individual items:
        - For JSON files: Validates JSON syntax before copying
        - For directories: Recursively copies all contents
        - Handles both file and directory synchronization
        - Supports dry run mode

        Args:
            item: Name of the item to sync (file or directory name)

        Raises:
            SyncError: If there is an error during the sync operation
            ValidationError: If JSON validation fails for JSON files

        Example:
            ```python
            # Sync a JSON file
            sync_mgr._sync_item("app.json")

            # Sync a directory
            sync_mgr._sync_item("themes")
            ```
        """
        source_path = self.source.settings_dir / item
        target_path = self.target.settings_dir / item

        if not source_path.exists():
            raise SyncError(f"Source item does not exist: {item}", source=self.source.vault_path, target=self.target.vault_path)

        try:
            # Validate JSON files
            if item.endswith('.json'):
                with open(source_path) as f:
                    try:
                        json.load(f)
                    except json.JSONDecodeError as e:
                        raise ValidationError(f"Invalid JSON in {item}", file_path=source_path) from e

            # Copy file or directory
            if not self.config.sync.dry_run:
                if source_path.is_file():
                    shutil.copy2(source_path, target_path)
                    logger.info(f"Synced file: {item}")
                else:
                    shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                    logger.info(f"Synced directory: {item}")
            else:
                logger.info(f"Would sync: {item} (dry run)")

        except Exception as e:
            if isinstance(e, (SyncError, ValidationError)):
                raise
            raise SyncError(f"Failed to sync {item}: {str(e)}", source=self.source.vault_path, target=self.target.vault_path) from e

    def list_backups(self) -> List[str]:
        """
        List available backups for the target vault.

        Returns:
            List[str]: List of backup paths, sorted by creation time
                      (most recent first)

        Example:
            ```python
            # List all backups
            backups = sync_mgr.list_backups()
            for backup in backups:
                print(f"Available backup: {backup}")
            ```
        """
        return self.backup_mgr.list_backups()

    def restore_backup(self, backup_path: Optional[Path] = None) -> bool:
        """
        Restore settings from a backup.

        This method restores the target vault's settings from a backup:
        - If no backup_path is provided, restores from the most recent backup
        - Validates the backup before restoration
        - Handles the restoration process safely

        Args:
            backup_path: Optional specific backup to restore from. If None,
                       uses the most recent backup.

        Returns:
            bool: True if restore was successful, False otherwise

        Raises:
            BackupError: If the backup doesn't exist or can't be restored

        Example:
            ```python
            # Restore from most recent backup
            success = sync_mgr.restore_backup()

            # Restore from specific backup
            success = sync_mgr.restore_backup(Path("/path/to/backup"))
            ```
        """
        return self.backup_mgr.restore_backup(backup_path)
